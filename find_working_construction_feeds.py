#!/usr/bin/env python3
"""
Find working RSS feeds for construction materials
"""

import feedparser
import requests
import json

def test_rss_feed(url, name):
    """Test if an RSS feed is working and has content"""
    print(f"Testing: {name}")
    print(f"URL: {url}")
    
    # Use proper feedparser error handling
    feed = feedparser.parse(url)
    
    # Check for feedparser errors
    if feed.bozo:
        print(f"❌ Feed parsing error: {feed.bozo_exception}")
        return False
    
    # Check for HTTP errors
    if hasattr(feed, 'status') and feed.status != 200:
        print(f"❌ HTTP error: {feed.status}")
        return False
    
    if feed.entries:
        print(f"✅ Feed working: {len(feed.entries)} entries")
        if feed.entries[0].get('links'):
            print(f"   Links found: {len(feed.entries[0].links)}")
        return True
    else:
        print("❌ No entries found")
        return False

def main():
    """Find working construction materials RSS feeds"""
    print("🏗️  FINDING WORKING CONSTRUCTION MATERIALS RSS FEEDS")
    print("=" * 60)
    
    # Test various RSS feeds
    test_feeds = [
        # arXiv feeds
        ("http://export.arxiv.org/rss/cs.MA", "arXiv Materials Science"),
        ("http://export.arxiv.org/rss/cs.CE", "arXiv Civil Engineering"),
        ("http://export.arxiv.org/rss/q-bio.BM", "arXiv Biomaterials"),
        
        # Other potential sources
        ("https://feeds.feedburner.com/oreilly/radar/atom", "O'Reilly Radar"),
        ("https://www.frontiersin.org/journals/materials/rss", "Frontiers in Materials"),
        ("https://www.sciencedirect.com/rss/article?issn=0013-7944", "Engineering Fracture Mechanics"),
        ("https://www.sciencedirect.com/rss/article?issn=0141-0296", "Engineering Structures"),
    ]
    
    working_feeds = []
    
    for url, name in test_feeds:
        if test_rss_feed(url, name):
            working_feeds.append({
                "name": name,
                "url": url,
                "domain": "construction_science",
                "enabled": True
            })
        print()
    
    print("🏗️  WORKING RSS FEEDS FOUND:")
    print("=" * 40)
    for feed in working_feeds:
        print(f"✅ {feed['name']}")
    
    # Save working feeds
    if working_feeds:
        config = {"feeds": working_feeds}
        # Ensure config directory exists
        import os
        os.makedirs("config", exist_ok=True)
        with open("config/feeds.json", "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n✅ Updated config with {len(working_feeds)} working feeds")
    
    return working_feeds

if __name__ == "__main__":
    main()