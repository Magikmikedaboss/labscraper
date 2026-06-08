#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from pdfminer.pdfexceptions import PDFNotImplementedError
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException

from run_rss_ingest import RSS_CACHE_DIR, download_pdf, get_pdf_links_from_entry, load_feeds_config
from utils.feed_utils import parse_feed
from utils.site_collectors import collect_documents, extract_pdf_links_from_page
from utils.source_triage import scan_pdf


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_FEEDS_CONFIG = PROJECT_ROOT / "config" / "feeds.json"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "exports" / "source_quality" / "construction_science_feed_quality.csv"
DEFAULT_OUTPUT_MD = PROJECT_ROOT / "exports" / "source_quality" / "construction_science_feed_quality.md"
DOMAIN_BUCKETS = [
    "construction_science",
    "materials_science",
    "physics",
    "biomedical",
    "mixed",
    "unknown",
]

SCAN_ERRORS = (PDFSyntaxError, PDFNotImplementedError, PdfminerException, OSError, ValueError)

logger = logging.getLogger(__name__)


def _percent(part: int, whole: int) -> str:
    if whole <= 0:
        return "0.0"
    return f"{(part / whole) * 100:.1f}"


def _resolve_feed_entries(feed: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        parsed = parse_feed(feed["url"], timeout=int(feed.get("request_timeout", 20)))
    except Exception as exc:
        logger.warning("Failed to resolve feed entries for %s: %s", feed.get("url", "<missing>"), exc, exc_info=True)
        return []
    if isinstance(parsed, dict):
        return list(parsed.get("entries", []))
    return list(getattr(parsed, "entries", []))


def _is_collector(feed: dict[str, Any]) -> bool:
    return str(feed.get("source_kind", "rss")).strip().lower() == "collector"


def _summarize_feed(feed: dict[str, Any], limit: int | None = None) -> dict[str, Any]:
    domain_counts = Counter()
    triage_counts = Counter()
    entries_found = 0
    html_pages_collected = 0
    html_pages_scanned = 0
    pdf_links_found = 0
    pdfs_downloaded = 0
    pdfs_attempted = 0
    seen_pdf_urls: set[str] = set()

    if _is_collector(feed):
        collected_documents = collect_documents(
            feed["url"],
            max_pages=int(feed.get("max_pages", 20)),
            same_domain_only=bool(feed.get("same_domain_only", True)),
            same_path_prefix=feed.get("same_path_prefix"),
            max_depth=int(feed.get("collector_max_depth", 1)),
            request_timeout=int(feed.get("request_timeout", 20)),
            max_seconds=int(feed.get("collector_timeout_seconds", 60)),
        )
        entries_found = len(collected_documents)
        html_pages_collected = len(collected_documents)

        for document in collected_documents:
            html_pages_scanned += 1
            for pdf_url in extract_pdf_links_from_page(document.url, timeout=int(feed.get("request_timeout", 20))):
                if pdf_url in seen_pdf_urls:
                    continue
                seen_pdf_urls.add(pdf_url)
                pdf_links_found += 1

                if limit is not None and pdfs_attempted >= limit:
                    continue

                pdf_path = download_pdf(pdf_url, RSS_CACHE_DIR)
                pdfs_attempted += 1
                if not pdf_path:
                    triage_counts["review"] += 1
                    domain_counts["unknown"] += 1
                    continue

                pdfs_downloaded += 1
                try:
                    triage = scan_pdf(pdf_path)
                except SCAN_ERRORS:
                    logger.exception("Failed to scan PDF %s during collector quality analysis", pdf_path)
                    triage_counts["review"] += 1
                    domain_counts["unknown"] += 1
                    continue

                triage_counts[triage.keep_skip_review] += 1
                domain_counts[triage.detected_domain] += 1
    else:
        entries = _resolve_feed_entries(feed)
        entries_found = len(entries)

        for entry in entries:
            for pdf_url in get_pdf_links_from_entry(entry):
                if pdf_url in seen_pdf_urls:
                    continue
                seen_pdf_urls.add(pdf_url)
                pdf_links_found += 1

                if limit is not None and pdfs_attempted >= limit:
                    continue

                pdf_path = download_pdf(pdf_url, RSS_CACHE_DIR)
                pdfs_attempted += 1
                if not pdf_path:
                    triage_counts["review"] += 1
                    domain_counts["unknown"] += 1
                    continue

                pdfs_downloaded += 1
                try:
                    triage = scan_pdf(pdf_path)
                except SCAN_ERRORS:
                    logger.exception("Failed to scan PDF %s during RSS quality analysis", pdf_path)
                    triage_counts["review"] += 1
                    domain_counts["unknown"] += 1
                    continue

                triage_counts[triage.keep_skip_review] += 1
                domain_counts[triage.detected_domain] += 1

    return {
        "feed_name": feed.get("name", "(unnamed feed)"),
        "feed_url": feed.get("url", ""),
        "source_kind": feed.get("source_kind", "rss"),
        "domain": feed.get("domain", ""),
        "enabled": bool(feed.get("enabled", False)),
        "entries_found": entries_found,
        "html_pages_collected": html_pages_collected,
        "pdf_links_found": pdf_links_found,
        "pdfs_downloaded": pdfs_downloaded,
        "pdfs_attempted": pdfs_attempted,
        "html_pages_scanned": html_pages_scanned,
        "keep": triage_counts["keep"],
        "review": triage_counts["review"],
        "skip": triage_counts["skip"],
        **{bucket: domain_counts[bucket] for bucket in DOMAIN_BUCKETS},
    }


def _write_csv(rows: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "feed_name",
        "feed_url",
        "source_kind",
        "domain",
        "enabled",
        "entries_found",
        "html_pages_collected",
        "pdf_links_found",
        "pdfs_downloaded",
        "pdfs_attempted",
        "html_pages_scanned",
        "keep",
        "review",
        "skip",
        *DOMAIN_BUCKETS,
        "keep_pct",
        "review_pct",
        "skip_pct",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            scanned = int(row["pdfs_attempted"])
            prepared = dict(row)
            prepared["keep_pct"] = _percent(int(row["keep"]), scanned)
            prepared["review_pct"] = _percent(int(row["review"]), scanned)
            prepared["skip_pct"] = _percent(int(row["skip"]), scanned)
            writer.writerow(prepared)

    return output_path


def _write_markdown(rows: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Construction Source Quality Report",
        "",
        "Entries found means RSS entries for feed sources or HTML pages collected for collectors.",
        "",
        "| Feed | Kind | Entries | HTML Collected | PDF Links | PDFs Downloaded | PDFs Attempted | HTML Scanned | Keep | Review | Skip |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        scanned = int(row["pdfs_attempted"])
        lines.append(
            f"| {row['feed_name']} | {row['source_kind']} | {row['entries_found']} | {row['html_pages_collected']} | "
            f"{row['pdf_links_found']} | {row['pdfs_downloaded']} | {row['pdfs_attempted']} | {row['html_pages_scanned']} | "
            f"{_percent(int(row['keep']), scanned)}% | "
            f"{_percent(int(row['review']), scanned)}% | {_percent(int(row['skip']), scanned)}% |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    parser = argparse.ArgumentParser(description="Build a feed-level construction source quality report")
    parser.add_argument("--feeds-config", type=Path, default=DEFAULT_FEEDS_CONFIG, help="Path to feeds.json")
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV, help="CSV output path")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD, help="Markdown output path")
    parser.add_argument("--limit", type=int, default=None, help="Optional per-feed document scan limit")
    args = parser.parse_args()

    config = load_feeds_config(args.feeds_config)
    feeds = [feed for feed in config.get("feeds", []) if feed.get("enabled") and feed.get("domain") == "construction_science"]

    rows = [_summarize_feed(feed, limit=args.limit) for feed in feeds]
    rows.sort(key=lambda row: (row["construction_science"], row["keep"], row["feed_name"]))

    csv_path = _write_csv(rows, args.output_csv)
    md_path = _write_markdown(rows, args.output_md)

    print(f"Wrote feed quality CSV: {csv_path}")
    print(f"Wrote feed quality report: {md_path}")


if __name__ == "__main__":
    main()
