#!/usr/bin/env python3
"""Generate a per-feed audit report for enabled feeds."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_rss_ingest import RSS_CACHE_DIR, download_pdf, get_pdf_links_from_entry, is_valid_pdf, load_feeds_config, load_trusted_construction_sources
from run_rss_ingest import _promotion_decision_from_lens_counts, _score_construction_review_lenses
from utils.domain_router import route_construction_source
from utils.feed_utils import parse_feed
from utils.site_collectors import collect_documents, extract_pdf_links_from_page
from utils.source_triage import scan_pdf


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEEDS_CONFIG = PROJECT_ROOT / "config" / "feeds.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "exports" / "feed_audit"
TRUSTED_CONSTRUCTION_SOURCES_CONFIG = PROJECT_ROOT / "config" / "construction_trusted_sources.json"
logger = logging.getLogger(__name__)


def _append_unique(values: list[str], candidate: str | None, *, limit: int | None = None) -> None:
    if not candidate or not isinstance(candidate, str):
        return
    normalized = candidate.strip()
    if not normalized or normalized in values:
        return
    if limit is not None and len(values) >= limit:
        return
    values.append(normalized)


def _entry_urls(entry: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    _append_unique(urls, entry.get("link"))
    _append_unique(urls, entry.get("id"))
    _append_unique(urls, entry.get("guid"))
    for link in entry.get("links", []):
        if not isinstance(link, dict):
            continue
        href = link.get("href")
        if not href:
            continue
        if "pdf" in str(href).lower():
            continue
        _append_unique(urls, href)
    return urls


def _record_pdf_outcome(
    *,
    feed: dict[str, Any],
    pdf_url: str,
    source_title: str,
    skip_reasons: Counter[str],
    triage_counts: Counter[str],
    trusted_construction_source: bool,
) -> dict[str, Any] | None:
    domain = str(feed.get("domain", "")).strip() or "methods_tooling"
    if domain == "construction_science":
        route = route_construction_source(title=source_title, text=pdf_url, url=pdf_url)
        if route.decision == "skip":
            skip_reasons["route_skip"] += 1
            return None

    pdf_path = download_pdf(pdf_url, RSS_CACHE_DIR)
    if not pdf_path:
        skip_reasons["download_failed"] += 1
        return None

    if not is_valid_pdf(pdf_path):
        skip_reasons["invalid_pdf"] += 1
        return None

    triage = scan_pdf(pdf_path)
    triage_decision = getattr(triage, "triage_decision", "") or triage.keep_skip_review
    final_decision = getattr(triage, "final_decision", "") or triage.keep_skip_review
    lens_promoted = bool(getattr(triage, "lens_promoted", False))
    promotion_reason = str(getattr(triage, "promotion_reason", "") or "")

    if domain == "construction_science" and triage_decision == "review" and trusted_construction_source:
        lens_counts = _score_construction_review_lenses(pdf_path)
        lens_promoted, promotion_reason = _promotion_decision_from_lens_counts(lens_counts)
        final_decision = "keep" if lens_promoted else "review"
    elif domain == "construction_science" and triage_decision == "review" and not trusted_construction_source:
        promotion_reason = "review promotion disabled for untrusted source"

    triage_counts[triage.keep_skip_review] += 1
    if triage.keep_skip_review == "review":
        skip_reasons["triage_review"] += 1
    elif triage.keep_skip_review == "skip":
        skip_reasons["triage_skip"] += 1

    return {
        "downloaded": True,
        "accepted": final_decision == "keep",
        "triage_decision": triage_decision,
        "lens_promoted": lens_promoted,
        "promotion_reason": promotion_reason,
        "final_decision": final_decision,
    }


def _summarize_pdf_list_feed(feed: dict[str, Any], *, max_pdf_attempts: int | None = None) -> dict[str, Any]:
    pdf_urls = [str(url).strip() for url in feed.get("pdf_urls", []) if str(url).strip()]
    discovered_urls = pdf_urls[:10]
    pdf_urls = list(dict.fromkeys(pdf_urls))
    pdf_links_found = len(pdf_urls)

    skip_reasons: Counter[str] = Counter()
    triage_counts: Counter[str] = Counter()
    triage_decision_counts: Counter[str] = Counter()
    final_decision_counts: Counter[str] = Counter()
    promotion_reason_counts: Counter[str] = Counter()
    pdfs_downloaded = 0
    pdfs_accepted = 0
    lens_promoted = 0
    processed_urls: set[str] = set()
    trusted_source = bool(feed.get("trusted_source", False))

    for pdf_url in pdf_urls:
        if pdf_url in processed_urls:
            skip_reasons["duplicate_pdf_url"] += 1
            continue
        processed_urls.add(pdf_url)
        if max_pdf_attempts is not None and len(processed_urls) > max_pdf_attempts:
            skip_reasons["audit_limit"] += 1
            continue
        outcome = _record_pdf_outcome(
            feed=feed,
            pdf_url=pdf_url,
            source_title=str(feed.get("name", "")),
            skip_reasons=skip_reasons,
            triage_counts=triage_counts,
            trusted_construction_source=trusted_source,
        )
        if not outcome:
            continue
        pdfs_downloaded += int(outcome["downloaded"])
        pdfs_accepted += int(outcome["accepted"])
        triage_decision_counts[str(outcome["triage_decision"])] += 1
        final_decision_counts[str(outcome["final_decision"])] += 1
        if outcome["lens_promoted"]:
            lens_promoted += 1
            if outcome["promotion_reason"]:
                promotion_reason_counts[str(outcome["promotion_reason"])] += 1

    pdfs_skipped = sum(skip_reasons.values())
    return {
        "feed_name": feed.get("name", "(unnamed feed)"),
        "feed_url": feed.get("url", ""),
        "source_kind": "pdf_list",
        "domain": feed.get("domain", ""),
        "enabled": bool(feed.get("enabled", False)),
        "entries_found": len(pdf_urls),
        "html_pages_collected": 0,
        "pdf_links_found": pdf_links_found,
        "pdfs_downloaded": pdfs_downloaded,
        "pdfs_accepted": pdfs_accepted,
        "pdfs_skipped": pdfs_skipped,
        "skip_reasons": dict(skip_reasons),
        "errors": [],
        "first_10_discovered_urls": discovered_urls,
        "first_10_pdf_urls": discovered_urls,
        "trusted_source": trusted_source,
        "triage_decision": dict(triage_decision_counts),
        "lens_promoted": lens_promoted,
        "promotion_reason": dict(promotion_reason_counts),
        "final_decision": dict(final_decision_counts),
        "keep": triage_counts["keep"],
        "review": triage_counts["review"],
        "skip": triage_counts["skip"],
    }


def _summarize_collector_feed(feed: dict[str, Any], *, max_pdf_attempts: int | None = None) -> dict[str, Any]:
    skip_reasons: Counter[str] = Counter()
    triage_counts: Counter[str] = Counter()
    triage_decision_counts: Counter[str] = Counter()
    final_decision_counts: Counter[str] = Counter()
    promotion_reason_counts: Counter[str] = Counter()
    errors: list[str] = []
    first_discovered_urls: list[str] = []
    first_pdf_urls: list[str] = []
    seen_pdf_urls: set[str] = set()
    pdfs_downloaded = 0
    pdfs_accepted = 0
    lens_promoted = 0
    trusted_source = bool(feed.get("trusted_source", False))

    try:
        collected_documents = collect_documents(
            feed["url"],
            max_pages=int(feed.get("max_pages", 20)),
            same_domain_only=bool(feed.get("same_domain_only", True)),
            same_path_prefix=feed.get("same_path_prefix"),
            max_depth=int(feed.get("collector_max_depth", 1)),
            request_timeout=int(feed.get("request_timeout", 20)),
            max_seconds=int(feed.get("collector_timeout_seconds", 60)),
        )
    except Exception as exc:
        logger.exception("Collector audit failed for %s", feed.get("name", feed.get("url", "<unknown>")))
        return {
            "feed_name": feed.get("name", "(unnamed feed)"),
            "feed_url": feed.get("url", ""),
            "source_kind": "collector",
            "domain": feed.get("domain", ""),
            "enabled": bool(feed.get("enabled", False)),
            "entries_found": 0,
            "html_pages_collected": 0,
            "pdf_links_found": 0,
            "pdfs_downloaded": 0,
            "pdfs_accepted": 0,
            "pdfs_skipped": 0,
            "skip_reasons": {},
            "errors": [f"{type(exc).__name__}: {exc}"],
            "first_10_discovered_urls": [],
            "first_10_pdf_urls": [],
            "trusted_source": False,
            "triage_decision": {},
            "lens_promoted": 0,
            "promotion_reason": {},
            "final_decision": {},
            "keep": 0,
            "review": 0,
            "skip": 0,
        }

    html_pages_collected = len(collected_documents)
    entries_found = html_pages_collected

    for document in collected_documents:
        _append_unique(first_discovered_urls, document.url, limit=10)
        try:
            pdf_urls = extract_pdf_links_from_page(document.url, timeout=int(feed.get("request_timeout", 20)))
        except Exception as exc:
            errors.append(f"{document.url}: {type(exc).__name__}: {exc}")
            continue

        for pdf_url in pdf_urls:
            if pdf_url in seen_pdf_urls:
                skip_reasons["duplicate_pdf_url"] += 1
                continue
            seen_pdf_urls.add(pdf_url)
            _append_unique(first_pdf_urls, pdf_url, limit=10)

            if max_pdf_attempts is not None and len(seen_pdf_urls) > max_pdf_attempts:
                skip_reasons["audit_limit"] += 1
                continue

            outcome = _record_pdf_outcome(
                feed=feed,
                pdf_url=pdf_url,
                source_title=document.title,
                skip_reasons=skip_reasons,
                triage_counts=triage_counts,
                trusted_construction_source=trusted_source,
            )
            if not outcome:
                continue
            pdfs_downloaded += int(outcome["downloaded"])
            pdfs_accepted += int(outcome["accepted"])
            triage_decision_counts[str(outcome["triage_decision"])] += 1
            final_decision_counts[str(outcome["final_decision"])] += 1
            if outcome["lens_promoted"]:
                lens_promoted += 1
                if outcome["promotion_reason"]:
                    promotion_reason_counts[str(outcome["promotion_reason"])] += 1

    pdfs_skipped = sum(skip_reasons.values())
    return {
        "feed_name": feed.get("name", "(unnamed feed)"),
        "feed_url": feed.get("url", ""),
        "source_kind": "collector",
        "domain": feed.get("domain", ""),
        "enabled": bool(feed.get("enabled", False)),
        "entries_found": entries_found,
        "html_pages_collected": html_pages_collected,
        "pdf_links_found": len(seen_pdf_urls),
        "pdfs_downloaded": pdfs_downloaded,
        "pdfs_accepted": pdfs_accepted,
        "pdfs_skipped": pdfs_skipped,
        "skip_reasons": dict(skip_reasons),
        "errors": errors,
        "first_10_discovered_urls": first_discovered_urls,
        "first_10_pdf_urls": first_pdf_urls,
        "trusted_source": trusted_source,
        "triage_decision": dict(triage_decision_counts),
        "lens_promoted": lens_promoted,
        "promotion_reason": dict(promotion_reason_counts),
        "final_decision": dict(final_decision_counts),
        "keep": triage_counts["keep"],
        "review": triage_counts["review"],
        "skip": triage_counts["skip"],
    }


def _summarize_rss_feed(feed: dict[str, Any], *, max_pdf_attempts: int | None = None) -> dict[str, Any]:
    skip_reasons: Counter[str] = Counter()
    triage_counts: Counter[str] = Counter()
    triage_decision_counts: Counter[str] = Counter()
    final_decision_counts: Counter[str] = Counter()
    promotion_reason_counts: Counter[str] = Counter()
    errors: list[str] = []
    first_discovered_urls: list[str] = []
    first_pdf_urls: list[str] = []
    seen_pdf_urls: set[str] = set()
    pdfs_downloaded = 0
    pdfs_accepted = 0
    lens_promoted = 0
    trusted_source = bool(feed.get("trusted_source", False))

    try:
        parsed_feed = parse_feed(feed["url"], timeout=int(feed.get("request_timeout", 20)))
    except Exception as exc:
        logger.exception("RSS audit failed for %s", feed.get("name", feed.get("url", "<unknown>")))
        return {
            "feed_name": feed.get("name", "(unnamed feed)"),
            "feed_url": feed.get("url", ""),
            "source_kind": "rss",
            "domain": feed.get("domain", ""),
            "enabled": bool(feed.get("enabled", False)),
            "entries_found": 0,
            "html_pages_collected": 0,
            "pdf_links_found": 0,
            "pdfs_downloaded": 0,
            "pdfs_accepted": 0,
            "pdfs_skipped": 0,
            "skip_reasons": {},
            "errors": [f"{type(exc).__name__}: {exc}"],
            "first_10_discovered_urls": [],
            "first_10_pdf_urls": [],
            "trusted_source": False,
            "triage_decision": {},
            "lens_promoted": 0,
            "promotion_reason": {},
            "final_decision": {},
            "keep": 0,
            "review": 0,
            "skip": 0,
        }

    if isinstance(parsed_feed, dict):
        entries = list(parsed_feed.get("entries", []))
    else:
        entries = list(getattr(parsed_feed, "entries", []))

    for entry in entries:
        for url in _entry_urls(entry):
            _append_unique(first_discovered_urls, url, limit=10)

        try:
            pdf_urls = get_pdf_links_from_entry(entry, source_domain=str(feed.get("domain", "")))
        except Exception as exc:
            errors.append(f"{entry.get('title', 'Unknown')}: {type(exc).__name__}: {exc}")
            continue

        for pdf_url in pdf_urls:
            if pdf_url in seen_pdf_urls:
                skip_reasons["duplicate_pdf_url"] += 1
                continue
            seen_pdf_urls.add(pdf_url)
            _append_unique(first_pdf_urls, pdf_url, limit=10)

            if max_pdf_attempts is not None and len(seen_pdf_urls) > max_pdf_attempts:
                skip_reasons["audit_limit"] += 1
                continue

            outcome = _record_pdf_outcome(
                feed=feed,
                pdf_url=pdf_url,
                source_title=str(entry.get("title", feed.get("name", ""))),
                skip_reasons=skip_reasons,
                triage_counts=triage_counts,
                trusted_construction_source=trusted_source,
            )
            if not outcome:
                continue
            pdfs_downloaded += int(outcome["downloaded"])
            pdfs_accepted += int(outcome["accepted"])
            triage_decision_counts[str(outcome["triage_decision"])] += 1
            final_decision_counts[str(outcome["final_decision"])] += 1
            if outcome["lens_promoted"]:
                lens_promoted += 1
                if outcome["promotion_reason"]:
                    promotion_reason_counts[str(outcome["promotion_reason"])] += 1

    pdfs_skipped = sum(skip_reasons.values())
    return {
        "feed_name": feed.get("name", "(unnamed feed)"),
        "feed_url": feed.get("url", ""),
        "source_kind": "rss",
        "domain": feed.get("domain", ""),
        "enabled": bool(feed.get("enabled", False)),
        "entries_found": len(entries),
        "html_pages_collected": 0,
        "pdf_links_found": len(seen_pdf_urls),
        "pdfs_downloaded": pdfs_downloaded,
        "pdfs_accepted": pdfs_accepted,
        "pdfs_skipped": pdfs_skipped,
        "skip_reasons": dict(skip_reasons),
        "errors": errors,
        "first_10_discovered_urls": first_discovered_urls,
        "first_10_pdf_urls": first_pdf_urls,
        "trusted_source": trusted_source,
        "triage_decision": dict(triage_decision_counts),
        "lens_promoted": lens_promoted,
        "promotion_reason": dict(promotion_reason_counts),
        "final_decision": dict(final_decision_counts),
        "keep": triage_counts["keep"],
        "review": triage_counts["review"],
        "skip": triage_counts["skip"],
    }


def _summarize_feed(feed: dict[str, Any], *, max_pdf_attempts: int | None = None) -> dict[str, Any]:
    source_kind = str(feed.get("source_kind", "rss")).strip().lower()
    if source_kind == "pdf_list":
        return _summarize_pdf_list_feed(feed, max_pdf_attempts=max_pdf_attempts)
    if source_kind == "collector":
        return _summarize_collector_feed(feed, max_pdf_attempts=max_pdf_attempts)
    return _summarize_rss_feed(feed, max_pdf_attempts=max_pdf_attempts)


def _load_enabled_feeds(config_path: Path) -> list[dict[str, Any]]:
    config = load_feeds_config(config_path)
    feeds = config.get("feeds", [])
    if not isinstance(feeds, list):
        return []
    return [feed for feed in feeds if isinstance(feed, dict) and feed.get("enabled", True)]


def _is_trusted_construction_feed(feed: dict[str, Any], trusted_sources: set[str]) -> bool:
    feed_name = str(feed.get("name", "")).strip().casefold()
    return bool(feed_name) and feed_name in trusted_sources


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
        "pdfs_accepted",
        "pdfs_skipped",
        "skip_reasons",
        "errors",
        "first_10_discovered_urls",
        "first_10_pdf_urls",
        "trusted_source",
        "triage_decision",
        "lens_promoted",
        "promotion_reason",
        "final_decision",
        "keep",
        "review",
        "skip",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            prepared = dict(row)
            prepared["skip_reasons"] = json.dumps(row.get("skip_reasons", {}), ensure_ascii=False)
            prepared["errors"] = json.dumps(row.get("errors", []), ensure_ascii=False)
            prepared["first_10_discovered_urls"] = json.dumps(row.get("first_10_discovered_urls", []), ensure_ascii=False)
            prepared["first_10_pdf_urls"] = json.dumps(row.get("first_10_pdf_urls", []), ensure_ascii=False)
            prepared["triage_decision"] = json.dumps(row.get("triage_decision", {}), ensure_ascii=False)
            prepared["promotion_reason"] = json.dumps(row.get("promotion_reason", {}), ensure_ascii=False)
            prepared["final_decision"] = json.dumps(row.get("final_decision", {}), ensure_ascii=False)
            writer.writerow(prepared)
    return output_path


def _write_json(rows: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"feeds": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def _print_summary(rows: list[dict[str, Any]]) -> None:
    print("\nFeed audit summary")
    print("=" * 80)
    for row in rows:
        triage_decision = row.get("triage_decision", {})
        final_decision = row.get("final_decision", {})
        print(
            f"{row['feed_name']}: kind={row['source_kind']} entries={row['entries_found']} "
            f"html={row['html_pages_collected']} pdf_links={row['pdf_links_found']} "
            f"downloaded={row['pdfs_downloaded']} skipped={row['pdfs_skipped']} "
            f"trusted={bool(row.get('trusted_source', False))} "
            f"triage={{keep:{triage_decision.get('keep', 0)}, review:{triage_decision.get('review', 0)}, skip:{triage_decision.get('skip', 0)}}} "
            f"promoted={row.get('lens_promoted', 0)} "
            f"final={{keep:{final_decision.get('keep', 0)}, review:{final_decision.get('review', 0)}, skip:{final_decision.get('skip', 0)}}}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an audit report for enabled feeds.")
    parser.add_argument("--config", default=str(DEFAULT_FEEDS_CONFIG), help="Path to feeds.json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for audit outputs")
    parser.add_argument("--max-pdfs", type=int, default=None, help="Optional per-feed PDF attempt cap")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    output_dir = Path(args.output_dir)
    feeds = _load_enabled_feeds(config_path)
    trusted_sources = load_trusted_construction_sources(TRUSTED_CONSTRUCTION_SOURCES_CONFIG)

    rows = []
    for feed in feeds:
        feed["trusted_source"] = _is_trusted_construction_feed(feed, trusted_sources)
        print(f"Auditing {feed.get('name', feed.get('url', '<unnamed>'))}")
        rows.append(_summarize_feed(feed, max_pdf_attempts=args.max_pdfs))

    csv_path = _write_csv(rows, output_dir / "feed_audit.csv")
    json_path = _write_json(rows, output_dir / "feed_audit.json")

    _print_summary(rows)
    print(f"\nWrote {csv_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())