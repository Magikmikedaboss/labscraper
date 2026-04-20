#!/usr/bin/env python3
"""
RSS Feed Ingestion System
"""
from __future__ import annotations

import sqlite3
from functools import wraps
# ...existing imports...

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

def _process_sentence(con, source_id, doc_id, chunk_id, page_number, domain, i, sent, section, seen):
    s_l = sent.lower()
    if not has_signal(s_l):
        return False

    tags = detect_method_tags(s_l)
    failure = detect_failure_reason(s_l)
    decision, driver = detect_decision(s_l)
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
    key = normalize_event_key(event_type, entities, i, sent)
    if key in seen:
        return False
    seen.add(key)
    event_id = _insert_event(
        con=con,
        source_id=source_id,
        doc_id=doc_id,
        chunk_id=chunk_id,
        page_number=i,
        domain=domain,
        event_type=event_type,
        study_stage=stage,
        biological_system=None,
        application_area=None,
        outcome=outcome,
        failure_reason=failure,
        decision_taken=decision,
        decision_driver=driver,
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
import re
import argparse
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any
import feedparser
import pdfplumber
import requests
from urllib.parse import urlparse
from utils.common import sha16, sha64
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
    insert_document,
    insert_chunk,
    insert_event,
    link_event_entity,
    link_event_tag,
    insert_measurement,
    upsert_entity,
)

DOC_LINK_REGEX = re.compile(r"https?://[^\s<>\"']+\.pdf(?:\?[^\s<>\"']*)?", re.IGNORECASE)

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
FEEDS_CONFIG = PROJECT_ROOT / "config/feeds.json"
DB_PATH = PROJECT_ROOT / "db/rss.sqlite"
RSS_CACHE_DIR = PROJECT_ROOT / "cache/rss"

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
    statements = []
    statement = ""
    for line in schema_sql.splitlines():
        # Skip comments
        if line.strip().startswith("--") or not line.strip():
            continue
        statement += line + "\n"
        if sqlite3.complete_statement(statement):
            statements.append(statement.strip())
            statement = ""

    with sqlite3.connect(db_path) as con:
        try:
            con.execute("BEGIN")
            for sql in statements:
                try:
                    con.execute(sql)
                except sqlite3.Error as e:
                    con.rollback()
                    msg = f"[ensure_db_schema] Error in SQL: {sql[:80]}...\nException: {e}"
                    raise RuntimeError(msg) from e
            con.commit()
        except Exception:
            con.rollback()
            raise

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
    return f"{event_type}|{entity_str}|{page}|{sha16(snippet[:100])}"



def suggested_keep(conf, event_type, failure_reason, decision_taken, tags):
    """
    Suggest whether to keep an event based on confidence and signal features.
    TODO: Extend for future RSS signal filtering (e.g., advanced event triage or reporting).
    """
    if conf in ("med", "high"):
        return 1
    if event_type != "other" and (
        failure_reason != "unknown" or decision_taken != "unknown" or bool(tags)
    ):
        return 1
    return 0


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
                if href and href not in found_urls:
                    found_urls.append(href)

        # Only keep URLs that look like PDFs (accept .pdf in path, even with query strings)
        pdf_urls = [
            url for url in found_urls
            if DOC_LINK_REGEX.search(url) or urlparse(url).path.lower().endswith(".pdf")
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
                        if url not in pdf_urls:
                            pdf_urls.append(url)
            except Exception as e:
                print(f"[DEBUG] Failed to fetch or parse HTML for PDFs: {e}")

        for url in pdf_urls:
            pdf_links.append({"url": url, "title": entry.get("title", "")})

    return pdf_links

# ---------------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------------
def download_pdf(url: str, cache_dir: Path):
    import logging
    from requests.exceptions import Timeout, ConnectionError, HTTPError
    cache_dir.mkdir(parents=True, exist_ok=True)

    file_path = cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.pdf"

    if file_path.exists():
        return file_path

    headers = {'User-Agent': 'LabScraper/1.0 (+https://github.com/labscraper/labscraper; contact: maintainer@labscraper.org)'}
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
            logging.warning(f"Download attempt {attempt} failed (network): {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff *= 2
        except HTTPError as e:
            if r.status_code >= 500 and attempt < max_attempts:
                logging.warning(f"Download attempt {attempt} failed (HTTP {r.status_code}): {e}. Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
                continue
            logging.error(f"❌ Download failed after {attempt} attempts (HTTP {r.status_code}): {e}")
            return None
        except Exception as e:
            logging.error(f"❌ Download failed after {attempt} attempts (unexpected error): {e}")
            return None

# ---------------------------------------------------------
# PROCESS
# ---------------------------------------------------------

def is_valid_pdf(path):
    try:
        with open(path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                return False
        return True
    except Exception:
        return False

def process_pdf(pdf_path: Path, domain: str, db_path: Path):
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
            # Use a content-based hash for source_id (fast version)
            file_bytes = pdf_path.read_bytes()
            source_id = sha16(file_bytes)
            # file_hash = sha64(file_bytes)            # metadata = extract_metadata(str(pdf_path))  # Uncomment if needed

            with pdfplumber.open(str(pdf_path)) as pdf:
                try:
                    doc_id = insert_document(con, source_id, str(pdf_path), sha64(file_bytes))
                    for i, page in enumerate(pdf.pages, start=1):
                        text = page.extract_text() or ""
                        if not text.strip():
                            continue

                        section = guess_section(text.lower())
                        chunk_id = insert_chunk(con, doc_id, i, section, text, source_id)

                        for sent in chunk_sentences(text):
                            added = _process_sentence(
                                con, source_id, doc_id, chunk_id, i, domain, i, sent, section, seen
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
    import gc
    gc.collect()
    return events

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()


    ensure_db_schema(DB_PATH)

    try:
        feeds = load_feeds_config(FEEDS_CONFIG)
    except FileNotFoundError:
        print(f"❌ Feeds config file not found: {FEEDS_CONFIG}")
        feeds = {"feeds": []}
    except RuntimeError as e:
        print(f"❌ Error loading feeds config: {e}")
        feeds = {"feeds": []}

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

            count = process_pdf(pdf, feed.get("domain", "methods_tooling"), DB_PATH)
            print(f"   ✅ {count} events")

            time.sleep(1)


if __name__ == "__main__":
    main()