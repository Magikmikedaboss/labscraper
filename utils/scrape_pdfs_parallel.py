
import random
import multiprocessing as mp
from multiprocessing import Pool
import sqlite3
import argparse
import re
import logging
import hashlib
from pathlib import Path
import pdfplumber
from tqdm import tqdm
from typing import List, Tuple
import sys
import time

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
    _db_has_all_tables,
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
from utils.common import sha256_hex as _sha64
from utils.db_init import init_db_schema
from utils.source_triage import scan_pdf


def sha64(s):
    """Compatibility shim for tests that monkeypatch module-level sha64."""
    return _sha64(s)

process_logger = logging.getLogger("scrape_pdfs_parallel")

def _connect(db_path: Path) -> sqlite3.Connection:
    """Create a sqlite connection configured for concurrent writes."""
    con = sqlite3.connect(str(db_path), timeout=30.0)
    con.execute("PRAGMA foreign_keys = ON;")
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


def _sha256_file(path: Path, chunk_size: int = 64 * 1024) -> str:
    """Hash a file in chunks to avoid loading large PDFs fully into memory."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _normalize_source_part(value: object) -> str:
    text = str(value).strip().lower()
    return re.sub(r"\s+", " ", text)


def _derive_stable_source_id(pdf_path: Path, metadata: dict) -> str:
    doi = metadata.get("doi")
    if isinstance(doi, str):
        normalized_doi = doi.strip()
        if normalized_doi:
            return normalized_doi

    source_parts = [
        metadata.get("title"),
        metadata.get("authors"),
        metadata.get("year"),
        metadata.get("venue"),
        metadata.get("journal"),
        pdf_path.stem,
    ]
    normalized_parts = [_normalize_source_part(part) for part in source_parts if part not in (None, "")]
    if normalized_parts:
        return _sha64("|".join(normalized_parts))

    return pdf_path.stem


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
            # Track number of events inserted; partial commits are intentional—already-committed rows may remain if a mid-PDF commit fails
            events_count = 0
            seen_events = set()

            with pdfplumber.open(str(pdf_path)) as pdf:
                metadata = extract_metadata(pdf_path, pdf)
                metadata.setdefault("domain", domain)
                metadata.setdefault("publication_date", metadata.get("year"))
                source_id = _derive_stable_source_id(pdf_path, metadata)
                file_hash = _sha256_file(pdf_path)
                resolved_source_id = upsert_source(con, source_id, pdf_path.name, metadata)
                if resolved_source_id != source_id:
                    process_logger.warning(
                        "Source ID remapped for %s: computed=%s resolved=%s",
                        pdf_path.name,
                        source_id,
                        resolved_source_id,
                    )
                source_id = resolved_source_id
                doc_id = insert_document(con, source_id, str(pdf_path.resolve()), file_hash)

                for page_idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue

                    section = guess_section(text.lower())
                    chunk_id = insert_chunk(con, doc_id, page_idx, section, text)

                    for sent in chunk_sentences(text):
                        s_l = sent.lower()
                        if not _has_signal(s_l):
                            continue

                        if domain == "construction_science" and not _has_construction_context(s_l):
                            continue


                        tags = detect_method_tags(s_l)
                        failure_reason = detect_failure_reason(s_l)
                        decision_taken = detect_decision(s_l)
                        outcome = detect_outcome(s_l)
                        stage = guess_stage(s_l)
                        event_type = classify_event_type(s_l, tags, failure_reason, decision_taken)
                        strength = evidence_strength(s_l)
                        ents = extract_entities(sent, domain)
                        if domain == "construction_science":
                            ents = [
                                ent for ent in ents
                                if ent.get("entity_name", "").strip().lower() not in CONSTRUCTION_GENERIC_ENTITY_DENYLIST
                            ]
                            if not ents:
                                continue
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
                                    stage=stage,
                                    system_context=bio_sys,
                                    application_context=None,
                                    outcome=outcome,
                                    failure_reason=failure_reason,
                                    decision_taken=decision_taken,
                                    decision_driver=None,
                                    evidence_snippet=sent,
                                    evidence_strength_v=strength,
                                    confidence_v=conf,
                                )
                                break
                            except sqlite3.IntegrityError:
                                raise
                            except sqlite3.Error as e:
                                last_exc = e
                                sleep_time = base_sleep * (2 ** attempt)
                                sleep_time += random.uniform(0, 0.05)  # nosec B311 - bounded jitter only affects retry backoff
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
                        # Periodically commit every 50 events for durability
                        # Partial commits are intentional—already-committed rows may remain if a mid-PDF commit fails
                        if events_count % 50 == 0:
                            try:
                                con.commit()
                            except sqlite3.Error as commit_exc:
                                con.rollback()
                                return (pdf_path.name, events_count, False, f"Commit failed: {commit_exc}")
            # Final commit after all events for this PDF
            # Partial commits are intentional—already-committed rows may remain if a mid-PDF commit fails
            try:
                con.commit()
            except sqlite3.Error as commit_exc:
                con.rollback()
                return (pdf_path.name, events_count, False, f"Final commit failed: {commit_exc}")
            return (pdf_path.name, events_count, True, "")
    except Exception as e:
        return (pdf_path.name, 0, False, str(e))


def _ensure_db_schema(db_path: Path) -> None:
    """Ensure the database has the required schema initialized."""
    if _db_has_all_tables(db_path):
        print("✅ Database schema already initialized")
        return
    
    print("🔧 Initializing database schema...")
    init_db_schema(db_path)
    print("✅ Database schema initialized successfully")


def _is_rss_cache_input(input_dir: Path) -> bool:
    parts = [part.lower() for part in input_dir.parts]
    return len(parts) >= 2 and parts[-2:] == ["cache", "rss"]

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

    if domain == "construction_science" and _is_rss_cache_input(input_dir):
        triaged_pdfs: list[Path] = []
        skipped_pdfs = 0
        for pdf_path in pdfs:
            try:
                triage = scan_pdf(pdf_path, first_pages=4, max_chars=3000)
            except Exception as exc:
                print(f"⚠️  Construction triage skipped unreadable PDF {pdf_path.name}: {exc}")
                skipped_pdfs += 1
                continue
            if triage.keep_skip_review == "skip":
                skipped_pdfs += 1
                continue
            triaged_pdfs.append(pdf_path)
        print(
            f"🧭 Construction triage kept {len(triaged_pdfs)}/{len(pdfs)} PDFs from {input_dir} "
            f"(skipped {skipped_pdfs} biomedical PDFs)"
        )
        pdfs = triaged_pdfs

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
