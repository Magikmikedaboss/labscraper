#!/usr/bin/env python3
"""
RSS Feed Ingestion System
"""
from __future__ import annotations

import sqlite3
from functools import wraps
import logging
from urllib.parse import urljoin
# ...existing imports...


# ---------------------------------------------------------
# IMPORTS AND SYMBOLS (moved above function definitions)
# ---------------------------------------------------------
import re
import argparse
import hashlib
import json
import sys
## Removed duplicate import of sqlite3
import time
from pathlib import Path
from typing import Any
import feedparser
import pdfplumber
import requests
from utils.common import sha256_hex
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
    FAILURE_PHRASES,
    DECISION_PHRASES,
    METHOD_TAGS,
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
    upsert_entity,
)

# ---------------------------------------------------------
# DB ERROR HANDLING DECORATOR
# ---------------------------------------------------------
def db_operational_error_handler(context_msg):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as oe:
                print(f"\u274c DB error during {context_msg}: {oe}")
                if "no such table" in str(oe):
                    print(f"   \u2192 Table missing: {context_msg}")
                raise
        return wrapper
    return decorator

# ---------------------------------------------------------
# PER-SENTENCE PROCESSING
# ---------------------------------------------------------
@db_operational_error_handler("insert_event")
def _insert_event(*args, **kwargs):
    return insert_event(*args, **kwargs)

@db_operational_error_handler("upsert_entity/link_event_entity")
def _upsert_and_link_entity(con, event_id, e):
    eid = upsert_entity(con, e["entity_type"], e["entity_name"], None, None)
    link_event_entity(con, event_id, eid, e.get("role", "unknown"))

@db_operational_error_handler("link_event_tag")
def _link_event_tag(con, event_id, tag):
    link_event_tag(con, event_id, tag)

@db_operational_error_handler("insert_measurement")
def _insert_measurement(con, event_id, m):
    insert_measurement(con, event_id, m)


def _resolve_pdf_url(base_url: str, url: str) -> str:
    return urljoin(base_url, url) if url else url

def _process_sentence(con, source_id, doc_id, chunk_id, page_number, domain, sent, section, seen):
    s_l = sent.lower()
    if not has_signal(s_l):
        return False

    tags = detect_method_tags(s_l)
    failure = detect_failure_reason(s_l)
    decision = detect_decision(s_l)
    outcome = detect_outcome(s_l)
    stage = guess_stage(s_l)
    event_type = classify_event_type(s_l, tags, failure, decision)
    strength = evidence_strength(s_l)
    entities = extract_entities(sent, domain)
    measurements = extract_quantitative_data(sent)
    conf = confidence_score(
        ConfidenceInput(
            has_entity=bool(entities),
            method_tags=tags,
            failure_reason=failure,
            decision_taken=decision,
            has_measurements=bool(measurements),
            sentence_l=s_l,
        )
    )
    # SMART FILTER: Only keep if at least one signal
    if not (entities or tags or measurements):
        return False
    key = normalize_event_key(event_type, entities, page_number, sent)
    if key in seen:
        return False
    seen.add(key)
    event_id = _insert_event(
        con=con,
        source_id=source_id,
        doc_id=doc_id,
        chunk_id=chunk_id,
        page_number=page_number,
        domain=domain,
        event_type=event_type,
        stage=stage,
        system_context=None,
        application_context=None,
        outcome=outcome,
        failure_reason=failure,
        decision_taken=decision,
        decision_driver=None,
        evidence_snippet=sent,
        evidence_strength_v=strength,
        confidence_v=conf,
    )
    for e in entities:
        _upsert_and_link_entity(con, event_id, e)
    for tag in tags:
        _link_event_tag(con, event_id, tag)
    for m in measurements:
        _insert_measurement(con, event_id, m)
    return True

DOC_LINK_REGEX = re.compile(
    r"(?:https?://)?[^\s<>\"']+\.pdf(?:\?[^\s<>\"']*)?(?:#[^\s<>\"']*)?",
    re.IGNORECASE,
)

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
FEEDS_CONFIG = PROJECT_ROOT / "config/feeds.json"
DB_PATH = PROJECT_ROOT / "db/rss.sqlite"
DATA_ROOT = PROJECT_ROOT / "data"
RSS_CACHE_DIR = (DATA_ROOT / "cache" / "rss") if DATA_ROOT.exists() else (PROJECT_ROOT / "cache" / "rss")

# ---------------------------------------------------------
# IMPORT PIPELINE
# ---------------------------------------------------------

