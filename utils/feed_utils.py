"""Shared utilities for RSS feed operations"""
import re
import feedparser
from typing import List, Dict, Optional

# Reusable patterns
PDF_REGEX = re.compile(r'https?://[^\s<>"\']+\.(?:pdf|PDF)(?:\?[^&\s]*)?(?:&[^&\s]*)?', re.IGNORECASE)
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

def parse_feed(url: str) -> feedparser.FeedParserDict:
    """Parse an RSS/Atom feed"""
    return feedparser.parse(url)

def extract_pdf_links(entry: Dict) -> List[str]:
    """Extract PDF links from a feed entry"""
    pdf_links = []
    
    # Check summary
    summary = entry.get('summary', '')
    pdf_links.extend(PDF_REGEX.findall(summary))
    
    # Check content blocks
    for content in entry.get('content', []):
        content_value = content.get('value', '')
        pdf_links.extend(PDF_REGEX.findall(content_value))
    
    # Check direct links
    for link in entry.get('links', []):
        href = link.get('href', '')
        if href.lower().endswith('.pdf'):
            pdf_links.append(href)
    
    return list(set(pdf_links))  # Deduplicate

def test_feed(url: str, name: str, check_keywords: Optional[List[str]] = None) -> Dict:
    """
    Test a feed and return results
    
    Args:
        url: Feed URL
        name: Human-readable name
        check_keywords: Optional keywords to search for in entries
        
    Returns:
        Dict with feed stats and PDF links
    """
    print(f"Testing {name}: {url}")
    
    try:
        feed = parse_feed(url)
        
        # Check for errors
        if hasattr(feed, 'status') and feed.status != 200:
            print(f"  ❌ HTTP error: {feed.status}")
            return {'success': False, 'error': f'HTTP {feed.status}'}
        
        entry_count = len(feed.entries)
        print(f"  Entries: {entry_count}")
        print(f"  Title: {feed.feed.get('title', 'N/A')}")
        
        if not feed.entries:
            print("  ⚠️  No entries found")
            return {'success': True, 'entries': 0, 'pdfs': []}
        
        # Check first entry
        entry = feed.entries[0]
        print(f"  First entry: {entry.get('title', 'N/A')}")
        
        # Extract PDF links
        pdf_links = extract_pdf_links(entry)
        
        if pdf_links:
            print(f"  ✅ Found {len(pdf_links)} PDF links")
            for pdf_link in pdf_links[:3]:
                print(f"    - {pdf_link}")
        else:
            print("  ⚠️  No PDF links found")
        
        # Check keywords if provided
        if check_keywords:
            summary = entry.get('summary', '').lower()
            found = [kw for kw in check_keywords if kw in summary]
            if found:
                print(f"  🔍 Keywords found: {', '.join(found)}")
        
        print()
        return {
            'success': True,
            'entries': entry_count,
            'pdfs': pdf_links,
            'title': feed.feed.get('title')
        }
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print()
        return {'success': False, 'error': str(e)}