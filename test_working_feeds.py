#!/usr/bin/env python3
"""
Test various open-access RSS feeds that provide PDF downloads
"""

import feedparser

def test_feed(url, name):
    """Test an RSS feed"""
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
            import re
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
                    print("  No PDF links found")
        print()
    except Exception as e:
        print(f"  Error: {e}")
        print()

def main():
    """Test various RSS feeds"""
    feeds = [
        # Known working feeds with PDFs
        ("https://feeds.feedburner.com/oreilly/radar/atom", "O'Reilly Radar (Test)"),
        ("https://www.nature.com/ncomms/articles.rss", "Nature Communications"),
        ("https://www.sciencedirect.com/rss/article/science?pii=S0010465523002000", "Computer Physics Communications"),
        ("https://www.mdpi.com/journal/materials/feed", "Materials Journal"),
        ("https://www.frontiersin.org/journals/materials/rss", "Frontiers in Materials"),
    ]
    
    for url, name in feeds:
        test_feed(url, name)

if __name__ == "__main__":
    main()