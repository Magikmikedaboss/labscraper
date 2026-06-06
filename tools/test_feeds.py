#!/usr/bin/env python3
"""
Unified feed testing utility
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.feed_utils import probe_feed
from utils.validators import ValidationError, validate_feed_config, validate_file_path

# Export default_feeds for import in tests
default_feeds = [
    ("https://www.sciencedaily.com/rss/health_medicine.xml", "ScienceDaily Health & Medicine"),
    ("https://www.nature.com/subjects/medicine/rss.xml", "Nature Medicine"),
]

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
    if argv is None:
        argv = sys.argv[1:]
    args, _ = parser.parse_known_args(argv)
    config_path = Path(args.config)
    # Default feeds fallback
    feeds = default_feeds
    config = None

    print("\n📡 Testing feeds...")
    print("=" * 60)

    # ---------------------------------------------------------
    # LOAD CONFIG
    # ---------------------------------------------------------
    if config_path.exists():
        try:
            validated_path = validate_file_path(config_path)

            with open(validated_path, encoding="utf-8") as f:
                config = validate_feed_config(json.load(f))

            feeds = [(feed["url"], feed["name"]) for feed in config.get("feeds", [])]

        except (json.JSONDecodeError, ValidationError) as e:
            print(f"⚠️ Validation error in {args.config}: {e}")
            print("   Falling back to default feeds...")
            feeds = default_feeds

        except Exception as e:
            print(f"⚠️ Error reading {args.config}: {e}")
            print("   Falling back to default feeds...")
            feeds = default_feeds

    print(f"\n🔍 Testing {len(feeds)} feeds...")
    print("=" * 60)

    # ---------------------------------------------------------
    # TEST FEEDS
    # ---------------------------------------------------------
    results = []

    for url, name in feeds:
        result = probe_feed(url, name, check_keywords=args.keywords)
        result["url"] = url
        result["name"] = name
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
        output = {
            "feeds": [
                {
                    "name": r["name"],
                    "url": r["url"],
                    "domain": "construction_science",
                    "enabled": True,
                }
                for r in working
            ]
        }
        save_path = config_path.with_name(config_path.stem + "_working.json")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            output = validate_feed_config(output)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)
            print(f"\n💾 Saved {len(working)} working feeds to {save_path}")
        except ValidationError as e:
            print(f"⚠️ Failed to validate output config: {e}")
            sys.exit(1)


# ---------------------------------------------------------
# ENTRY
# ---------------------------------------------------------
if __name__ == "__main__":
    main()