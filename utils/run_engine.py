# Entrypoint will be placed at the end of the file
import re
import sqlite3
import argparse
import logging
from pathlib import Path

# Third-party
import pdfplumber
from tqdm import tqdm


# Local imports
from utils.common import sha16, sha64
from utils.text_utils import chunk_sentences, guess_stage, guess_section
from utils.entities import extract_entities, extract_compounds
from utils.data_extractors import extract_quantitative_data, extract_relationships
from utils.event_classification import (
    METHOD_TAGS,
    FAILURE_PHRASES,
    DECISION_PHRASES,
    detect_method_tags,
    detect_failure_reason,
    detect_decision,
    detect_outcome,
    classify_event_type,
    evidence_strength,
    confidence_score,
)
from utils.db_utils import (
    upsert_source, insert_document, insert_chunk, upsert_entity, insert_event,
    link_event_entity, link_event_tag, insert_measurement
)

# Use plain text loader for text seeds
from utils.common import load_seed_file

# Re-export for backward compatibility
__all__ = [
    "load_seed_file",
    "extract_compounds",
    "extract_relationships",
    "extract_entities",
]

# --- Seed loading for backward compatibility ---
from utils.common import _get_compound_seeds, _get_target_seeds, _get_model_seeds, _get_stopword_seeds

def get_seeds(SEEDS_DIR=None):
    """Return (compounds, targets, models, stopwords) as sets."""
    return (
        _get_compound_seeds(SEEDS_DIR),
        _get_target_seeds(SEEDS_DIR),
        _get_model_seeds(SEEDS_DIR),
        _get_stopword_seeds(SEEDS_DIR),
    )


# Define SEEDS_DIR relative to the project root (repo root)
project_root = Path(__file__).resolve().parent.parent
if (project_root / 'input' / 'seeds').exists():
    SEEDS_DIR = project_root / 'input' / 'seeds'
else:
    SEEDS_DIR = project_root / 'seeds'

# Confidence scoring thresholds for evidence strength
HIGH_CONF_THRESHOLD = 6  # High confidence: strong evidence, multiple signals
MED_CONF_THRESHOLD = 3   # Medium confidence: moderate evidence

# ---------------------------------------------------------
# Metadata Extraction
# ---------------------------------------------------------
def extract_metadata(pdf_path: Path, pdf) -> dict:
    """Extract paper metadata from PDF"""
    metadata = {
        'title': None,
        'authors': None,
        'year': None,
        'doi': None,
        'venue': None
    }
    
    # Try PDF metadata first
    if pdf.metadata:
        metadata['title'] = pdf.metadata.get('Title')
        metadata['authors'] = pdf.metadata.get('Author')
        
        # Try to extract year from creation date
        if pdf.metadata.get('CreationDate'):
            try:
                year_match = re.search(r'(19|20)\d{2}', str(pdf.metadata.get('CreationDate')))
                if year_match:
                    metadata['year'] = int(year_match.group(0))
            except Exception as e:
                logging.exception(f"Error extracting year from CreationDate: {e}")
    
    # Try first page text for DOI and other metadata
    if pdf.pages:
        try:
            first_page = pdf.pages[0].extract_text() or ""
            # Extract DOI
            doi_match = re.search(r'doi[:\s]*(10\.\d{4,}/[^\s]+)', first_page, re.I)
            if doi_match:
                metadata['doi'] = doi_match.group(1).rstrip('.,;')
            # Extract year from text if not found in metadata
            if not metadata['year']:
                year_match = re.search(r'\b(19|20)\d{2}\b', first_page)
                if year_match:
                    metadata['year'] = int(year_match.group(0))
            # Try to extract title from first page if not in metadata
            if not metadata['title']:
                # Usually the title is in the first few lines
                lines = first_page.split('\n')[:10]
                for line in lines:
                    if len(line) > 20 and len(line) < 200:  # Reasonable title length
                        metadata['title'] = line.strip()
                        break
        except Exception as e:
            print(f"  ⚠️  Could not extract metadata from first page: {e}")
    return metadata



# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main(domain: str | None = None, input_dir: Path | None = None, db_path: Path | None = None, lenses: list | None = None):
    # Parse command line arguments only if all parameters are None
    parser = argparse.ArgumentParser(description='Scrape PDFs for research intelligence')
    parser.add_argument('--domain', default='methods_tooling', 
                       help='Research domain (methods_tooling, drug_discovery, etc.)')
    parser.add_argument('--input-dir', type=Path, default=Path('input/pdfs'),
                       help='Directory containing PDF files')
    parser.add_argument('--output-db', type=Path, default=Path('db/runs.sqlite'),
                       help='Output SQLite database path')

    if domain is None and input_dir is None and db_path is None:
        args = parser.parse_args()
        research_domain = args.domain
        input_dir = args.input_dir
        db_path = args.output_db
    else:
        research_domain = domain if domain is not None else 'methods_tooling'
        input_dir = input_dir if input_dir is not None else Path('input/pdfs')
        db_path = db_path if db_path is not None else Path('db/runs.sqlite')
    
    # TODO: Implement lens filtering when lens system is ready
    # Currently lenses parameter is accepted but not used
    if lenses is not None:
        print(f"⚠️  Lenses parameter provided but not implemented yet: {lenses}")
        # Future implementation would filter processing based on selected lenses
    
    if isinstance(input_dir, str):
        input_dir = Path(input_dir)
    if isinstance(db_path, str):
        db_path = Path(db_path)
    
    if not input_dir.exists():
        raise SystemExit(f"Missing folder: {input_dir.resolve()}")

    # Recursively find all PDFs in input_dir and subfolders
    pdfs = sorted(input_dir.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs to process in {input_dir.resolve()}")
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {input_dir.resolve()}")

    # Ensure output directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    

    # Use context manager for database connection
    with sqlite3.connect(db_path) as con:
        # Check if schema exists by looking for a required table
        try:
            con.execute("SELECT 1 FROM sources LIMIT 1;")
        except sqlite3.OperationalError:
            raise SystemExit("Database schema is missing. Please initialize the schema before running the engine.")

        for pdf_path in tqdm(pdfs, desc="PDFs"):
            print(f"Processing PDF: {pdf_path}")
            try:
                # create stable-ish ids using file content hash and relative path
                try:
                    rel_path = str(pdf_path.relative_to(project_root))
                except ValueError:
                    # Fallback: use os.path.relpath or str(pdf_path) as stable alternative
                    try:
                        import os
                        rel_path = os.path.relpath(str(pdf_path), str(project_root))
                    except Exception:
                        rel_path = str(pdf_path)
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()
                content_hash = sha16(file_bytes.hex())
                source_id = sha16(f"{rel_path}|{content_hash}")
                file_hash = sha64(f"{rel_path}|{content_hash}")

                with pdfplumber.open(str(pdf_path)) as pdf:
                    # Extract metadata
                    metadata = extract_metadata(pdf_path, pdf)
                    upsert_source(con, source_id, pdf_path.name, metadata)
                    doc_id = insert_document(con, source_id, str(pdf_path.resolve()), file_hash)

                    for page_idx, page in enumerate(pdf.pages, start=1):
                        try:
                            text = page.extract_text() or ""
                            if not text.strip():
                                continue
                            section = guess_section(text.lower())
                            chunk_id = insert_chunk(con, source_id, doc_id, page_idx, section, text)
                            # sentence scan
                            for sent in chunk_sentences(text):
                                s_l = sent.lower()
                                # keep only sentences with any signal or quantitative data
                                quantitative = extract_quantitative_data(sent)
                                has_signal = (
                                    any(p in s_l for lst in FAILURE_PHRASES.values() for p in lst) or
                                    any(p in s_l for lst in DECISION_PHRASES.values() for p in lst) or
                                    any(p in s_l for lst in METHOD_TAGS.values() for p in lst) or
                                    bool(quantitative)
                                )
                                if not has_signal:
                                    continue
                                tags = detect_method_tags(s_l)
                                failure_reason = detect_failure_reason(s_l)
                                decision_taken, decision_driver = detect_decision(s_l)
                                outcome = detect_outcome(s_l)
                                stage = guess_stage(s_l)
                                event_type = classify_event_type(s_l, tags, failure_reason, decision_taken)
                                strength = evidence_strength(s_l)
                                entities = extract_entities(sent, research_domain)
                                # Compute confidence
                                conf = confidence_score(bool(entities), tags, failure_reason, decision_taken, bool(quantitative), s_l)
                                # Insert event
                                event_id = insert_event(
                                    con, source_id, doc_id, chunk_id, page_idx,
                                    research_domain, event_type, stage, None, None,
                                    outcome, failure_reason, decision_taken, decision_driver,
                                    sent, strength, conf
                                )
                                # Link entities
                                for ent in entities:
                                    entity_id = upsert_entity(
                                        con,
                                        ent.get("entity_type"),
                                        ent.get("entity_name"),
                                        ent.get("entity_variant"),
                                        ent.get("organism")
                                    )
                                    link_event_entity(con, event_id, entity_id, ent.get("role", ""))
                                # Link tags
                                for tag in tags:
                                    link_event_tag(con, event_id, tag)
                                # Insert quantitative measurements
                                for m in quantitative:
                                    insert_measurement(con, event_id, m)
                        except Exception as e:
                            print(f"  ⚠️  Error processing page {page_idx} in {pdf_path.name}: {e}")
            except Exception as e:
                print(f"  ⚠️  Error processing PDF {pdf_path.name}: {e}")

# Entrypoint: call main() if run as a script (must be at the end)
if __name__ == "__main__":
    main()



