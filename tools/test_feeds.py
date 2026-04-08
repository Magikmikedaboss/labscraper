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
from utils.feed_utils import test_feed

def main():
    parser = argparse.ArgumentParser(description='Test RSS feeds')
    parser.add_argument('--config', default='config/feeds.json', 
                       help='Feed configuration file')
    parser.add_argument('--keywords', nargs='+', 
                       help='Keywords to search for in entries')
    parser.add_argument('--save-working', action='store_true',
                       help='Save working feeds back to config')
    args = parser.parse_args()
    
    # Load feeds from config
    if Path(args.config).exists():
        try:
            with open(args.config) as f:
                config = json.load(f)
                feeds = [(f['url'], f['name']) for f in config.get('feeds', [])]
        except json.JSONDecodeError as e:
            print(f"⚠️  Error parsing {args.config}: {e}")
            print("   Falling back to default feeds...")
            config = None
            feeds = [
                ("https://feeds.feedburner.com/oreilly/radar/atom", "O'Reilly Radar"),
                ("https://www.frontiersin.org/journals/materials/rss", "Frontiers in Materials"),
                ("http://export.arxiv.org/rss/cond-mat.mtrl-sci", "arXiv Materials Science"),
            ]
        except Exception as e:
            print(f"⚠️  Error reading {args.config}: {e}")
            print("   Falling back to default feeds...")
            config = None
            feeds = [
                ("https://feeds.feedburner.com/oreilly/radar/atom", "O'Reilly Radar"),
                ("https://www.frontiersin.org/journals/materials/rss", "Frontiers in Materials"),
                ("http://export.arxiv.org/rss/cond-mat.mtrl-sci", "arXiv Materials Science"),
            ]
    else:
        # Default test feeds
        config = None
        feeds = [
            ("https://feeds.feedburner.com/oreilly/radar/atom", "O'Reilly Radar"),
            ("https://www.frontiersin.org/journals/materials/rss", "Frontiers in Materials"),
            ("http://export.arxiv.org/rss/cond-mat.mtrl-sci", "arXiv Materials Science"),
        ]
    
    print(f"\n🧪 Testing {len(feeds)} feeds...")
    print("=" * 60)
    
    results = []
    for url, name in feeds:
        result = test_feed(url, name, check_keywords=args.keywords)
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
        with open('config/feeds.json', 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\n💾 Saved {len(working)} working feeds to config/feeds.json")

if __name__ == "__main__":
    main()