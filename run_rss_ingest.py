#!/usr/bin/env python3
"""
RSS Feed Ingestion System

Downloads and processes RSS feeds, extracts PDFs, and processes them
through the modular pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import feedparser
import pdfplumber
import requests


# ---------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
FEEDS_CONFIG = Path("config/feeds.json")
DB_PATH = Path("db/rss.sqlite")
RSS_CACHE_DIR = Path("cache/rss")


# ---------------------------------------------------------
# IMPORTS: VALIDATORS
# ---------------------------------------------------------
from utils.validators import (
    ValidationError,
    validate_database,
    validate_directory,
    validate_domain_name,
    validate_file_path,
)

# ---------------------------------------------------------
# IMPORTS: MODULAR PIPELINE
# ---------------------------------------------------------
from utils.common import sha16, sha64
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
    FAILURE_PHRASES,
    DECISION_PHRASES,
    METHOD_TAGS,
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
# LOCAL HELPERS
# ---------------------------------------------------------
def load_feeds_config(path: Path) -> dict[str, Any]:
    """Load RSS feed configuration JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_event_key(event_type: str, entities: list[dict], page: int, snippet: str) -> str:
    """Create a stable event key for per-document deduplication."""
    entity_str = "|".join(
        sorted(f"{e.get('entity_type', '')}:{e.get('entity_name', '')}" for e in entities)
    )
    snippet_hash = sha16(snippet[:100])
    return f"{event_type}|{entity_str}|{page}|{snippet_hash}"


def suggested_keep(
    conf: str,
    event_type: str,
    failure_reason: str,
    decision_taken: str,
    tags: list[str],
) -> int:
    """Simple keep rule for event retention."""
    if conf in ("med", "high"):
        return 1
    if event_type != "other" and (
        failure_reason != "unknown" or decision_taken != "unknown" or bool(tags)
    ):
        return 1
    return 0


