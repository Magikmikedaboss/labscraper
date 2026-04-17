"""
PDF metadata extraction utility
"""

from pathlib import Path
import pdfplumber
from typing import Dict, Any
from utils.pdf_metadata_parser import extract_year_from_creation_date, parse_first_page_text


def extract_metadata(pdf_path: str | Path, pdf=None) -> Dict[str, Any]:
    """
    Extract metadata from a PDF file. Tries to get title, authors, year, and DOI from PDF metadata or first page text.
    If a pdfplumber PDF object is provided, use it directly (for testing/mocking).
    """
    pdf_path = Path(pdf_path)
    meta = {"title": None, "authors": None, "year": None, "doi": None}
    try:
        if pdf is None:
            with pdfplumber.open(str(pdf_path)) as pdf_obj:
                pdf = pdf_obj
                doc_meta = pdf.metadata or {}
                meta["title"] = doc_meta.get("Title")
                meta["authors"] = doc_meta.get("Author")
                if doc_meta.get("CreationDate"):
                    meta["year"] = extract_year_from_creation_date(doc_meta["CreationDate"])
                if doc_meta.get("Subject") and "doi" in doc_meta["Subject"].lower():
                    meta["doi"] = doc_meta["Subject"]
                # Fallback to first page text if needed
                if not meta["title"] or not meta["authors"] or not meta["year"] or not meta["doi"]:
                    first_page = pdf.pages[0] if pdf.pages else None
                    if first_page:
                        text = first_page.extract_text() or ""
                        parsed = parse_first_page_text(text)
                        for k, v in parsed.items():
                            if not meta[k] and v:
                                meta[k] = v
        else:
            # Use provided pdfplumber PDF object (for testing/mocking)
            doc_meta = getattr(pdf, "metadata", {}) or {}
            meta["title"] = doc_meta.get("Title")
            meta["authors"] = doc_meta.get("Author")
            if doc_meta.get("CreationDate"):
                meta["year"] = extract_year_from_creation_date(doc_meta["CreationDate"])
            if not meta["year"]:
                # Try to extract year from first page text
                if hasattr(pdf, "pages") and pdf.pages:
                    first_page = pdf.pages[0]
                    text = first_page.extract_text() or ""
                    parsed = parse_first_page_text(text)
                    if parsed["year"]:
                        meta["year"] = parsed["year"]
            if hasattr(pdf, "pages") and pdf.pages:
                first_page = pdf.pages[0]
                text = first_page.extract_text() or ""
                parsed = parse_first_page_text(text)
                for k, v in parsed.items():
                    if not meta[k] and v:
                        meta[k] = v
    except Exception as e:
        meta["error"] = str(e)
    # Clean up authors (split if comma-separated)
    if meta["authors"] and isinstance(meta["authors"], str):
        meta["authors"] = meta["authors"].strip()
    return meta
