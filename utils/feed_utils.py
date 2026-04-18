"""Shared utilities for RSS feed operations"""
import re
import feedparser
from typing import List, Dict, Optional

DOC_LINK_REGEX = re.compile(r'https?://[^\s<>"\']+\.(?:pdf|PDF|docx?|DOCX?|html|HTML)(?:\?[^&\s]*)?(?:&[^&\s]*)?', re.IGNORECASE)
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

def parse_feed(url: str):
    """Parse an RSS/Atom feed"""
    try:
        return feedparser.parse(url)
    except Exception:
        # Return empty dict on error (matches test expectation)
        return {}

def extract_pdf_links(entry: Dict) -> List[str]:
    """Extract PDF links from a feed entry"""
    doc_links = []
    # Check summary
    summary = entry.get('summary', '')
    doc_links.extend(DOC_LINK_REGEX.findall(summary))
    # Check content blocks
    for content in entry.get('content', []):
        content_value = content.get('value', '')
        doc_links.extend(DOC_LINK_REGEX.findall(content_value))
    # Check direct links
    for link in entry.get('links', []):
        href = link.get('href', '')
        if href:
            doc_links.extend(DOC_LINK_REGEX.findall(href))
    # Only keep links ending with .pdf (case-insensitive)
    pdf_links = [url for url in set(doc_links) if url.lower().endswith('.pdf')]
    return pdf_links

def probe_feed(url: str, name: str, check_keywords: Optional[List[str]] = None) -> Dict:
    """
    Probe a feed and return results
    
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
        
        # Handle both dict and feedparser object for compatibility
        if isinstance(feed, dict):
            entries = feed.get('entries', [])
            feed_title = feed.get('feed', {}).get('title') if isinstance(feed.get('feed'), dict) else None
            # Check for error status in dict
            if feed.get('status') and feed.get('status') != 200:
                print(f"  ❌ HTTP error: {feed.get('status')}")
                return {'success': False, 'error': f"HTTP {feed.get('status')}"}
        else:
            # feedparser object
            entries = feed.entries if hasattr(feed, 'entries') else []
            feed_title = feed.feed.get('title') if hasattr(feed, 'feed') else None
            if hasattr(feed, 'status') and feed.status != 200:
                print(f"  ❌ HTTP error: {feed.status}")
                return {'success': False, 'error': f'HTTP {feed.status}'}
        
        entry_count = len(entries)
        print(f"  Entries: {entry_count}")
        print(f"  Title: {feed_title or 'N/A'}")
        
        # Filter entries by keywords if provided
        filtered_entries = entries
        if check_keywords:
            # Normalize keywords to lowercase for case-insensitive matching
            normalized_keywords = [kw.lower() for kw in check_keywords]
            # Filter: keep only entries that have keywords (for reporting)
            entries_with_keywords = [
                e for e in entries 
                if any(kw in e.get('summary', '').lower() or kw in e.get('title', '').lower() 
                       for kw in normalized_keywords)
            ]
            # For reporting: show entries that have keywords
            if entries_with_keywords:
                print(f"  🔍 Keywords found in {len(entries_with_keywords)} entries")
            # Use filtered for output (entries WITH keywords)
            filtered_entries = entries_with_keywords
        
        if not filtered_entries:
            print("  ⚠️  No entries found")
            return {'success': True, 'entries': 0, 'pdfs': 0}
        
        # Check first entry (use filtered if available)
        first_entry = filtered_entries[0]
        print(f"  First entry: {first_entry.get('title', 'N/A')}")
        
        # Extract PDF links
        pdf_links = extract_pdf_links(first_entry)
        
        if pdf_links:
            print(f"  ✅ Found {len(pdf_links)} PDF links")
            for pdf_link in pdf_links[:3]:
                print(f"    - {pdf_link}")
        else:
            print("  ⚠️  No PDF links found")
        
        print()
        return {
            'success': True,
            'entries': len(filtered_entries),
            'pdfs': len(pdf_links),
            'title': feed_title
        }
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print()
        return {'success': False, 'error': str(e)}


def test_feed(url: str, name: str, check_keywords: Optional[List[str]] = None) -> Dict:
    """Backward-compatible alias for older scripts."""
    return probe_feed(url, name, check_keywords=check_keywords)