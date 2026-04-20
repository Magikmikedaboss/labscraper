from utils.scrape_pdfs_parallel import _db_has_all_tables
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
import logging
import argparse
from utils.db_init import _init_db_schema
import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.pdfexceptions import PDFNotImplementedError
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
    Only initialize schema for non-canonical/test DBs.
    """
    canonical_path = str(Path("db/runs.sqlite").resolve())
    db_path_resolved = str(Path(db_path).resolve())
    logger = logging.getLogger(__name__)
    if db_path_resolved == canonical_path:
        if not _db_has_all_tables(db_path):
            logger.info(f"Canonical DB at {canonical_path} missing schema; initializing with _init_db_schema.")
            _init_db_schema(str(db_path))
        else:
            logger.info(f"Canonical DB at {canonical_path} already initialized; skipping schema init.")
    else:
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

    con = sqlite3.connect(str(db_path), timeout=30.0)
    try:
        success_count = 0
        for pdf_path in tqdm(pdfs, desc="PDFs"):
            print(f"Processing: {pdf_path.name}")
            try:
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()

                # Hash file bytes directly
                content_hash = sha16(file_bytes)
                source_id = content_hash
                file_hash = sha64(file_bytes)

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
                            con, doc_id, page_idx, section, text, source_id
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
                                study_stage=stage,
                                biological_system=None,
                                application_area=None,
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
            except KeyboardInterrupt:
                raise
            except (PDFSyntaxError, PDFNotImplementedError, sqlite3.Error, OSError, ValueError) as e:
                logging.exception("⚠️ %s processing %s: %s", type(e).__name__, pdf_path, e)
                continue
            except Exception:
                logging.exception("Unexpected error processing %s", pdf_path)
                raise
        con.commit()
        if success_count == 0:
            sys.exit(1)
    finally:
        con.close()


# ---------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------
if __name__ == "__main__":
    main()

# Re-export for test imports
