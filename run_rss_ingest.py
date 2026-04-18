#!/usr/bin/env python3
"""
RSS Feed Ingestion System
"""

from __future__ import annotations

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

    with sqlite3.connect(db_path) as con:
        con.executescript(schema_path.read_text())
        con.commit()

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def load_feeds_config(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_event_key(event_type, entities, page, snippet):
    entity_str = "|".join(
        sorted(f"{e.get('entity_type')}:{e.get('entity_name')}" for e in entities)
    )
    return f"{event_type}|{entity_str}|{page}|{sha16(snippet[:100])}"


def suggested_keep(conf, event_type, failure_reason, decision_taken, tags):
    if conf in ("med", "high"):
        return 1
    if event_type != "other" and (
        failure_reason != "unknown" or decision_taken != "unknown" or bool(tags)
    ):
        return 1
    return 0


def has_signal(sentence_l: str):
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
        # Strategy 1: reuse feed_utils regex (scans summary, content, links)
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

        for url in found_urls:
            pdf_links.append({"url": url, "title": entry.get("title", "")})

    return pdf_links

# ---------------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------------
def download_pdf(url: str, cache_dir: Path):
    cache_dir.mkdir(parents=True, exist_ok=True)

    file_path = cache_dir / f"{hashlib.md5(url.encode()).hexdigest()}.pdf"

    if file_path.exists():
        return file_path

    try:
        headers = {'User-Agent': 'LabScraper/1.0 (+https://yourdomain.example)'}
        r = requests.get(url, timeout=20, headers=headers)
        r.raise_for_status()
        file_path.write_bytes(r.content)
        return file_path
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None

# ---------------------------------------------------------
# PROCESS
# ---------------------------------------------------------
def process_pdf(pdf_path: Path, domain: str, db_path: Path):
    events = 0
    seen = set()

    def is_valid_pdf(path):
        try:
            with open(path, "rb") as f:
                header = f.read(5)
                if header != b"%PDF-":
                    return False
            return True
        except Exception:
            return False

    with sqlite3.connect(db_path) as con:
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                # metadata = extract_metadata(str(pdf_path))
                # Use a content-based hash for source_id
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()
                source_id = sha16(file_bytes.hex())
                doc_id = insert_document(con, source_id, str(pdf_path), sha64(pdf_path.name))
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue

                    section = guess_section(text.lower())
                    chunk_id = insert_chunk(con, source_id, doc_id, i, section, text)

                    for sent in chunk_sentences(text):
                        s_l = sent.lower()

                        # RELAXED: Do not filter by has_signal
                        # if not has_signal(s_l):
                        #     continue

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
                            bool(entities),
                            tags,
                            failure,
                            decision,
                            bool(measurements),
                            s_l
                        )

                        # RELAXED: Do not filter by suggested_keep
                        # if suggested_keep(conf, event_type, failure, decision, tags) == 0:
                        #     continue

                        key = normalize_event_key(event_type, entities, i, sent)

                        if key in seen:
                            continue

                        seen.add(key)

                        event_id = insert_event(
                            con, source_id, doc_id, chunk_id, i,
                            domain, event_type, stage,
                            None, None, outcome,
                            failure, decision, driver,
                            sent, strength, conf
                        )

                        for e in entities:
                            eid = upsert_entity(con, e["entity_type"], e["entity_name"], None, None)
                            link_event_entity(con, event_id, eid, e.get("role", "unknown"))

                        for tag in tags:
                            link_event_tag(con, event_id, tag)

                        for m in measurements:
                            insert_measurement(con, event_id, m)

                        events += 1
        except Exception as e:
            print(f"❌ Failed to process PDF {pdf_path}: {e}")
            return 0
    return events
    return events

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_db_schema(DB_PATH)

    feeds = load_feeds_config(FEEDS_CONFIG)


    for feed in feeds.get("feeds", []):
        if not feed.get("enabled", True):
            continue

        print(f"📡 {feed['name']}")

        links = get_pdf_links_from_feed(feed["url"])
        print(f"[DEBUG] Links found: {len(links)}")

        for item in links:
            print(f"   📄 {item['title']}")

            if args.dry_run:
                continue

            pdf = download_pdf(item["url"], RSS_CACHE_DIR)
            if not pdf:
                continue

            count = process_pdf(pdf, feed.get("domain", "methods_tooling"), DB_PATH)
            print(f"   ✅ {count} events")

            time.sleep(1)


if __name__ == "__main__":
    main()