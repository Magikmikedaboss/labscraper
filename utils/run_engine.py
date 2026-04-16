# Re-export for test imports
from utils.common import get_seeds, load_seed_file, sha16, sha64

# Explicitly declare public API for re-exports
__all__ = ["sha16", "sha64", "get_seeds", "load_seed_file"]
# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------

from pathlib import Path
import sqlite3
import sys
import re
import logging
import argparse
from utils.db_init import _init_db_schema


import pdfplumber
from tqdm import tqdm

# Local utils
from utils.common import sha16, sha64  # Re-export for consumers
from utils.text_utils import chunk_sentences, guess_stage, guess_section
from utils.entities import extract_entities
from utils.data_extractors import extract_quantitative_data
from utils.event_classification import (
    FAILURE_PHRASES,
    detect_method_tags,
    detect_failure_reason,
    detect_decision,
    detect_outcome,
    classify_event_type,
    evidence_strength,
    confidence_score,
)
from utils.db_utils import (
    upsert_source,
    insert_document,
    insert_chunk,
    upsert_entity,
    insert_event,
    link_event_entity,
    link_event_tag,
    insert_measurement,
)

# ---------------------------------------------------------
# DB INIT
# ---------------------------------------------------------
def _init_db_schema_if_needed(db_path):
    """
    Ensure the database at db_path is initialized with the schema.
    Delegates to utils.db_init._init_db_schema for actual initialization logic.
    """
    _init_db_schema(str(db_path))


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
project_root = Path(__file__).resolve().parent.parent

if (project_root / "input" / "seeds").exists():
    SEEDS_DIR = project_root / "input" / "seeds"
else:
    SEEDS_DIR = project_root / "seeds"


# ---------------------------------------------------------
# METADATA EXTRACTION
# ---------------------------------------------------------
def extract_metadata(pdf_path: Path, pdf) -> dict:
    metadata = {
        "title": None,
        "authors": None,
        "year": None,
        "doi": None,
        "venue": None,
    }

    if pdf.metadata:
        metadata["title"] = pdf.metadata.get("Title")
        metadata["authors"] = pdf.metadata.get("Author")

        if pdf.metadata.get("CreationDate"):
            try:
                year_match = re.search(r"(19|20)\d{2}", str(pdf.metadata.get("CreationDate")))
                if year_match:
                    metadata["year"] = int(year_match.group(0))
            except Exception as e:
                logging.exception(f"Error extracting year: {e}")

    if pdf.pages:
        try:
            first_page = pdf.pages[0].extract_text() or ""

            doi_match = re.search(r"doi[:\s]*(10\.\d{4,}/[^\s]+)", first_page, re.I)
            if doi_match:
                metadata["doi"] = doi_match.group(1).rstrip(".,;")

            if not metadata["year"]:
                year_match = re.search(r"\b(19|20)\d{2}\b", first_page)
                if year_match:
                    metadata["year"] = int(year_match.group(0))

            if not metadata["title"]:
                lines = first_page.split("\n")[:10]
                for line in lines:
                    if 20 < len(line) < 200:
                        metadata["title"] = line.strip()
                        break

        except Exception as e:
            print(f"⚠️ Metadata extraction failed: {e}")

    return metadata


# ---------------------------------------------------------
# MAIN ENGINE
# ---------------------------------------------------------
def main(domain=None, input_dir=None, db_path=None, lenses=None):

    parser = argparse.ArgumentParser(description="Scrape PDFs for research intelligence")
    parser.add_argument("--domain", default="methods_tooling")
    parser.add_argument("--input-dir", type=Path, default=Path("input/pdfs"))
    parser.add_argument("--output-db", type=Path, default=Path("db/runs.sqlite"))

    if domain is None and input_dir is None and db_path is None:
        args = parser.parse_args()
        research_domain = args.domain
        input_dir = args.input_dir
        db_path = args.output_db
    else:
        research_domain = domain or "methods_tooling"
        input_dir = input_dir or Path("input/pdfs")
        db_path = db_path or Path("db/runs.sqlite")

    # Normalize paths
    input_dir = Path(input_dir)
    db_path = Path(db_path)

    # Initialize DB
    _init_db_schema_if_needed(db_path)

    if not input_dir.exists():
        raise SystemExit(f"Missing folder: {input_dir.resolve()}")

    pdfs = sorted(input_dir.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs")

    if not pdfs:
        raise SystemExit("No PDFs found.")

    db_path.parent.mkdir(parents=True, exist_ok=True)


    with sqlite3.connect(db_path) as con:
        success_count = 0
        for pdf_path in tqdm(pdfs, desc="PDFs"):
            print(f"Processing: {pdf_path.name}")
            try:
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()

                content_hash = sha16(file_bytes.hex())
                source_id = sha16(str(pdf_path) + content_hash)
                file_hash = sha64(str(pdf_path) + content_hash)

                with pdfplumber.open(str(pdf_path)) as pdf:
                    metadata = extract_metadata(pdf_path, pdf)
                    upsert_source(con, source_id, pdf_path.name, metadata)
                    doc_id = insert_document(con, source_id, str(pdf_path), file_hash)
                    for page_idx, page in enumerate(pdf.pages, start=1):
                        text = page.extract_text() or ""
                        if not text.strip():
                            continue
                        section = guess_section(text.lower())
                        chunk_id = insert_chunk(
                            con, source_id, doc_id, page_idx, section, text
                        )
                        for sent in chunk_sentences(text):
                            s_l = sent.lower()
                            quantitative = extract_quantitative_data(sent)
                            tags = detect_method_tags(s_l)
                            decision_taken, decision_driver = detect_decision(s_l)
                            has_failure_phrase = any(
                                p in s_l for lst in FAILURE_PHRASES.values() for p in lst
                            )
                            has_method_tag = bool(tags)
                            has_decision = bool(decision_taken)
                            if not quantitative and not has_failure_phrase and not has_method_tag and not has_decision:
                                continue
                            failure_reason = detect_failure_reason(s_l)
                            outcome = detect_outcome(s_l)
                            stage = guess_stage(s_l)
                            event_type = classify_event_type(
                                s_l, tags, failure_reason, decision_taken
                            )
                            strength = evidence_strength(s_l)
                            entities = extract_entities(sent, research_domain)
                            conf = confidence_score(
                                bool(entities),
                                tags,
                                failure_reason,
                                decision_taken,
                                bool(quantitative),
                                s_l,
                            )
                            event_id = insert_event(
                                con,
                                source_id,
                                doc_id,
                                chunk_id,
                                page_idx,
                                research_domain,
                                event_type,
                                stage,
                                None,
                                None,
                                outcome,
                                failure_reason,
                                decision_taken,
                                decision_driver,
                                sent,
                                strength,
                                conf,
                            )
                            for ent in entities:
                                entity_id = upsert_entity(
                                    con,
                                    ent.get("entity_type"),
                                    ent.get("entity_name"),
                                    ent.get("entity_variant"),
                                    ent.get("organism"),
                                )
                                link_event_entity(
                                    con, event_id, entity_id, ent.get("role", "")
                                )
                            for tag in tags:
                                link_event_tag(con, event_id, tag)
                            for m in quantitative:
                                insert_measurement(con, event_id, m)
                    success_count += 1
            except Exception:
                logging.exception("⚠️ Error processing %s", pdf_path)
        if success_count == 0:
            sys.exit(1)


# ---------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------
if __name__ == "__main__":
    main()

# Re-export for test imports
