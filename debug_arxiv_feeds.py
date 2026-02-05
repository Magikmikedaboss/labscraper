#!/usr/bin/env python3
"""
Debug arXiv RSS feeds to understand their structure
"""

import feedparser

def debug_arxiv_feed(feed_url, feed_name):
    """Debug arXiv RSS feed content"""
    print(f"🔍 DEBUGGING {feed_name}")
    print("=" * 60)
    print(f"URL: {feed_url}")
    
    feed = feedparser.parse(feed_url)
    
    print(f"Feed title: {feed.feed.get('title', 'N/A')}")
    print(f"Feed entries: {len(feed.entries)}")
    
    if feed.entries:
        entry = feed.entries[0]
        print("\n📝 First entry:")
        print(f"  Title: {entry.get('title', 'N/A')}")
        print(f"  Published: {entry.get('published', 'N/A')}")
        
        print("\n🔗 Links:")
        for i, link in enumerate(entry.get('links', [])):
            href = link.get('href', 'N/A')
            link_type = link.get('type', 'N/A')
            rel = link.get('rel', 'N/A')
            print(f"  {i}: {href} (type: {link_type}, rel: {rel})")
        
        print("\n📋 Summary (first 300 chars):")
        summary = entry.get('summary', '')
        print(f"  {summary[:300]}...")
        
        print("\n📄 Content:")
        for i, content in enumerate(entry.get('content', [])):
            content_value = content.get('value', '')
            print(f"  {i}: {content_value[:300]}...")
        
        # Look for PDF links in different places
        print(f"\n🔍 PDF Link Search:")
        pdf_links = []
        
        # Check links
        for link in entry.get('links', []):
            href = link.get('href', '')
            if '.pdf' in href.lower():
                pdf_links.append(href)
        
        # Check summary
        summary = entry.get('summary', '')
        import re
        pdf_matches = re.findall(r'https?://[^\s<>"\']*.pdf', summary, re.IGNORECASE)
        pdf_links.extend(pdf_matches)
        
        # Check content
        for content in entry.get('content', []):
            content_value = content.get('value', '')
            pdf_matches = re.findall(r'https?://[^\s<>"\']*.pdf', content_value, re.IGNORECASE)
            pdf_links.extend(pdf_matches)
        
        if pdf_links:
            print(f"  Found {len(pdf_links)} PDF links:")
            for pdf_link in pdf_links:
                print(f"    - {pdf_link}")
        else:
            print(f"  No PDF links found")
    
    return feed

def main():
    """Debug multiple arXiv feeds"""
    feeds = [
        ("http://export.arxiv.org/rss/cs.MA", "arXiv Materials Science"),
        ("http://export.arxiv.org/rss/cs.CE", "arXiv Computational Engineering"),
        ("http://export.arxiv.org/rss/q-bio.BM", "arXiv Biomaterials")
    ]
    
    for feed_url, feed_name in feeds:
        debug_arxiv_feed(feed_url, feed_name)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()