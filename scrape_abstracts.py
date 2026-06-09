#!/usr/bin/env python3
"""Compatibility wrapper for abstract-heavy feeds.

The canonical ingest engine is run_rss_ingest.py. This script remains only
for older workflows that still invoke the abstract-only entry point.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import feedparser

from run_rss_ingest import DB_PATH, FEEDS_CONFIG, ensure_db_schema, load_feeds_config, process_feed_entry
from utils.validators import (
    ValidationError,
    ensure_database_dir,
    validate_database,
    validate_domain_name,
    validate_file_path,
)


logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Compatibility wrapper for abstract-heavy feeds")
    parser.add_argument("--feeds-config", type=Path, default=FEEDS_CONFIG, help="Path to RSS feeds configuration JSON file")
    parser.add_argument("--feed-name", action="append", dest="feed_names", help="Only run feeds whose name matches this value; may be repeated")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="Output database path")
    parser.add_argument("--domain", type=str, default="construction_science", help="Domain for processing")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without actually processing")
    args = parser.parse_args()

    try:
        args.feeds_config = validate_file_path(args.feeds_config, must_exist=False)
        args.db_path = validate_database(args.db_path, must_exist=False)
        args.domain = validate_domain_name(args.domain)
        feeds_config = load_feeds_config(args.feeds_config)
    except ValidationError as exc:
        print(f"❌ Validation error: {exc}")
        sys.exit(1)

    args.db_path = ensure_database_dir(args.db_path)
    if not args.dry_run:
        ensure_db_schema(args.db_path)

    print("⚠️  scrape_abstracts.py is deprecated; using the canonical hybrid ingest path.")
    print("   Prefer run_rss_ingest.py for new work.")
    print()

    feeds = list(feeds_config.get("feeds", []))
    if args.feed_names:
        wanted_names = {name.strip() for name in args.feed_names if name and name.strip()}
        feeds = [feed for feed in feeds if feed.get("name") in wanted_names]
        if not feeds:
            print(f"⚠️  No feeds matched the requested name(s): {', '.join(sorted(wanted_names))}")
            print("   Nothing to do.")
            return

    total_processed = 0
    total_events = 0

    for feed_config in feeds:
        if not feed_config.get("enabled", True):
            continue
        if "url" not in feed_config:
            print(f"⚠️ Skipping feed entry missing 'url': {feed_config}")
            continue

        print(f"📡 {feed_config.get('name', feed_config['url'])}")
        domain = feed_config.get("domain", args.domain)
        feed = feedparser.parse(feed_config["url"])
        entries = getattr(feed, "entries", [])
        print(f"   Found {len(entries)} entries")

        feed_processed = 0
        feed_events = 0
        for entry in entries:
            if args.dry_run:
                continue
            try:
                result = process_feed_entry(entry, domain=domain, db_path=args.db_path, dry_run=False)
            except Exception:
                entry_identifier = entry.get('id') or entry.get('link') or entry.get('title')
                logger.exception(
                    "Failed processing feed entry %r from %s",
                    entry_identifier,
                    feed_config.get("url"),
                )
                continue
            feed_processed += int(result["pdf_processed"] or 0) + int(result["abstract_processed"] or 0)
            feed_events += int(result["pdf_events"] or 0) + int(result["abstract_events"] or 0)

        total_processed += feed_processed
        total_events += feed_events
        print(f"   Summary: {feed_processed} processed, {feed_events} events extracted")
        print()

    print("=" * 60)
    print("HYBRID PROCESSING COMPLETE")
    print(f"Total processed: {total_processed}")
    print(f"Total events extracted: {total_events}")
    print(f"Database: {args.db_path}")

    if args.dry_run:
        print("\n⚠️  This was a dry run - no actual scraping or processing occurred")


if __name__ == "__main__":
    main()
