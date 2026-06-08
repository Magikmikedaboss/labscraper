
"""
PDF metadata extraction utility
"""

from __future__ import annotations
from pathlib import Path
import pdfplumber
import logging

from typing import Dict, Any, Union
import re
from pdfminer.pdfparser import PDFException
from pdfminer.psparser import PSException
from utils.pdf_metadata_parser import extract_year_from_creation_date, parse_first_page_text


logger = logging.getLogger(__name__)
AUTHOR_SEPARATOR = "; "


def _extract_meta_from_pdf(pdf, meta):
    """
    Helper to extract metadata from a pdfplumber PDF object and update meta dict.
    Handles precedence: CreationDate -> parsed year fallback, Subject -> doi detection, fallback to first-page parsed fields.
    """
    raw_meta = getattr(pdf, "metadata", None)
    doc_meta = raw_meta if raw_meta is not None else {}
    meta["title"] = doc_meta.get("Title")
    meta["authors"] = doc_meta.get("Author")
    year_from_creation = None
    if doc_meta.get("CreationDate"):
        year_from_creation = extract_year_from_creation_date(doc_meta["CreationDate"])
        meta["year"] = year_from_creation
    if doc_meta.get("Subject") and "doi" in doc_meta["Subject"].lower():
        subject = doc_meta["Subject"]
        doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9<>%+,]+", subject, re.I)
        if doi_match:
            doi_value = doi_match.group(0).rstrip(".,;:")
            if re.search(r"\([^)]+\)$", doi_value):
                doi_value = re.sub(r"\([^)]+\)$", "", doi_value).rstrip(".,;:")
            meta["doi"] = doi_value
    parsed = None
    if hasattr(pdf, "pages") and pdf.pages:
        first_page = pdf.pages[0]
        text = first_page.extract_text() or ""
        parsed = parse_first_page_text(text)
    if parsed:
        if not year_from_creation and parsed.get("year"):
            meta["year"] = parsed["year"]
        for k, v in parsed.items():
            if k in meta and not meta.get(k) and v:
                meta[k] = v


def extract_metadata(pdf_path: Union[str, Path], pdf=None) -> Dict[str, Any]:
    """
    Extract metadata from a PDF file. Tries to get title, authors, year, and DOI from PDF metadata or first page text.
    If a pdfplumber PDF object is provided, use it directly (for testing/mocking).
    """
    pdf_path = Path(pdf_path)
    meta = {"title": None, "authors": None, "year": None, "doi": None}
    try:
        if pdf is None:
            with pdfplumber.open(str(pdf_path)) as pdf_obj:
                _extract_meta_from_pdf(pdf_obj, meta)
        else:
            _extract_meta_from_pdf(pdf, meta)
    except (OSError, PDFException, PSException) as e:
        logger.exception("Error extracting metadata from %s", pdf_path)
        meta["error"] = str(e)
    # Authors may arrive as a string or a sequence; serialize sequences with a separator that
    # preserves names containing commas for downstream storage and dedupe.
    if isinstance(meta["authors"], list):
        meta["authors"] = AUTHOR_SEPARATOR.join(str(author).strip() for author in meta["authors"] if author is not None)
    elif isinstance(meta["authors"], str):
        meta["authors"] = meta["authors"].strip()
    elif meta["authors"] is not None:
        meta["authors"] = str(meta["authors"]).strip()
    return meta
