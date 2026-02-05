#!/usr/bin/env python3
"""
Set up construction materials monitoring system
"""

import json
import requests
import re

def setup_construction_materials_monitoring():
    """Set up RSS feeds for construction materials monitoring"""
    print("🏗️  SETTING UP CONSTRUCTION MATERIALS MONITORING")
    print("=" * 60)
    
    # Working RSS feeds for construction materials
    construction_feeds = [
        {
            "name": "O'Reilly Radar (Technology & Materials)",
            "url": "https://feeds.feedburner.com/oreilly/radar/atom",
            "domain": "construction_science",
            "enabled": True,
            "description": "Technology research with materials science applications"
        },
        {
            "name": "Frontiers in Materials",
            "url": "https://www.frontiersin.org/journals/materials/rss",
            "domain": "construction_science", 
            "enabled": True,
            "description": "Open-access materials research journal"
        }
    ]
    
    # Save to config
    config = {"feeds": construction_feeds}
    
    with open("config/feeds.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("✅ Updated RSS configuration for construction materials")
    print(f"   Added {len(construction_feeds)} feeds")
    
    # Test the feeds
    print("\n📡 Testing construction materials feeds...")
    for feed in construction_feeds:
        print(f"\nTesting: {feed['name']}")
        try:
            response = requests.get(feed['url'], timeout=10)
            if response.status_code == 200:
                # Look for PDF links in the content
                pdf_links = re.findall(r'https?://[^\s<>"\']*.pdf', response.text, re.IGNORECASE)
                print(f"  ✅ Feed accessible ({len(pdf_links)} PDFs found)")
            else:
                print(f"  ❌ HTTP {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n🏗️  CONSTRUCTION MATERIALS MONITORING SETUP COMPLETE")
    print("=" * 60)
    print("Next steps:")
    print("1. Run: python run_rss_ingest.py")
    print("2. Monitor RSS feeds for new construction materials research")
    print("3. Manually upload high-quality ASCE papers to input_pdfs/")
    print("4. Process through your analysis pipeline")

def main():
    """Set up construction materials monitoring"""
    setup_construction_materials_monitoring()

if __name__ == "__main__":
    main()