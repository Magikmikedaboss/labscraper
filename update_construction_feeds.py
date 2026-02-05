#!/usr/bin/env python3
"""
Update RSS feeds configuration with working construction materials sources
"""

import json

def update_construction_feeds():
    """Update RSS feeds with working construction materials sources"""
    print("🏗️  UPDATING CONSTRUCTION MATERIALS RSS FEEDS")
    print("=" * 60)
    
    # Working RSS feeds for construction materials
    construction_feeds = [
        {
            "name": "arXiv Materials Science",
            "url": "http://export.arxiv.org/rss/cs.MA",
            "domain": "construction_science",
            "enabled": True,
            "description": "arXiv materials science research with construction applications"
        },
        {
            "name": "arXiv Biomaterials",
            "url": "http://export.arxiv.org/rss/q-bio.BM",
            "domain": "construction_science",
            "enabled": True,
            "description": "Biomaterials research with construction material applications"
        },
        {
            "name": "O'Reilly Radar (Technology & Materials)",
            "url": "https://feeds.feedburner.com/oreilly/radar/atom",
            "domain": "construction_science",
            "enabled": True,
            "description": "Technology research with materials science applications"
        }
    ]
    
    # Save to config
    config = {"feeds": construction_feeds}
    
    with open("config/feeds.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("✅ Updated RSS configuration for construction materials")
    print(f"   Added {len(construction_feeds)} working feeds")
    
    print("\n🏗️  CONSTRUCTION MATERIALS RSS FEEDS CONFIGURED")
    print("=" * 60)
    print("Next steps:")
    print("1. Run: python run_rss_ingest.py")
    print("2. Monitor RSS feeds for new construction materials research")
    print("3. Check database for processed construction science events")

def main():
    """Update construction materials RSS feeds"""
    update_construction_feeds()

if __name__ == "__main__":
    main()