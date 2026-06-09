"""Organize PDFs into domain/status folders while skipping duplicate content."""

from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from pdfminer.pdfexceptions import PDFNotImplementedError
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException

from utils.source_triage import TriagedSource, scan_pdf


DEFAULT_INPUT_ROOTS = [Path("cache/rss"), Path("input/pdfs")]
DEFAULT_OUTPUT_ROOT = Path("organized_pdfs")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrganizedPdf:
    source_path: Path
    destination_path: Path
    detected_domain: str
    keep_skip_review: str
    confidence: str
    title: str
    reason: str
    content_hash: str
    is_duplicate: bool
    duplicate_of: str


def _safe_label(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value.strip().lower())
    return cleaned or "unknown"


def _pdf_sha256(pdf_path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with pdf_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_pdf_paths(input_roots: list[Path], limit: int | None = None) -> list[tuple[Path, Path]]:
    pdf_paths: list[tuple[Path, Path]] = []
    for root in input_roots:
        if not root.exists() or not root.is_dir():
            continue
        for pdf_path in sorted(root.rglob("*.pdf")):
            pdf_paths.append((root, pdf_path))
            if limit is not None and len(pdf_paths) >= limit:
                return pdf_paths
    return pdf_paths


def _destination_path(output_root: Path, input_root: Path, pdf_path: Path, triage: TriagedSource) -> Path:
    relative_path = pdf_path.relative_to(input_root)
    domain_folder = _safe_label(triage.detected_domain)
    status_folder = _safe_label(triage.keep_skip_review)
    source_folder = _safe_label(input_root.name)
    return output_root / domain_folder / status_folder / source_folder / relative_path


def organize_pdfs(
    *,
    input_roots: list[Path],
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    limit: int | None = None,
    first_pages: int = 2,
    max_chars: int = 1600,
    dry_run: bool = False,
    action: str = "copy",
) -> list[OrganizedPdf]:
    results: list[OrganizedPdf] = []
    seen_by_hash: dict[str, OrganizedPdf] = {}
    output_root.mkdir(parents=True, exist_ok=True)

    for input_root, pdf_path in _iter_pdf_paths(input_roots, limit=limit):
        content_hash = _pdf_sha256(pdf_path)
        canonical_row = seen_by_hash.get(content_hash)
        if canonical_row is None:
            try:
                triage = scan_pdf(pdf_path, first_pages=first_pages, max_chars=max_chars)
            except (PDFSyntaxError, PDFNotImplementedError, PdfminerException, OSError, ValueError) as exc:
                triage = TriagedSource(
                    file_path=str(pdf_path),
                    title=pdf_path.stem,
                    detected_domain="unknown",
                    keep_skip_review="review",
                    confidence="low",
                    construction_signals="",
                    contamination_signals="",
                    reason=f"failed to scan PDF ({exc.__class__.__name__}) — see logs",
                )
            is_duplicate = False
            duplicate_of = ""
        else:
            triage = TriagedSource(
                file_path=str(pdf_path),
                title=canonical_row.title,
                detected_domain=canonical_row.detected_domain,
                keep_skip_review=canonical_row.keep_skip_review,
                confidence=canonical_row.confidence,
                construction_signals="",
                contamination_signals="",
                reason=canonical_row.reason,
            )
            is_duplicate = True
            duplicate_of = str(canonical_row.destination_path)
        destination_path = _destination_path(output_root, input_root, pdf_path, triage)
        if not is_duplicate:
            seen_by_hash[content_hash] = OrganizedPdf(
                source_path=pdf_path,
                destination_path=destination_path,
                detected_domain=triage.detected_domain,
                keep_skip_review=triage.keep_skip_review,
                confidence=triage.confidence,
                title=triage.title,
                reason=triage.reason,
                content_hash=content_hash,
                is_duplicate=False,
                duplicate_of="",
            )

        if not dry_run and not is_duplicate:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if action == "move":
                try:
                    shutil.move(str(pdf_path), str(destination_path))
                except (OSError, shutil.Error):
                    shutil.copy2(pdf_path, destination_path)
                    try:
                        os.remove(pdf_path)
                    except OSError:
                        logger.exception("Failed to remove original PDF after copy fallback: %s", pdf_path)
            else:
                shutil.copy2(pdf_path, destination_path)

        results.append(
            OrganizedPdf(
                source_path=pdf_path,
                destination_path=destination_path,
                detected_domain=triage.detected_domain,
                keep_skip_review=triage.keep_skip_review,
                confidence=triage.confidence,
                title=triage.title,
                reason=triage.reason,
                content_hash=content_hash,
                is_duplicate=is_duplicate,
                duplicate_of=duplicate_of,
            )
        )

    return results


def write_organization_index(rows: list[OrganizedPdf], output_root: Path) -> Path:
    index_path = output_root / "organization_index.csv"
    with index_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "source_path",
            "destination_path",
            "detected_domain",
            "keep_skip_review",
            "confidence",
            "title",
            "reason",
            "content_hash",
            "is_duplicate",
            "duplicate_of",
        ])
        for row in rows:
            writer.writerow([
                str(row.source_path),
                str(row.destination_path),
                row.detected_domain,
                row.keep_skip_review,
                row.confidence,
                row.title,
                row.reason,
                row.content_hash,
                str(row.is_duplicate).lower(),
                row.duplicate_of,
            ])
    return index_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize PDFs into domain and triage folders while skipping duplicates")
    parser.add_argument(
        "--input-root",
        action="append",
        dest="input_roots",
        type=Path,
        help="PDF root to scan (can be repeated)",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="Where organized PDFs are written")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for quick smoke tests")
    parser.add_argument("--first-pages", type=int, default=2, help="Number of first pages to sample")
    parser.add_argument("--max-chars", type=int, default=1600, help="Maximum sampled text per PDF")
    parser.add_argument("--dry-run", action="store_true", help="Classify PDFs without copying or moving")
    parser.add_argument("--move", action="store_true", help="Move PDFs instead of copying them")
    args = parser.parse_args()

    input_roots = args.input_roots or DEFAULT_INPUT_ROOTS
    action = "move" if args.move else "copy"
    rows = organize_pdfs(
        input_roots=input_roots,
        output_root=args.output_root,
        limit=args.limit,
        first_pages=args.first_pages,
        max_chars=args.max_chars,
        dry_run=args.dry_run,
        action=action,
    )

    index_path = write_organization_index(rows, args.output_root)
    print(f"Wrote organization index: {index_path}")
    duplicate_count = sum(1 for row in rows if row.is_duplicate)
    print(f"Processed {len(rows)} PDFs into {args.output_root} ({duplicate_count} duplicates skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
