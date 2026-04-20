import random
"""
Parallel PDF Scraper - Process multiple PDFs simultaneously
Uses multiprocessing to speed up scraping by 4-8x (depending on PDF size/IO)
"""

import multiprocessing as mp
from multiprocessing import Pool
import sqlite3
import argparse
import re
import logging
from pathlib import Path
import pdfplumber
from tqdm import tqdm
from typing import List, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent))


from utils.metadata_utils import extract_metadata
from utils.text_utils import chunk_sentences, guess_stage, guess_section
from utils.data_extractors import extract_quantitative_data
from utils.entities import extract_entities
from utils.event_classification import (
    detect_method_tags,
    detect_failure_reason,
    detect_decision,
    detect_outcome,
    classify_event_type,
    evidence_strength,
    confidence_score,
    FAILURE_PHRASES, DECISION_PHRASES, METHOD_TAGS,
    ConfidenceInput,
)
from utils.db_utils import (
    upsert_source,
    insert_document,
    insert_chunk,
    insert_event,
    link_event_entity,
    link_event_tag,
    insert_measurement,
    upsert_entity
)
from utils.deduplication import normalize_event_key
from utils.common import sha16, sha64
import time

process_logger = logging.getLogger("scrape_pdfs_parallel")

def _connect(db_path: Path) -> sqlite3.Connection:
    """Create a sqlite connection configured for concurrent writes."""
    con = sqlite3.connect(str(db_path), timeout=30.0)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA busy_timeout=30000;")
    return con


def _has_signal(s_l: str) -> bool:
    return (
        any(p in s_l for lst in FAILURE_PHRASES.values() for p in lst)
        or any(p in s_l for lst in DECISION_PHRASES.values() for p in lst)
        or any(p in s_l for lst in METHOD_TAGS.values() for p in lst)
    )


def process_single_pdf(job: Tuple[str, str, str]) -> Tuple[str, int, bool, str]:
    """
    Worker: process one PDF end-to-end.
    Returns: (pdf_name, events_inserted, success, error_message)
    """
    pdf_path_s, domain, db_path_s = job
    pdf_path = Path(pdf_path_s)
    db_path = Path(db_path_s)

    try:
        with _connect(db_path) as con:
            source_id = sha16(f"{pdf_path.name}|{pdf_path.stat().st_size}|{int(pdf_path.stat().st_mtime)}")
            file_hash = sha64(f"{pdf_path.name}|{pdf_path.stat().st_size}|{int(pdf_path.stat().st_mtime)}")

            events_count = 0
            seen_events = set()

            with pdfplumber.open(str(pdf_path)) as pdf:
                metadata = extract_metadata(pdf_path, pdf)

                upsert_source(con, source_id, pdf_path.name, metadata)
                doc_id = insert_document(con, source_id, str(pdf_path.resolve()), file_hash)

                for page_idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue

                    section = guess_section(text.lower())
                    chunk_id = insert_chunk(con, doc_id, page_idx, section, text, source_id)

                    for sent in chunk_sentences(text):
                        s_l = sent.lower()
                        if not _has_signal(s_l):
                            continue


                        tags = detect_method_tags(s_l)
                        failure_reason = detect_failure_reason(s_l)
                        decision_taken, decision_driver = detect_decision(s_l)
                        outcome = detect_outcome(s_l)
                        stage = guess_stage(s_l)
                        event_type = classify_event_type(s_l, tags, failure_reason, decision_taken)
                        strength = evidence_strength(s_l)
                        ents = extract_entities(sent, domain)
                        measurements = extract_quantitative_data(sent)

                        # Use new confidence_score for filtering
                        conf = confidence_score(
                            ConfidenceInput(
                                has_entity=bool(ents),
                                method_tags=tags,
                                failure_reason=failure_reason,
                                decision_taken=decision_taken,
                                has_measurements=bool(measurements),
                                sentence_l=s_l
                            )
                        )
                        if conf == "low":
                            continue

                        event_key = normalize_event_key(event_type, ents, page_idx, sent)
                        if event_key in seen_events:
                            continue
                        seen_events.add(event_key)

                        bio_sys = None
                        if "serum" in tags:
                            bio_sys = "serum/plasma"
                        elif "organoid" in s_l:
                            bio_sys = "organoid"
                        elif "cell line" in s_l or re.search(r'\bcell culture\b|\bcell lines?\b', s_l):
                            bio_sys = "cells"

                        # Add retry logic for SQLite writes
                        event_id = None
                        last_exc = None
                        base_sleep = 0.1
                        for attempt in range(3):
                            try:
                                event_id = insert_event(
                                    con=con,
                                    source_id=source_id,
                                    doc_id=doc_id,
                                    chunk_id=chunk_id,
                                    page_number=page_idx,
                                    domain=domain,
                                    event_type=event_type,
                                    study_stage=stage,
                                    biological_system=bio_sys,
                                    application_area=None,
                                    outcome=outcome,
                                    failure_reason=failure_reason,
                                    decision_taken=decision_taken,
                                    decision_driver=decision_driver,
                                    evidence_snippet=sent,
                                    evidence_strength_v=strength,
                                    confidence_v=conf,
                                )
                                break
                            except sqlite3.OperationalError as e:
                                last_exc = e
                                sleep_time = base_sleep * (2 ** attempt)
                                sleep_time += random.uniform(0, 0.05)
                                time.sleep(sleep_time)
                        else:
                            process_logger.warning(
                                "Failed to insert event after 3 retries: source_id=%s, doc_id=%s, chunk_id=%s, page_idx=%s, event_type=%s, exc=%r",
                                source_id, doc_id, chunk_id, page_idx, event_type, last_exc
                            )
                            continue

                        for t in tags:
                            link_event_tag(con, event_id, t)

                        for e in ents:
                            entity_id = upsert_entity(
                                con,
                                e["entity_type"],
                                e["entity_name"],
                                e.get("entity_variant"),
                                None
                            )
                            link_event_entity(con, event_id, entity_id, e.get("role", "unknown"))

                        for m in measurements:
                            insert_measurement(con, event_id, m)

                        events_count += 1
            con.commit()
            return (pdf_path.name, events_count, True, "")
    except Exception as e:
        return (pdf_path.name, 0, False, str(e))


