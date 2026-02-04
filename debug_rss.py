#!/usr/bin/env python3
"""
Debug RSS feed content to understand arXiv feed structure
"""

import feedparser
import json

def debug_rss_feed(feed_url):
    """Debug RSS feed content"""
    print(f"\n🔍 DEBUGGING RSS FEED: {feed_url}")
    print("=" * 60)
    
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
        
        print(f"\n📋 Summary (first 200 chars):")
        summary = entry.get('summary', '')
        print(f"  {summary[:200]}...")
        
        print(f"\n📄 Content:")
        for i, content in enumerate(entry.get('content', [])):
            content_value = content.get('value', '')
            print(f"  {i}: {content_value[:200]}...")
    
    return feed

if __name__ == "__main__":
    feeds = [
        "http://export.arxiv.org/rss/cs.MA",
        "http://export.arxiv.org/rss/cs.CE", 
        "http://export.arxiv.org/rss/q-bio.BM"
    ]
    
    for feed_url in feeds:
        debug_rss_feed(feed_url)