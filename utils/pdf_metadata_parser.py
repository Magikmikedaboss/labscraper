"""
PDF metadata parsing and normalization utilities
"""
import re
from typing import Dict, Any

def extract_year_from_creation_date(creation_date: str) -> int | None:
    """Extracts year from PDF creation date string."""
    if not creation_date or not isinstance(creation_date, str):
        return None
    match = re.search(r'(19|20)\d{2}', creation_date)
    if match:
        return int(match.group(0))
    return None

def parse_first_page_text(text: str) -> Dict[str, Any]:
    """Parse first page text for title, authors, year, and DOI."""
    meta = {"title": None, "authors": None, "year": None, "doi": None}
    lines = text.splitlines()
    if lines:
        meta["title"] = lines[0].strip()
    if len(lines) > 1:
        meta["authors"] = lines[1].strip()
    # DOI extraction: only set if valid regex or clean 'doi:' suffix
    for line in lines:
        if "doi" in line.lower() and not meta["doi"]:
            doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", line, re.I)
            if doi_match:
                meta["doi"] = doi_match.group(0)
            else:
                # Try to extract after 'doi:' or 'DOI:'
                parts = re.split(r"doi:\s*", line, flags=re.I)
                if len(parts) > 1:
                    candidate = parts[1].strip()
                    if re.match(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", candidate, re.I):
                        meta["doi"] = candidate
    # Year extraction: scan from end to avoid picking from title
    for line in reversed(lines):
        year_match = re.search(r"(19|20)\d{2}", line)
        if year_match and not meta["year"]:
            meta["year"] = int(year_match.group(0))
    return meta
