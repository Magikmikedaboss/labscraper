# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------
from utils.common import get_seeds, load_seed_file, sha256_short, sha256_short_unsafe, sha256_hex
from utils.deduplication import normalize_event_key
from pathlib import Path
import sqlite3
import sys
import logging
import argparse
import re
import secrets
import time
from utils.db_init import init_db_schema
from utils.axon_domains import get_domain_by_id
import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.pdfexceptions import PDFNotImplementedError
from pdfplumber.utils.exceptions import PdfminerException

from tqdm import tqdm
from utils.metadata_utils import extract_metadata
from utils.source_triage import scan_pdf

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

# Re-export for test imports
sha16 = sha256_short_unsafe
sha64 = sha256_hex

__all__ = ["sha16", "sha64", "sha256_short", "sha256_short_unsafe", "sha256_hex", "get_seeds", "load_seed_file"]


CONSTRUCTION_CONTEXT_TERMS = {
    "building",
    "buildings",
    "construction",
    "structural",
    "structure",
    "wall",
    "roof",
    "foundation",
    "slab",
    "beam",
    "column",
    "assembly",
    "envelope",
    "insulation",
    "material",
    "masonry",
    "concrete",
    "steel",
    "frame",
    "facade",
    "cladding",
    "building envelope",
    "roof assembly",
    "wall assembly",
}

CONSTRUCTION_GENERIC_ENTITY_DENYLIST = {
    "temperature",
    "exposure",
    "pressure",
    "humidity",
    "uv",
    "thermal",
}


def _has_construction_context(s_l: str) -> bool:
    return any(term in s_l for term in CONSTRUCTION_CONTEXT_TERMS)

# DB INIT
# ---------------------------------------------------------
def _is_canonical_db(db_path) -> bool:
    canonical_db_path = Path("db/runs.sqlite")
    db_path_obj = Path(db_path)

    try:
        if canonical_db_path.exists() and db_path_obj.exists():
            return db_path_obj.samefile(canonical_db_path)
    except OSError:
        pass

    return db_path_obj.resolve() == canonical_db_path.resolve()


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

    is_canonical_db = _is_canonical_db(db_path_obj)

    if is_canonical_db:
        if not _db_has_all_tables(db_path):
            logger.error(
                "Canonical DB at %s is missing schema; run python init_db.py or python -m init_db first.",
                canonical_path,
            )
            raise SystemExit(f"Canonical DB at {canonical_path} is missing schema. Run python init_db.py or python -m init_db.")
        else:
            logger.info(f"Canonical DB at {canonical_path} already initialized; skipping schema init.")
    else:
        init_db_schema(str(db_path))


def _retry_sqlite_write(action, *args, attempts: int = 3, base_sleep: float = 0.1, **kwargs):
    last_exc = None
    jitter_rng = secrets.SystemRandom()
    for attempt in range(attempts):
        try:
            return action(*args, **kwargs)
        except sqlite3.IntegrityError:
            raise
        except sqlite3.Error as exc:
            last_exc = exc
            if attempt == attempts - 1:
                break
            sleep_time = base_sleep * (2 ** attempt)
            sleep_time += jitter_rng.uniform(0, 0.05)
            time.sleep(sleep_time)

    logger = logging.getLogger(__name__)
    logger.warning("SQLite write failed after %s attempts: %r", attempts, last_exc)
    if last_exc is not None:
        raise last_exc
    raise sqlite3.Error("SQLite write failed without a captured exception")


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


