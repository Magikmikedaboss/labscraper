#!/usr/bin/env python3
"""
Unified feed testing utility
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.feed_utils import probe_feed
from utils.validators import ValidationError, validate_domain_name, validate_feed_entry, validate_file_path

# Export default_feeds for import in tests
default_feeds = [
    ("https://www.sciencedaily.com/rss/health_medicine.xml", "ScienceDaily Health & Medicine"),
    ("https://www.nature.com/subjects/medicine/rss.xml", "Nature Medicine"),
]


def _default_feed_entries() -> list[dict[str, Any]]:
    return [{"url": url, "name": name, "enabled": True, "source_kind": "rss"} for url, name in default_feeds]


def _load_feed_entries(config_path: Path) -> list[dict[str, Any]]:
    validated_path = validate_file_path(config_path)

    with open(validated_path, encoding="utf-8") as handle:
        config = json.load(handle)

    if not isinstance(config, dict):
        raise ValidationError("Feed config must be a JSON object")

    feeds = config.get("feeds", [])
    if feeds is None:
        feeds = []
    if not isinstance(feeds, list):
        raise ValidationError("Feed config field 'feeds' must be a list")

    normalized_feeds: list[dict[str, Any]] = []
    for index, feed in enumerate(feeds, start=1):
        if not isinstance(feed, dict):
            raise ValidationError(f"Feed #{index}: Feed entry must be an object")

        source_kind = str(feed.get("source_kind", "rss")).strip().lower()
        if source_kind == "pdf_list":
            name = str(feed.get("name", "")).strip()
            if not name:
                raise ValidationError(f"Feed #{index}: Missing required field(s): name")

            pdf_urls = feed.get("pdf_urls", [])
            if pdf_urls is None:
                pdf_urls = []
            if not isinstance(pdf_urls, list):
                raise ValidationError(f"Feed #{index}: Field 'pdf_urls' must be a list")

            validated_feed = feed.copy()
            validated_feed["name"] = name
            validated_feed["enabled"] = bool(feed.get("enabled", True))
            validated_feed["source_kind"] = "pdf_list"
            validated_feed["pdf_urls"] = [url.strip() for url in pdf_urls if isinstance(url, str) and url.strip()]
            if feed.get("domain"):
                validated_feed["domain"] = validate_domain_name(str(feed["domain"]).strip())
            normalized_feeds.append(validated_feed)
            continue

        validated_feed = validate_feed_entry(feed, index=index)
        normalized_feeds.append(validated_feed)

    return normalized_feeds

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="config/feeds.json",
        help="Feed configuration file",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        help="Keywords to search for in entries",
    )
    parser.add_argument(
        "--save-working",
        action="store_true",
        help="Save working feeds to <config_stem>_working.json",
    )
    parser.add_argument(
        "--default-domain",
        default=None,
        help="Fallback domain to use when a feed does not specify one",
    )
    if argv is None:
        argv = sys.argv[1:]
    args, _ = parser.parse_known_args(argv)
    if args.default_domain is not None:
        try:
            args.default_domain = validate_domain_name(args.default_domain)
        except ValidationError as e:
            print(f"⚠️ Invalid --default-domain: {e}")
            return 1
    config_path = Path(args.config)
    feeds = _default_feed_entries()

    print("\n📡 Testing feeds...")
    print("=" * 60)

    # ---------------------------------------------------------
    # LOAD CONFIG
    # ---------------------------------------------------------
    try:
        feeds = _load_feed_entries(config_path)

    except (json.JSONDecodeError, ValidationError) as e:
        print(f"⚠️ Validation error in {args.config}: {e}")
        print("   Falling back to default feeds...")
        feeds = _default_feed_entries()

    except Exception as e:
        print(f"⚠️ Error reading {args.config}: {e}")
        print("   Falling back to default feeds...")
        feeds = _default_feed_entries()

    feeds_to_test = [feed for feed in feeds if feed.get("enabled", True)]

    print(f"\n🔍 Testing {len(feeds_to_test)} feeds...")
    print("=" * 60)

    # ---------------------------------------------------------
    # TEST FEEDS
    # ---------------------------------------------------------
    results = []

    for feed in feeds_to_test:
        url = feed.get("url")
        name = feed.get("name", "<unnamed>")
        source_kind = str(feed.get("source_kind", "rss")).strip().lower()
        result: dict[str, Any]

        try:
            if source_kind == "pdf_list":
                pdf_urls = feed.get("pdf_urls", [])
                pdf_urls = [pdf_url.strip() for pdf_url in pdf_urls if isinstance(pdf_url, str) and pdf_url.strip()]
                print(f"Testing {name}: PDF list source")
                print(f"  PDF URLs: {len(pdf_urls)}")
                if pdf_urls:
                    print(f"  First PDF: {pdf_urls[0]}")
                    result = {
                        "success": True,
                        "entries": len(pdf_urls),
                        "pdfs": len(pdf_urls),
                        "title": name,
                    }
                else:
                    print("  ⚠️  No PDF URLs configured")
                    result = {"success": False, "error": "No PDF URLs configured"}
            elif source_kind == "collector":
                collector_mode = feed.get("collector_mode", "html_archive")
                print(f"Testing {name}: collector source ({collector_mode})")
                if url:
                    print(f"  URL: {url}")
                max_pages = feed.get("max_pages")
                if max_pages:
                    print(f"  Max pages: {max_pages}")
                result = {
                    "success": bool(url),
                    "entries": 0,
                    "pdfs": 0,
                    "title": name,
                }
                if not url:
                    result["error"] = "Missing url for collector source"
            else:
                result = probe_feed(url, name, check_keywords=args.keywords)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            print(f"⚠️ Probe failed for '{name}' ({url}): {error_msg}")
            result = {"success": False, "error": error_msg}
        result["url"] = url
        result["name"] = name
        result["source_kind"] = source_kind
        result["feed"] = feed
        results.append(result)

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    working = [r for r in results if r.get("success")]

    print(f"\n{'=' * 60}")
    print(f"✅ Working: {len(working)}/{len(results)}")
    print(f"📄 Feeds with PDFs: {len([r for r in working if r.get('pdfs')])}")

    # ---------------------------------------------------------
    # SAVE WORKING FEEDS
    # ---------------------------------------------------------
    if args.save_working and working:
        sanitized_feeds = []
        for r in working:
            original_feed = dict(r.get("feed", {}))
            domain = original_feed.get("domain") or args.default_domain
            if not domain:
                print(f"⚠️ Skipping feed without a domain: {r.get('name')} ({r.get('url')})")
                continue
            feed_entry = original_feed.copy()
            feed_entry["domain"] = domain
            feed_entry["enabled"] = True
            sanitized_feeds.append(feed_entry)
        output = {"feeds": sanitized_feeds}
        save_path = config_path.with_name(config_path.stem + "_working.json")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)
            print(f"\n💾 Saved {len(sanitized_feeds)} working feeds to {save_path}")
        except ValidationError as e:
            print(f"⚠️ Failed to validate output config: {e}")
            sys.exit(1)


# ---------------------------------------------------------
# ENTRY
# ---------------------------------------------------------
if __name__ == "__main__":
    main()