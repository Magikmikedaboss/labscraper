"""
PDF metadata parsing and normalization utilities
"""
import re
from typing import Dict, Any, Optional

def extract_year_from_creation_date(creation_date: str) -> Optional[int]:
    """Extracts year from PDF creation date string."""
    if not creation_date or not isinstance(creation_date, str):
        return None
    match = re.search(r'(19|20)\d{2}', creation_date)
    if match:
        return int(match.group(0))
    return None

def parse_first_page_text(text: str, max_header_scan: int = 10) -> Dict[str, Any]:
    """Parse first page text for title, authors, year, and DOI.
    Uses heuristics to skip headers/journals and select reasonable title/authors lines.
    Args:
        text: First page text.
        max_header_scan: Number of non-empty lines to scan for title/authors.
    """
    meta = {"title": None, "authors": None, "year": None, "doi": None}
    lines = [line.strip() for line in text.splitlines()]
    nonempty = [line for line in lines if line]
    # Heuristics for skipping header/journal lines for title
    HEADER_PATTERN = re.compile(
        r"("  # Start group
        r"journal|vol(ume)?|issue|page[s]?|issn|doi|copyright|published by|all rights reserved|arxiv|biorxiv|medrxiv|preprint"
        r")",
        re.I,
    )
    # Find title candidate
    title_candidate = None
    for line in nonempty[:max_header_scan]:
        if len(line) < 5:
            continue  # skip very short lines
        if HEADER_PATTERN.search(line):
            continue
        title_candidate = line
        break
    if title_candidate:
        meta["title"] = title_candidate
    else:
        meta["title"] = None
    # Heuristics for authors
    affiliation_keywords = ["university", "institute", "department", "dept", "school", "hospital", "center", "centre", "faculty", "college", "clinic", "laboratory", "lab", "company", "corporation", "inc", "llc", "ltd", "email", "@", ".edu", ".org", ".com", "http://", "https://"]
    author_candidate = None
    for line in nonempty[1:max_header_scan]:
        if any(kw in line.lower() for kw in affiliation_keywords):
            continue
        if re.search(r"@|http[s]?://|www\.", line):
            continue
        if ("," in line or " and " in line.lower()) and 3 < len(line) < 200:
            author_candidate = line
            break
    if author_candidate:
        meta["authors"] = author_candidate
    elif len(nonempty) > 1:
        meta["authors"] = nonempty[1]
    # DOI extraction: only set if valid regex or clean 'doi:' suffix
    for line in lines:
        if "doi" in line.lower() and not meta["doi"]:
            doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9<>%+,]+", line, re.I)
            if doi_match:
                doi_val = doi_match.group(0).rstrip(".,;:")
                meta["doi"] = doi_val
            else:
                # Try to extract after 'doi:' or 'DOI:'
                parts = re.split(r"doi:\s*", line, flags=re.I)
                if len(parts) > 1:
                    candidate = parts[1].strip()
                    match = re.match(r"10\.\d{4,9}/[-._;()/:A-Z0-9<>%+,]+", candidate, re.I)
                    if match:
                        doi_val = match.group(0).rstrip(".,;:")
                        meta["doi"] = doi_val
    # Year extraction: scan from end to avoid picking from title
    for line in reversed(lines):
        year_match = re.search(r"(19|20)\d{2}", line)
        if year_match:
            meta["year"] = int(year_match.group(0))
            break
    return meta
