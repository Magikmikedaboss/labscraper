#!/usr/bin/env python3
"""
Find working construction materials research sources
"""

import requests
import re

def find_construction_materials_pdfs():
    """Find construction materials PDFs from various sources"""
    print("🏗️  FINDING CONSTRUCTION MATERIALS PDF SOURCES")
    print("=" * 60)
    
    # Test some known open-access construction materials sources
    sources = [
        ("https://www.researchgate.net/topic/Construction-Materials", "ResearchGate - Construction Materials"),
        ("https://arxiv.org/search/?query=construction+materials&searchtype=all&abstracts=show&order=-announced_date_first", "arXiv - Construction Materials"),
        ("https://www.sciencedirect.com/search?qs=construction%20materials&articleTypes=FLA", "ScienceDirect - Construction Materials"),
        ("https://www.mdpi.com/journal/materials", "MDPI Materials Journal"),
    ]
    
    for url, name in sources:
        print(f"Checking {name}: {url}")
        try:
            # Use requests with headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Look for PDF links
                pdf_links = re.findall(r'https?://[^\s<>"\']*.pdf', response.text, re.IGNORECASE)
                if pdf_links:
                    print(f"  ✅ Found {len(pdf_links)} PDF links")
                    for pdf_link in pdf_links[:3]:  # Show first 3
                        print(f"    - {pdf_link}")
                else:
                    print(f"  ⚠️  No PDF links found")
            else:
                print(f"  ❌ HTTP {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()

def main():
    """Find construction materials research sources"""
    find_construction_materials_pdfs()

if __name__ == "__main__":
    main()