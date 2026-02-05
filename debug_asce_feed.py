#!/usr/bin/env python3
"""
Debug ASCE RSS feed to understand its structure
"""

import feedparser

def debug_asce_feed():
    """Debug ASCE RSS feed content"""
    print("🔍 DEBUGGING ASCE RSS FEED")
    print("=" * 60)
    
    feed_url = "https://ascelibrary.org/action/showFeed?type=etoc&feed=rss&jc=jmcee7"
    feed = feedparser.parse(feed_url)
    
    print(f"Feed title: {feed.feed.get('title', 'N/A')}")
    print(f"Feed entries: {len(feed.entries)}")
    
    if feed.entries:
        entry = feed.entries[0]
        print(f"\n📝 First entry:")
        print(f"  Title: {entry.get('title', 'N/A')}")
        print(f"  Published: {entry.get('published', 'N/A')}")
        
        print(f"\n🔗 Links:")
        for i, link in enumerate(entry.get('links', [])):
            print(f"  {i}: {link.get('href', 'N/A')} (type: {link.get('type', 'N/A')})")
        
        print(f"\n📋 Summary (first 300 chars):")
        summary = entry.get('summary', '')
        print(f"  {summary[:300]}...")
        
        print(f"\n📄 Content:")
        for i, content in enumerate(entry.get('content', [])):
            content_value = content.get('value', '')
            print(f"  {i}: {content_value[:300]}...")
    
    return feed

if __name__ == "__main__":
    debug_asce_feed()