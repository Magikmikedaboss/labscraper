#!/usr/bin/env python3
"""
Test RSS feeds specifically for construction materials research
"""

import feedparser
import re

def test_construction_feed(url, name):
    """Test a construction materials RSS feed"""
    print(f"Testing {name}: {url}")
    try:
        feed = feedparser.parse(url)
        print(f"  Entries: {len(feed.entries)}")
        print(f"  Title: {feed.feed.get('title', 'N/A')}")
        
        if feed.entries:
            entry = feed.entries[0]
            print(f"  First entry: {entry.get('title', 'N/A')}")
            
            # Look for PDF links
            pdf_links = []
            summary = entry.get('summary', '')
            pdf_matches = re.findall(r'https?://[^\s<>"\']*.pdf', summary, re.IGNORECASE)
            pdf_links.extend(pdf_matches)
            
            for content in entry.get('content', []):
                content_value = content.get('value', '')
                pdf_matches = re.findall(r'https?://[^\s<>"\']*.pdf', content_value, re.IGNORECASE)
                pdf_links.extend(pdf_matches)
            
                if pdf_links:
                    print(f"  ✅ Found {len(pdf_links)} PDF links")
                    for pdf_link in pdf_links[:3]:  # Show first 3
                        print(f"    - {pdf_link}")
                else:
                    print("  ⚠️  No PDF links found")
                
            # Look for construction materials keywords
            keywords = ['concrete', 'steel', 'materials', 'construction', 'cement', 'composite', 'polymer', 'asphalt']
            summary_lower = summary.lower()
            found_keywords = [kw for kw in keywords if kw in summary_lower]
            if found_keywords:
                print(f"  🏗️  Construction keywords: {', '.join(found_keywords)}")
        print()
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print()

def main():
    """Test construction materials RSS feeds"""
    print("🏗️  TESTING CONSTRUCTION MATERIALS RSS FEEDS")
    print("=" * 60)
    
    feeds = [
        # Open access materials journals
        ("https://www.mdpi.com/journal/materials/feed", "Materials Journal (MDPI)"),
        ("https://www.frontiersin.org/journals/materials/rss", "Frontiers in Materials"),
        ("https://www.sciencedirect.com/journal/construction-and-building-materials/rss", "Construction and Building Materials"),
        
        # Industry and research sources
        ("https://www.concrete.org/rss/", "American Concrete Institute"),
        ("https://www.astm.org/rss/", "ASTM International"),
        ("https://www.nist.gov/rss/", "NIST Materials Research"),
        
        # University repositories
        ("https://dspace.mit.edu/rss", "MIT DSpace - Materials"),
        ("https://repository.lboro.ac.uk/rss", "Loughborough University - Materials"),
        
        # Working test feed
        ("https://feeds.feedburner.com/oreilly/radar/atom", "O'Reilly Radar (Test)"),
    ]
    
    for url, name in feeds:
        test_construction_feed(url, name)

if __name__ == "__main__":
    main()