# ---------------------------------------------------------
# DB INIT
# ---------------------------------------------------------
def ensure_db_schema(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_path = PROJECT_ROOT / "schema.sql"
    if not schema_path.exists():
        raise SystemExit(f"Missing schema file: {schema_path}")

    schema_sql = schema_path.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as con:
        try:
            con.executescript(schema_sql)
            _apply_rename_context_columns_migration_if_needed(con)
            con.commit()
        except sqlite3.Error as e:
            con.rollback()
            raise RuntimeError(f"[ensure_db_schema] Error executing schema script: {e}") from e


def _apply_rename_context_columns_migration_if_needed(con: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in con.execute("PRAGMA table_info(research_events)").fetchall()
    }
    legacy_cols = {"study_stage", "biological_system", "application_area"}
    target_cols = {"stage", "system_context", "application_context"}
    if legacy_cols.issubset(columns) and target_cols.isdisjoint(columns):
        migration_sql = (PROJECT_ROOT / "migrations" / "01_rename_research_event_context_columns.sql").read_text(encoding="utf-8")
        con.executescript(migration_sql)
# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def load_feeds_config(path: Path) -> dict[str, Any]:

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Malformed JSON in feeds config file {path}: {e}")


def normalize_event_key(event_type, entities, page, snippet):
    entity_str = "|".join(
        sorted(f"{e.get('entity_type')}:{e.get('entity_name')}" for e in entities)
    )
    return f"{event_type}|{entity_str}|{page}|{sha256_hex(snippet)}"


def has_signal(sentence_l: str):
    """
    Check if a sentence contains signal phrases.
    
    TODO: keep for future RSS signal filtering (e.g., for pre-filtering sentences before event extraction)
    """
    return (
        any(p in sentence_l for lst in FAILURE_PHRASES.values() for p in lst)
        or any(p in sentence_l for lst in DECISION_PHRASES.values() for p in lst)
        or any(p in sentence_l for lst in METHOD_TAGS.values() for p in lst)
    )
# ---------------------------------------------------------
# RSS
# ---------------------------------------------------------
def get_pdf_links_from_feed(feed_url: str):
    from utils.feed_utils import extract_pdf_links

    feed = feedparser.parse(feed_url)
    pdf_links = []

    for entry in feed.entries:
        # Uncomment for debugging:
        # print("[DEBUG] Feed entry:", json.dumps(entry, default=str, indent=2))
        found_urls = extract_pdf_links(entry)

        # Strategy 2: arXiv abstract URL → PDF URL conversion
        entry_link = entry.get("link", "")
        if "arxiv.org/abs/" in entry_link:
            arxiv_pdf = entry_link.replace("/abs/", "/pdf/") + ".pdf"
            if arxiv_pdf not in found_urls:
                found_urls.append(arxiv_pdf)

        # Strategy 3: check link elements for type=application/pdf or title=pdf (Atom feeds)
        for link in entry.get("links", []):
            href = link.get("href", "")
            if (
                "application/pdf" in link.get("type", "")
                or link.get("title", "").lower() == "pdf"
            ):
                resolved_href = _resolve_pdf_url(entry_link, href)
                if resolved_href and resolved_href not in found_urls:
                    found_urls.append(resolved_href)

        # Only keep URLs that look like PDFs (accept .pdf in path, even with query strings)
        pdf_urls = [
            url for url in found_urls
            if DOC_LINK_REGEX.search(url)
        ]

        # If no direct PDF links found, try fetching the HTML page and searching for PDFs
        if not pdf_urls and entry_link:
            try:
                print(f"[DEBUG] Fetching HTML page for PDF discovery: {entry_link}")
                resp = requests.get(entry_link, timeout=10)
                if resp.ok:
                    html = resp.text
                    html_pdfs = DOC_LINK_REGEX.findall(html)
                    for url in html_pdfs:
                        resolved_url = _resolve_pdf_url(entry_link, url)
                        if resolved_url not in pdf_urls:
                            pdf_urls.append(resolved_url)
            except Exception as e:
                print(f"[DEBUG] Failed to fetch or parse HTML for PDFs: {e}")

        for url in pdf_urls:
            pdf_links.append({"url": url, "title": entry.get("title", "")})

    return pdf_links

# ---------------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------------
def download_pdf(url: str, cache_dir: Path):
    from requests.exceptions import Timeout, ConnectionError, HTTPError

    cache_dir.mkdir(parents=True, exist_ok=True)
    file_path = cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.pdf"

    if file_path.exists():
        return file_path

    headers = {
        "User-Agent": "LabScraper/1.0 (+https://github.com/labscraper/labscraper)"
    }

    max_attempts = 3
    backoff = 1

    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.get(url, timeout=20, headers=headers)
            r.raise_for_status()
            file_path.write_bytes(r.content)
            return file_path

        except (Timeout, ConnectionError) as e:
            if attempt == max_attempts:
                logging.error(f"❌ Download failed after {attempt} attempts: {e}")
                return None

            logging.warning(
                f"Network error (attempt {attempt}): {e}. Retrying in {backoff}s..."
            )
            time.sleep(backoff)
            backoff *= 2

        except HTTPError as e:
            status_code = getattr(e.response, "status_code", "unknown")

            if status_code != "unknown" and status_code >= 500 and attempt < max_attempts:
                logging.warning(
                    f"Server error {status_code} (attempt {attempt}). Retrying in {backoff}s..."
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            logging.error(
                f"❌ HTTP error after {attempt} attempts ({status_code}): {e}"
            )
            return None

        except Exception as e:
            logging.error(f"❌ Unexpected error after {attempt} attempts: {e}")
            if attempt == max_attempts:
                return None
            logging.warning(
                f"Unexpected error (attempt {attempt}): {e}. Retrying in {backoff}s..."
            )
            time.sleep(backoff)
            backoff *= 2
            continue

# ---------------------------------------------------------
# PROCESS
# ---------------------------------------------------------

def is_valid_pdf(path):
    try:
        with open(path, "rb") as f:
            header = f.read(5)
            is_pdf = header == b"%PDF-"
        return is_pdf
    except Exception:
        return False

def process_pdf(
    pdf_path: Path,
    domain: str,
    db_path: Path,
    source_url: str | None = None,
    source_title: str | None = None,
):
    events = 0
    seen = set()

    required_tables = [
        "sources", "documents", "chunks", "entities", "research_events",
        "event_entities", "tags", "event_tags", "quantitative_measurements"
    ]

    def check_required_tables(con):
        missing = []
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}
        for t in required_tables:
            if t not in tables:
                missing.append(t)
        return missing

    with sqlite3.connect(db_path) as con:
        # Preflight: check for required tables
        missing_tables = check_required_tables(con)
        if missing_tables:
            print(f"❌ Database schema is missing required tables: {', '.join(missing_tables)}.\n       Please run ensure_db_schema or check your schema migrations.")
            return 0
        try:
            # Stream file hashing to avoid high memory use for large PDFs.
            h = hashlib.sha256()
            with open(pdf_path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            file_hash = h.hexdigest()
            # Use a deterministic hash-derived base id; upsert_source may return a canonical existing id.
            initial_source_id = file_hash[:16]
            metadata = {
                "title": source_title or pdf_path.stem,
                "url": source_url,
                "domain": domain,
            }
            if source_url:
                doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9<>%+,]+", source_url, re.I)
                if doi_match:
                    metadata["doi"] = doi_match.group(0).rstrip(".,;:")
            source_id = upsert_source(con, initial_source_id, str(pdf_path), metadata)

            with pdfplumber.open(str(pdf_path)) as pdf:
                try:
                    doc_id = insert_document(con, source_id, str(pdf_path), file_hash)
                    for i, page in enumerate(pdf.pages, start=1):
                        text = page.extract_text() or ""
                        if not text.strip():
                            continue

                        section = guess_section(text.lower())
                        chunk_id = insert_chunk(con, source_id, doc_id, i, section, text)

                        for sent in chunk_sentences(text):
                            added = _process_sentence(
                                con, source_id, doc_id, chunk_id, i, domain, sent, section, seen
                            )
                            if added:
                                events += 1
                except sqlite3.OperationalError as oe:
                    print(f"❌ DB schema error: {oe}")
                    if 'no such table' in str(oe):
                        print("   → One or more required tables are missing. Run ensure_db_schema or check your migrations.")
                    return 0
        except Exception as e:
            print(f"❌ Failed to process PDF {pdf_path}: {e}")
            return 0
    return events

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--feeds", default=str(FEEDS_CONFIG), help="Path to feeds.json")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to SQLite database")
    args = parser.parse_args()

    feeds_config_path = Path(args.feeds)
    db_path = Path(args.db)


    ensure_db_schema(db_path)

    try:
        feeds = load_feeds_config(feeds_config_path)
    except FileNotFoundError:
        print(f"❌ Feeds config file not found: {feeds_config_path}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ Error loading feeds config: {e}")
        sys.exit(1)

    for feed in feeds.get("feeds", []):
        if not feed.get("enabled", True):
            continue

        if "url" not in feed:
            print(f"⚠️ Skipping feed entry missing 'url': {feed}")
            continue

        print(f"📡 {feed.get('name', feed['url'])}")

        links = get_pdf_links_from_feed(feed["url"])
        print(f"[DEBUG] Links found: {len(links)}")

        for item in links:
            print(f"   📄 {item['title']}")

            if args.dry_run:
                continue

            pdf = download_pdf(item["url"], RSS_CACHE_DIR)
            if not pdf:
                continue

            if not is_valid_pdf(pdf):
                print("⚠️ Skipping invalid PDF")
                continue

            count = process_pdf(
                pdf,
                feed.get("domain", "methods_tooling"),
                db_path,
                source_url=item.get("url"),
                source_title=item.get("title"),
            )
            print(f"   ✅ {count} events")

            time.sleep(1)


if __name__ == "__main__":
    main()