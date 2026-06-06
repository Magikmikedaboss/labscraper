# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------
from utils.common import get_seeds, load_seed_file, sha16, sha64
from pathlib import Path
import sqlite3
import sys
import logging
import argparse
from utils.db_init import init_db_schema
from utils.axon_domains import get_domain_by_id
import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.pdfexceptions import PDFNotImplementedError

# Re-export for test imports
__all__ = ["sha16", "sha64", "get_seeds", "load_seed_file"]
from tqdm import tqdm
from utils.metadata_utils import extract_metadata

# Local utils

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
    ConfidenceInput,
)
from utils.db_utils import (
    _db_has_all_tables,
    upsert_source,
    insert_document,
    insert_chunk,
    upsert_entity,
    insert_event,
    link_event_entity,
    link_event_tag,
    insert_measurement,
)
from utils.scrape_pdfs_parallel import _sha256_file

# DB INIT
# ---------------------------------------------------------
def _init_db_schema_if_needed(db_path):
    """
    Ensure the database at db_path is initialized with the schema.
    For the canonical DB (Path("db/runs.sqlite")), this function checks if required tables are present using _db_has_all_tables;
    if any are missing, it initializes the schema by calling init_db_schema. For non-canonical/test DBs, it always initializes the schema.
    Delegates to utils.db_init.init_db_schema for actual initialization logic.
    This conditional behavior ensures that the canonical DB is only initialized if needed, while test/non-canonical DBs are always initialized.
    """
    canonical_db_path = Path("db/runs.sqlite")
    db_path_obj = Path(db_path)
    canonical_path = str(canonical_db_path.resolve())
    logger = logging.getLogger(__name__)

    # Use samefile when possible to handle symlinks/casing/platform differences.
    try:
        if canonical_db_path.exists() and db_path_obj.exists():
            is_canonical_db = db_path_obj.samefile(canonical_db_path)
        else:
            is_canonical_db = db_path_obj.resolve() == canonical_db_path.resolve()
    except OSError:
        is_canonical_db = db_path_obj.resolve() == canonical_db_path.resolve()

    if is_canonical_db:
        if not _db_has_all_tables(db_path):
            logger.info(f"Canonical DB at {canonical_path} missing schema; initializing with init_db_schema.")
            init_db_schema(str(db_path))
        else:
            logger.info(f"Canonical DB at {canonical_path} already initialized; skipping schema init.")
    else:
        init_db_schema(str(db_path))


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
project_root = Path(__file__).resolve().parent.parent

if (project_root / "input" / "seeds").exists():
    SEEDS_DIR = project_root / "input" / "seeds"
else:
    SEEDS_DIR = project_root / "seeds"






# ---------------------------------------------------------
# MAIN ENGINE
# ---------------------------------------------------------
def _default_input_dir() -> Path:
    data_documents = Path("data/documents")
    if data_documents.exists():
        return data_documents
    return Path("input/pdfs")


def main(domain=None, input_dir=None, db_path=None, lenses=None):

    parser = argparse.ArgumentParser(description="Scrape PDFs for research intelligence")
    parser.add_argument("--domain", default="methods_tooling")
    parser.add_argument("--input-dir", type=Path, default=_default_input_dir())
    parser.add_argument("--output-db", type=Path, default=Path("db/runs.sqlite"))

    if domain is None and input_dir is None and db_path is None:
        args = parser.parse_args()
        research_domain = args.domain
        input_dir = args.input_dir
        db_path = args.output_db
    else:
        research_domain = domain or "methods_tooling"
        input_dir = input_dir or _default_input_dir()
        db_path = db_path or Path("db/runs.sqlite")

    if get_domain_by_id(research_domain) is None:
        logging.getLogger(__name__).warning(
            "Unknown domain '%s'; proceeding with fallback behavior.",
            research_domain,
        )

    # Normalize paths
    input_dir = Path(input_dir)
    db_path = Path(db_path)

    # Ensure DB directory exists before schema init
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize DB (only for non-canonical/test DBs)
    _init_db_schema_if_needed(db_path)

    if not input_dir.exists():
        raise SystemExit(f"Missing folder: {input_dir.resolve()}")

    pdfs = sorted(input_dir.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs")

    if not pdfs:
        raise SystemExit("No PDFs found.")


    with sqlite3.connect(str(db_path), timeout=30.0) as con:
        success_count = 0
        for pdf_path in tqdm(pdfs, desc="PDFs"):
            print(f"Processing: {pdf_path.name}")
            try:
                content_hash = _sha256_file(pdf_path)
                source_id = content_hash
                file_hash = content_hash

                with pdfplumber.open(str(pdf_path)) as pdf:
                    metadata = extract_metadata(pdf_path, pdf)
                    metadata.setdefault("domain", research_domain)
                    metadata.setdefault("publication_date", metadata.get("year"))
                    source_id = upsert_source(con, source_id, pdf_path.name, metadata)
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
                            has_decision = bool(decision_taken) and decision_taken != "unknown"
                            if not quantitative and not has_failure_phrase and not has_method_tag and not has_decision:
                                continue
                            failure_reason = detect_failure_reason(s_l)
                            outcome = detect_outcome(s_l)
                            stage = guess_stage(s_l)
                            event_type = classify_event_type(
                                s_l, tags, failure_reason, decision_taken
                            )
                            strength = evidence_strength(s_l)
                            entities = extract_entities(sent, research_domain, SEEDS_DIR)
                            conf = confidence_score(
                                ConfidenceInput(
                                    has_entity=bool(entities),
                                    method_tags=tags,
                                    failure_reason=failure_reason,
                                    decision_taken=decision_taken,
                                    has_measurements=bool(quantitative),
                                    sentence_l=s_l,
                                )
                            )
                            event_id = insert_event(
                                con=con,
                                source_id=source_id,
                                doc_id=doc_id,
                                chunk_id=chunk_id,
                                page_number=page_idx,
                                domain=research_domain,
                                event_type=event_type,
                                stage=stage,
                                system_context=None,
                                application_context=None,
                                outcome=outcome,
                                failure_reason=failure_reason,
                                decision_taken=decision_taken,
                                decision_driver=decision_driver,
                                evidence_snippet=sent,
                                evidence_strength_v=strength,
                                confidence_v=conf,
                            )
                            print(f"[EVENT] {event_type} | conf={conf} | {sent[:60]}")
                            for ent in entities:
                                entity_id = upsert_entity(
                                    con,
                                    ent.get("entity_type"),
                                    ent.get("entity_name"),
                                    ent.get("entity_variant"),
                                    ent.get("organism"),
                                )
                                link_event_entity(
                                    con, event_id, entity_id, ent.get("role", "unknown")
                                )
                            for tag in tags:
                                link_event_tag(con, event_id, tag)
                            for m in quantitative:
                                insert_measurement(con, event_id, m)
                    success_count += 1
                # Commit after each PDF is fully processed
                con.commit()
            except KeyboardInterrupt:
                raise
            except (PDFSyntaxError, PDFNotImplementedError, sqlite3.Error, OSError, ValueError) as e:
                logging.exception("⚠️ %s processing %s: %s", type(e).__name__, pdf_path, e)
                continue
            except Exception:
                logging.exception("Unexpected error processing %s", pdf_path)
                continue
        con.commit()
        if success_count == 0:
            sys.exit(1)


# ---------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------
if __name__ == "__main__":
    main()

# Re-export for test imports