def ensure_db_schema(db_path: Path) -> None:
    """Initialize schema.sql if key tables do not exist yet."""

    required_tables = {
        "sources",
        "documents",
        "chunks",
        "entities",
        "research_events",
        "event_entities",
        "tags",
        "event_tags",
        "quantitative_measurements",
    }

    print(f"[DEBUG] ensure_db_schema called with db_path: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sqlite3.connect(db_path) as con:
            rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            existing = {r[0] for r in rows}
            print(f"[DEBUG] Existing tables: {existing}")
            if required_tables.issubset(existing):
                print("[DEBUG] All required tables exist. Skipping schema initialization.")
                return
            else:
                print("[DEBUG] Missing tables detected. Will initialize schema.")
    except Exception as e:
        print(f"[DEBUG] Exception while checking tables: {e}")

    schema_path = PROJECT_ROOT / "schema.sql"
    print(f"[DEBUG] Using schema_path: {schema_path}")
    if not schema_path.exists():
        print(f"[DEBUG] Schema file missing: {schema_path}")
        raise SystemExit(f"Missing schema file: {schema_path}")

    schema_sql = schema_path.read_text(encoding="utf-8")
    try:
        with sqlite3.connect(db_path) as con:
            con.executescript(schema_sql)
            con.commit()
        print("[DEBUG] Schema initialized successfully.")
    except Exception as e:
        print(f"[DEBUG] Exception during schema initialization: {e}")


def has_signal(sentence_l: str) -> bool:
    """Fast screen for potentially meaningful sentences."""
    return (
        any(p in sentence_l for lst in FAILURE_PHRASES.values() for p in lst)
        or any(p in sentence_l for lst in DECISION_PHRASES.values() for p in lst)
        or any(p in sentence_l for lst in METHOD_TAGS.values() for p in lst)
    )


# ---------------------------------------------------------
# RSS / FEED EXTRACTION
# ---------------------------------------------------------
def get_pdf_links_from_feed(feed_url: str) -> list[dict[str, str]]:
    """Extract candidate PDF links from an RSS/Atom feed."""
    try:
        feed = feedparser.parse(feed_url)
        pdf_links: list[dict[str, str]] = []

        for entry in feed.entries:
            links: list[str] = []

            for link in entry.get("links", []):
                href = link.get("href", "")
                if not href:
                    continue

                href_l = href.lower()

                if ".pdf" in href_l:
                    links.append(href)
                    continue

                if "arxiv.org" in href_l:
                    parsed = requests.utils.urlparse(href)
                    path = parsed.path

                    if "/abs/" in path:
                        path = path.replace("/abs/", "/pdf/")
                    elif "/pdf/" not in path:
                        path = path.rstrip("/") + "/pdf/"

                    if not path.endswith(".pdf"):
                        path += ".pdf"

                    pdf_url = parsed._replace(path=path).geturl()
                    links.append(pdf_url)

            summary = entry.get("summary", "")
            links.extend(re.findall(r'https?://[^\s<>"\']*\.pdf', summary, re.IGNORECASE))

            for content in entry.get("content", []):
                content_value = content.get("value", "")
                links.extend(
                    re.findall(r'https?://[^\s<>"\']*\.pdf', content_value, re.IGNORECASE)
                )

            seen = set()
            for link in links:
                link = link.strip()
                if not link or link.startswith("#"):
                    continue

                if not link.startswith("http"):
                    link = requests.compat.urljoin(feed_url, link)

                if link in seen:
                    continue
                seen.add(link)

                pdf_links.append(
                    {
                        "url": link,
                        "title": entry.get("title", ""),
                        "published": entry.get("published", ""),
                        "summary": entry.get("summary", "")[:200],
                    }
                )

        return pdf_links

    except Exception as e:
        print(f"❌ Error parsing feed {feed_url}: {e}")
        return []


# ---------------------------------------------------------
# PDF DOWNLOAD
# ---------------------------------------------------------
def download_pdf(pdf_url: str, cache_dir: Path) -> Path | None:
    """Download a PDF into the cache directory."""
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)

        url_hash = hashlib.md5(pdf_url.encode("utf-8")).hexdigest()
        cache_file = cache_dir / f"{url_hash}.pdf"

        if cache_file.exists():
            print(f"  📥 Using cached PDF: {cache_file.name}")
            return cache_file

        print(f"  📥 Downloading PDF: {pdf_url}")
        response = requests.get(
            pdf_url,
            timeout=30,
            stream=True,
            headers={"User-Agent": "labscraper-rss-ingest/1.0"},
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()

        # peek first chunk safely
        first_chunk = next(response.iter_content(chunk_size=8192), b"")
        if "pdf" not in content_type and not first_chunk.startswith(b"%PDF"):
            print(f"  ⚠️  Not a PDF file: {pdf_url}")
            return None

        with open(cache_file, "wb") as f:
            if first_chunk:
                f.write(first_chunk)
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print(f"  ✅ Downloaded: {cache_file.name}")
        return cache_file

    except Exception as e:
        print(f"  ❌ Failed to download {pdf_url}: {e}")
        return None


# ---------------------------------------------------------
# PDF PROCESSING
# ---------------------------------------------------------
def process_pdf_with_engine(pdf_path: Path, domain: str, db_path: Path) -> int:
    """Process one cached PDF through the extraction pipeline."""
    try:
        file_size = pdf_path.stat().st_size
        file_mtime = int(pdf_path.stat().st_mtime)

        source_id = sha16(f"{pdf_path.name}|{file_size}|{file_mtime}")
        file_hash = sha64(f"{pdf_path.name}|{file_size}|{file_mtime}")

        events_count = 0
        seen_events: set[str] = set()

        with sqlite3.connect(db_path) as con:
            with pdfplumber.open(str(pdf_path)) as pdf:
                metadata = extract_metadata(str(pdf_path))
                upsert_source(con, source_id, pdf_path.name, metadata)
                doc_id = insert_document(con, source_id, str(pdf_path.resolve()), file_hash)

                for page_idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue

                    section = guess_section(text.lower())
                    chunk_id = insert_chunk(con, source_id, doc_id, page_idx, section, text)

                    for sent in chunk_sentences(text):
                        s_l = sent.lower()
                        if not has_signal(s_l):
                            continue

                        tags = detect_method_tags(s_l)
                        failure_reason = detect_failure_reason(s_l)
                        decision_taken, decision_driver = detect_decision(s_l)
                        outcome = detect_outcome(s_l)
                        stage = guess_stage(s_l)
                        event_type = classify_event_type(s_l, tags, failure_reason, decision_taken)
                        strength = evidence_strength(s_l)

                        entities = extract_entities(sent, domain)
                        measurements = extract_quantitative_data(sent)

                        conf = confidence_score(
                            bool(entities),
                            tags,
                            failure_reason,
                            decision_taken,
                            bool(measurements),
                            s_l,
                        )
                        keep = suggested_keep(conf, event_type, failure_reason, decision_taken, tags)

                        if keep == 0 and event_type == "other":
                            continue

                        event_key = normalize_event_key(event_type, entities, page_idx, sent)
                        if event_key in seen_events:
                            continue
                        seen_events.add(event_key)

                        bio_sys = None
                        if "serum" in tags:
                            bio_sys = "serum/plasma"
                        elif "organoid" in s_l:
                            bio_sys = "organoid"
                        elif "cell line" in s_l or re.search(r"\bcell culture\b|\bcell lines?\b", s_l):
                            bio_sys = "cells"

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

                        for tag in tags:
                            link_event_tag(con, event_id, tag)

                        for entity in entities:
                            entity_id = upsert_entity(
                                con,
                                entity["entity_type"],
                                entity["entity_name"],
                                entity.get("entity_variant"),
                                None,
                            )
                            link_event_entity(con, event_id, entity_id, entity.get("role", "unknown"))

                        for measurement in measurements:
                            insert_measurement(con, event_id, measurement)

                        events_count += 1

            con.commit()

        return events_count

    except Exception as e:
        print(f"  ❌ Error processing {pdf_path}: {e}")
        return 0


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="RSS Feed Ingestion System")
    parser.add_argument(
        "--feeds-config",
        type=Path,
        default=FEEDS_CONFIG,
        help="Path to RSS feeds configuration JSON file",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DB_PATH,
        help="Output database path",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=RSS_CACHE_DIR,
        help="Cache directory for downloaded PDFs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading or processing",
    )
    parser.add_argument(
        "--domain",
        type=str,
        help="Override domain for all feeds",
    )

    args = parser.parse_args()

    try:
        args.feeds_config = validate_file_path(args.feeds_config, must_exist=False)
        args.db_path = validate_database(args.db_path, must_exist=False)
        args.cache_dir = validate_directory(args.cache_dir, must_exist=False)
        if args.domain:
            args.domain = validate_domain_name(args.domain)

        feeds_config = load_feeds_config(args.feeds_config)

    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        sys.exit(1)

    args.db_path.parent.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    ensure_db_schema(args.db_path)

    print("📡 RSS FEED INGESTION SYSTEM")
    print("=" * 50)
    print(f"Database: {args.db_path}")
    print(f"Cache: {args.cache_dir}")
    print(f"Feeds config: {args.feeds_config}")
    print()

    total_downloaded = 0
    total_processed = 0

    for feed_config in feeds_config.get("feeds", []):
        if not feed_config.get("enabled", True):
            print(f"⏭️  Skipping disabled feed: {feed_config.get('name', 'Unnamed feed')}")
            continue

        feed_name = feed_config.get("name", "Unnamed feed")
        feed_url = feed_config["url"]
        domain = args.domain if args.domain else feed_config.get("domain", "methods_tooling")

        print(f"📡 Processing feed: {feed_name}")
        print(f"   URL: {feed_url}")
        print(f"   Domain: {domain}")

        pdf_links = get_pdf_links_from_feed(feed_url)
        print(f"   Found {len(pdf_links)} PDF links")

        if not pdf_links:
            print("   No PDFs found, skipping...")
            print()
            continue

        feed_downloaded = 0
        feed_processed = 0

        for pdf_info in pdf_links:
            pdf_url = pdf_info["url"]
            pdf_title = pdf_info.get("title", "")

            print(f"   📄 {pdf_title}")
            print(f"      URL: {pdf_url}")

            if args.dry_run:
                print("      [DRY RUN] Would download and process")
                feed_downloaded += 1
                feed_processed += 1
                continue

            cache_file = download_pdf(pdf_url, args.cache_dir)
            if not cache_file:
                continue

            feed_downloaded += 1

            events_count = process_pdf_with_engine(cache_file, domain, args.db_path)
            if events_count > 0:
                feed_processed += 1
                print(f"      ✅ Processed: {events_count} events")
            else:
                print("      ⚠️  No events extracted")

        total_downloaded += feed_downloaded
        total_processed += feed_processed

        print(f"   Summary: {feed_downloaded} downloaded, {feed_processed} processed")
        print()

        time.sleep(2)

    print("=" * 50)
    print("RSS INGESTION COMPLETE")
    print(f"Total downloaded: {total_downloaded}")
    print(f"Total processed: {total_processed}")
    print(f"Database: {args.db_path}")

    if args.dry_run:
        print("\n⚠️  This was a dry run. No actual downloads or processing occurred.")


if __name__ == "__main__":
    main()