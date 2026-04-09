#!/usr/bin/env python3
"""
Unified feed testing utility
Replaces: test_arxiv_feeds.py, test_working_feeds.py, 
test_construction_materials_feeds.py, find_working_construction_feeds.py,
debug_arxiv_feeds.py, debug_asce_feed.py, debug_rss.py
"""

import argparse
import json
import sys
from pathlib import Path

# Add the parent directory to the path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.feed_utils import probe_feed
from utils.validators import ValidationError, validate_feed_config, validate_file_path

def main():
    parser = argparse.ArgumentParser(description='Test RSS feeds')
    parser.add_argument('--config', default='config/feeds.json', 
                       help='Feed configuration file')
    parser.add_argument('--keywords', nargs='+', 
                       help='Keywords to search for in entries')
    parser.add_argument('--save-working', action='store_true',
                       help='Save working feeds back to config')
    args = parser.parse_args()

    default_feeds = [
        ("https://feeds.feedburner.com/oreilly/radar/atom", "O'Reilly Radar"),
        ("https://www.frontiersin.org/journals/materials/rss", "Frontiers in Materials"),
        ("http://export.arxiv.org/rss/cond-mat.mtrl-sci", "arXiv Materials Science"),
    ]

    config = None
    feeds = default_feeds
    config_path = Path(args.config)

    # Load feeds from config
    if config_path.exists():
        try:
            validated_path = validate_file_path(config_path)
            with open(validated_path, encoding='utf-8') as f:
                config = validate_feed_config(json.load(f))
                feeds = [(feed['url'], feed['name']) for feed in config.get('feeds', [])]
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"⚠️  Validation error in {args.config}: {e}")
            print("   Falling back to default feeds...")
            config = None
            feeds = default_feeds
        except Exception as e:
            print(f"⚠️  Error reading {args.config}: {e}")
            print("   Falling back to default feeds...")
            config = None
            feeds = default_feeds
    
    print(f"\n🧪 Testing {len(feeds)} feeds...")
    print("=" * 60)
    
    results = []
    for url, name in feeds:
        result = probe_feed(url, name, check_keywords=args.keywords)
        result['url'] = url
        result['name'] = name
        results.append(result)
    
    # Summary
    working = [r for r in results if r.get('success')]
    print(f"\n{'='*60}")
    print(f"✅ Working: {len(working)}/{len(results)}")
    print(f"📄 Feeds with PDFs: {len([r for r in working if r.get('pdfs')])}")
    
    # Save working feeds if requested
    if args.save_working and working:
        output = {
            'feeds': [
                {
                    'name': r['name'],
                    'url': r['url'],
                    'domain': 'construction_science',
                    'enabled': True
                }
                for r in working
            ]
        }
        Path('config').mkdir(exist_ok=True)
        output = validate_feed_config(output)
        with open('config/feeds.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        print(f"\n💾 Saved {len(working)} working feeds to config/feeds.json")

if __name__ == "__main__":
    main()