def _is_rss_cache_input(input_dir: Path) -> bool:
    parts = [part.lower() for part in input_dir.parts]
    return len(parts) >= 2 and parts[-2:] == ["cache", "rss"]


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
        raise SystemExit(
            f"Unknown domain '{research_domain}'. Expected a config/domains/{research_domain}.json file."
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

    # Only RSS-cache inputs are triaged here; direct PDF directories are left alone
    # so manually curated construction folders are not filtered twice.
    if research_domain == "construction_science" and _is_rss_cache_input(input_dir):
        triaged_pdfs: list[Path] = []
        skipped_pdfs = 0
        for pdf_path in pdfs:
            try:
                # scan_pdf(...) returns a triage object; keep/skip/review controls whether
                # the PDF is retained, dropped, or counted for manual review downstream.
                triage = scan_pdf(pdf_path, first_pages=4, max_chars=3000)
            except Exception as exc:
                # Unreadable PDFs are treated as skipped inputs and counted with other drops.
                logging.getLogger(__name__).warning(
                    "Construction triage skipped unreadable PDF %s: %s",
                    pdf_path,
                    exc,
                )
                skipped_pdfs += 1
                continue
            if triage.keep_skip_review == "skip":
                skipped_pdfs += 1
                continue
            triaged_pdfs.append(pdf_path)
        logger = logging.getLogger(__name__)
        logger.info(
            "Construction triage kept %s/%s PDFs from %s (skipped %s biomedical PDFs)",
            len(triaged_pdfs),
            len(pdfs),
            input_dir,
            skipped_pdfs,
        )
        # Replace the raw cache list with the triaged subset so all downstream
        # extraction and event generation only sees the approved PDFs.
        pdfs = triaged_pdfs

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
                with pdfplumber.open(str(pdf_path)) as pdf:
                    metadata = extract_metadata(pdf_path, pdf)
                    metadata.setdefault("domain", research_domain)
                    metadata.setdefault("publication_date", metadata.get("year"))
                    source_id = _retry_sqlite_write(upsert_source, con, source_id, pdf_path.name, metadata)
                    doc_id = _retry_sqlite_write(insert_document, con, source_id, str(pdf_path), content_hash)
                    seen_events = set()
                    for page_idx, page in enumerate(pdf.pages, start=1):
                        text = page.extract_text() or ""
                        if not text.strip():
                            continue
                        section = guess_section(text.lower())
                        chunk_id = _retry_sqlite_write(insert_chunk, con, doc_id, page_idx, section, text)
                        for sent in chunk_sentences(text):
                            s_l = sent.lower()
                            quantitative = extract_quantitative_data(sent)
                            if (
                                research_domain == "construction_science"
                                and not _has_construction_context(s_l)
                                and not quantitative
                            ):
                                continue
                            tags = detect_method_tags(s_l)
                            decision_taken = detect_decision(s_l)
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
                            if research_domain == "construction_science":
                                entities = [
                                    entity for entity in entities
                                    if entity.get("entity_name", "").strip().lower() not in CONSTRUCTION_GENERIC_ENTITY_DENYLIST
                                ]
                                if not entities and not quantitative:
                                    continue
                            event_key = normalize_event_key(event_type, entities, page_idx, sent)
                            if event_key in seen_events:
                                continue
                            seen_events.add(event_key)
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
                            event_id = _retry_sqlite_write(
                                insert_event,
                                con=con,
                                source_id=source_id,
                                doc_id=doc_id,
                                chunk_id=chunk_id,
                                page_number=page_idx,
                                domain=research_domain,
                                event_type=event_type,
                                stage=stage,
                                system_context=(
                                    "serum/plasma"
                                    if "serum" in tags
                                    else "organoid"
                                    if "organoid" in s_l
                                    else "cells"
                                    if "cell line" in s_l or re.search(r'\bcell culture\b|\bcell lines?\b', s_l)
                                    else None
                                ),
                                application_context=None,
                                outcome=outcome,
                                failure_reason=failure_reason,
                                decision_taken=decision_taken,
                                decision_driver=None,
                                evidence_snippet=sent,
                                evidence_strength_v=strength,
                                confidence_v=conf,
                            )
                            print(f"[EVENT] {event_type} | conf={conf} | {sent[:60]}")
                            for ent in entities:
                                entity_id = _retry_sqlite_write(
                                    upsert_entity,
                                    con,
                                    ent.get("entity_type"),
                                    ent.get("entity_name"),
                                    ent.get("entity_variant"),
                                    ent.get("organism"),
                                )
                                _retry_sqlite_write(
                                    link_event_entity,
                                    con,
                                    event_id,
                                    entity_id,
                                    ent.get("role", "unknown"),
                                )
                            for tag in tags:
                                _retry_sqlite_write(link_event_tag, con, event_id, tag)
                            for m in quantitative:
                                _retry_sqlite_write(insert_measurement, con, event_id, m)
                # Commit after each PDF is fully processed
                _retry_sqlite_write(con.commit)
                success_count += 1
            except KeyboardInterrupt:
                raise
            except (PDFSyntaxError, PDFNotImplementedError, PdfminerException, sqlite3.Error, OSError, ValueError) as e:
                logging.exception("⚠️ %s processing %s: %s", type(e).__name__, pdf_path, e)
                con.rollback()
                continue
            except Exception:
                logging.exception("Unexpected error processing %s", pdf_path)
                raise
        _retry_sqlite_write(con.commit)
        if success_count == 0:
            sys.exit(1)


# ---------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------
if __name__ == "__main__":
    main()

# Re-export for test imports
