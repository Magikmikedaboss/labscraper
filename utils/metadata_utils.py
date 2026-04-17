"""
PDF metadata extraction utility
"""
from pathlib import Path
import pdfplumber
from typing import Dict, Any

def extract_metadata(pdf_path: str | Path, pdf=None) -> Dict[str, Any]:
    """
    Extract metadata from a PDF file. Tries to get title, authors, year, and DOI from PDF metadata or first page text.
    If a pdfplumber PDF object is provided, use it directly (for testing/mocking).
    """
    pdf_path = Path(pdf_path)
    meta = {"title": None, "authors": None, "year": None, "doi": None}
    try:
        import re
        def extract_year_from_creation_date(creation_date):
            # Handles formats like 'D:20240101000000' or '2024-01-01T00:00:00Z'
            match = re.search(r'(19|20)\\d{2}', creation_date)
            if match:
                return int(match.group(0))
            return None
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
                if not meta["title"] or not meta["authors"] or not meta["year"]:
                    first_page = pdf.pages[0] if pdf.pages else None
                    if first_page:
                        text = first_page.extract_text() or ""
                        lines = text.splitlines()
                        if not meta["title"] and lines:
                            meta["title"] = lines[0].strip()
                        if not meta["authors"] and len(lines) > 1:
                            meta["authors"] = lines[1].strip()
                        if not meta["year"]:
                            for line in lines:
                                match = re.search(r"(19|20)\\d{2}", line)
                                if match:
                                    meta["year"] = int(match.group(0))
                                    break
                        if not meta["doi"]:
                            for line in lines:
                                if "doi" in line.lower():
                                    meta["doi"] = line.strip()
                                    break
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
                    match = re.search(r"(19|20)\\d{2}", text)
                    if match:
                        meta["year"] = int(match.group(0))
            if hasattr(pdf, "pages") and pdf.pages:
                first_page = pdf.pages[0]
                text = first_page.extract_text() or ""
                lines = text.splitlines()
                if not meta["title"] and lines:
                    meta["title"] = lines[0].strip()
                if not meta["authors"] and len(lines) > 1:
                    meta["authors"] = lines[1].strip()
                if not meta["doi"]:
                    for line in lines:
                        if "doi" in line.lower():
                            match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", line, re.I)
                            if match:
                                meta["doi"] = match.group(0)
                            else:
                                meta["doi"] = line.strip()
                            break
        # Use provided pdfplumber PDF object (for testing/mocking)
        if pdf is not None:
            doc_meta = getattr(pdf, "metadata", {}) or {}
            meta["title"] = doc_meta.get("Title")
            meta["authors"] = doc_meta.get("Author")
            if doc_meta.get("CreationDate"):
                import re
                match = re.search(r"(19|20)\\d{2}", doc_meta["CreationDate"])
                if match:
                    meta["year"] = int(match.group(0))
            if not meta["year"]:
                # Try to extract year from first page text
                if hasattr(pdf, "pages") and pdf.pages:
                    first_page = pdf.pages[0]
                    text = first_page.extract_text() or ""
                    import re
                    match = re.search(r"(19|20)\\d{2}", text)
                    if match:
                        meta["year"] = int(match.group(0))
            if hasattr(pdf, "pages") and pdf.pages:
                first_page = pdf.pages[0]
                text = first_page.extract_text() or ""
                lines = text.splitlines()
                if not meta["title"] and lines:
                    meta["title"] = lines[0].strip()
                if not meta["authors"] and len(lines) > 1:
                    meta["authors"] = lines[1].strip()
                if not meta["doi"]:
                    for line in lines:
                        if "doi" in line.lower():
                            import re
                            match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", line, re.I)
                            if match:
                                meta["doi"] = match.group(0)
                            else:
                                meta["doi"] = line.strip()
                            break
    except Exception as e:
        meta["error"] = str(e)
    # Clean up authors (split if comma-separated)
    if meta["authors"] and isinstance(meta["authors"], str):
        meta["authors"] = meta["authors"].strip()
    return meta