def _db_has_all_tables(db_path: Path) -> bool:
    """Check if all required tables exist in the DB."""
    required_tables = {
        'sources', 'documents', 'chunks', 'entities',
        'research_events', 'event_entities', 'tags', 'event_tags',
        'quantitative_measurements', 'entity_relationships'
    }
    try:
        with sqlite3.connect(db_path, timeout=30.0) as con:
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = {t[0] for t in tables}
            return required_tables.issubset(table_names)
    except Exception:
        return False

def _ensure_db_schema(db_path: Path) -> None:
    """Ensure the database has the required schema initialized."""
    if _db_has_all_tables(db_path):
        print("✅ Database schema already initialized")
        return
    
    print("🔧 Initializing database schema...")
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    if not schema_path.exists():
        raise SystemExit(f"Schema file not found: {schema_path}")
    
    schema = schema_path.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as con:
        con.executescript(schema)
        con.commit()
    print("✅ Database schema initialized successfully")

def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel PDF Scraper (Phase 1 Enhanced)")
    parser.add_argument("--domain", default="methods_tooling", help="Research domain (methods_tooling, drug_discovery, etc. — do NOT use entity names like peptide)")
    parser.add_argument("--input-dir", type=Path, default=Path("input_pdfs"), help="Directory with PDFs")
    parser.add_argument("--output-db", type=Path, default=Path("db/runs.sqlite"), help="Output DB path")
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (mp.cpu_count() or 2) - 1),
        help="Number of worker processes (default: cpu_count-1)",
    )
    args = parser.parse_args()


    # Guard: prevent entity names as domains
    ENTITY_NAMES = {"peptide", "protein", "cell", "compound", "target", "assay", "model", "indication", "stem_cell"}
    if args.domain.lower() in ENTITY_NAMES:
        print(f"❌ Invalid domain: '{args.domain}'. Do not use entity names as domains. Use a research axis like 'methods_tooling' or 'drug_discovery'.")
        exit(1)

    input_dir: Path = args.input_dir
    db_path: Path = args.output_db
    domain: str = args.domain
    num_workers: int = max(1, args.workers)

    if not input_dir.exists():
        raise SystemExit(f"Missing folder: {input_dir.resolve()}")

    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {input_dir.resolve()}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure DB schema is initialized before launching workers
    _ensure_db_schema(db_path)
    # Prepare jobs (strings are safer to pickle across platforms)
    jobs: List[Tuple[str, str, str]] = [(str(p), domain, str(db_path)) for p in pdfs]

    total_events = 0
    failed: List[Tuple[str, str]] = []

    with Pool(processes=num_workers) as pool:
        for pdf_name, events_count, ok, err in tqdm(
            pool.imap_unordered(process_single_pdf, jobs),
            total=len(jobs),
            desc="PDFs",
        ):
            if ok:
                total_events += events_count
            else:
                failed.append((pdf_name, err))

    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)
    print(f"✅ Total events inserted: {total_events}")
    print(f"✅ Successful PDFs: {len(pdfs) - len(failed)}/{len(pdfs)}")
    print(f"✅ Database: {db_path.resolve()}")

    if failed:
        print(f"\n⚠️  Failed PDFs ({len(failed)}):")
        for pdf_name, err in failed[:10]:
            msg = (err or "").replace("\n", " ")
            print(f"   - {pdf_name}: {msg[:120]}")
        if len(failed) > 10:
            print(f"   ... and {len(failed) - 10} more")

    print("\n" + "=" * 70)
    print("Next step: Run dual-lens export")
    print(f"  python export_dual_lens.py {db_path} {domain}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    mp.freeze_support()  # Windows-safe
    main()
