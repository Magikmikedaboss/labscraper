#!/usr/bin/env python3
"""
Test arXiv RSS feeds to find working URLs
"""

import feedparser

def test_arxiv_feed(url, name):
    """Test an arXiv RSS feed"""
    print(f"Testing {name}: {url}")
    try:
        feed = feedparser.parse(url)
        print(f"  Entries: {len(feed.entries)}")
        print(f"  Title: {feed.feed.get('title', 'N/A')}")
        if feed.entries:
            print(f"  First entry: {feed.entries[0].get('title', 'N/A')}")
        print()
    except Exception as e:
        print(f"  Error: {e}")
        print()

def main():
    """Test various arXiv feed URLs"""
    feeds = [
        ("http://export.arxiv.org/rss/cs.MA", "Materials Science"),
        ("http://export.arxiv.org/rss/cs.CE", "Computational Engineering"),
        ("http://export.arxiv.org/rss/q-bio.BM", "Biomaterials"),
        ("http://export.arxiv.org/rss/cs", "Computer Science"),
        ("http://export.arxiv.org/rss/physics", "Physics"),
        ("http://export.arxiv.org/rss/math", "Mathematics"),
    ]
    
    for url, name in feeds:
        test_arxiv_feed(url, name)

if __name__ == "__main__":
    main()