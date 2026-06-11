#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import logging
import json
import sys
from collections import Counter
from pathlib import Path

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lenses import LENS_REGISTRY, detect_multi_lens  # noqa: E402
from utils.source_triage import load_keep_manifest, scan_pdfs  # noqa: E402
from utils.text_utils import chunk_sentences  # noqa: E402


DEFAULT_LENS_ORDER = ["building_physics", "climate", "compliance", "failure", "insurance_risk", "materials"]
logger = logging.getLogger(__name__)


def _default_cache_dir() -> Path:
    return ROOT / "cache" / "rss"


def _default_manifest_path() -> Path:
    return ROOT / "exports" / "source_triage" / "construction_science_keep.json"


def _default_output_dir() -> Path:
    return ROOT / "exports" / "lens_evaluation"


def _is_review_bucket_pdf(path: Path) -> bool:
    review_dir = (ROOT / "cache" / "rss_organized" / "construction_science" / "review").resolve()
    try:
        return path.resolve().is_relative_to(review_dir)
    except AttributeError:
        resolved = path.resolve()
        return str(resolved).startswith(str(review_dir))


def _normalize_manifest_entries(manifest_path: Path) -> set[str]:
    normalized: set[str] = set()
    for item in load_keep_manifest(manifest_path):
        item_path = Path(item)
        if not item_path.is_absolute():
            item_path = ROOT / item_path
        normalized.add(item_path.resolve().as_posix())
    return normalized


def _select_lens_order() -> list[str]:
    return [lens_name for lens_name in DEFAULT_LENS_ORDER if lens_name in LENS_REGISTRY]


def _triage_priority(row) -> tuple[int, int, int, int, int, str]:
    return (
        -(row.building_physics_score + row.materials_score + row.failure_score + row.climate_score),
        -row.building_physics_score,
        -row.materials_score,
        -row.failure_score,
        -row.climate_score,
        row.title.lower(),
    )


def _collect_candidate_pdfs(
    cache_dir: Path,
    manifest_entries: set[str],
    limit: int,
    triage_limit: int | None,
) -> list[Path]:
    keep_files = []
    for item in sorted(manifest_entries):
        pdf_path = Path(item)
        if pdf_path.exists() and pdf_path.suffix.lower() == ".pdf":
            keep_files.append(pdf_path)

    seen = {path.resolve().as_posix() for path in keep_files}

    review_dir = ROOT / "cache" / "rss_organized" / "construction_science" / "review"
    if review_dir.exists():
        for pdf_path in sorted(review_dir.rglob("*.pdf")):
            resolved = pdf_path.resolve().as_posix()
            if resolved in seen:
                continue
            keep_files.append(pdf_path)
            seen.add(resolved)
            if len(keep_files) >= limit:
                return keep_files[:limit]

    if len(keep_files) < limit:
        scan_limit = triage_limit if triage_limit is not None else None
        triaged_rows = scan_pdfs(cache_dir, limit=scan_limit)
        triaged_rows = [
            row
            for row in triaged_rows
            if row.keep_skip_review in {"keep", "review"} and row.detected_domain == "construction_science"
        ]
        triaged_rows.sort(key=_triage_priority)
        for row in triaged_rows:
            pdf_path = Path(row.file_path)
            resolved = pdf_path.resolve().as_posix()
            if resolved in seen:
                continue
            keep_files.append(pdf_path)
            seen.add(resolved)
            if len(keep_files) >= limit:
                break

    return keep_files[:limit]


def _relative_repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _scan_pdf_for_lenses(pdf_path: Path, lens_order: list[str]) -> tuple[dict[str, int], int, int, int]:
    lens_counts = {lens_name: 0 for lens_name in lens_order}
    sentence_count = 0
    page_count = 0
    error_count = 0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                for sentence in chunk_sentences(text):
                    sentence_count += 1
                    results = detect_multi_lens(sentence, enabled_lenses=lens_order)
                    for result in results:
                        lens_name = result.get("lens")
                        if lens_name in lens_counts:
                            lens_counts[lens_name] += 1
    except (OSError, IOError, PDFSyntaxError):
        logger.exception("Handled PDF scan error for %s", pdf_path)
        error_count = 1
    except Exception:
        logger.exception("Failed to scan PDF %s", pdf_path)
        error_count = 1

    return lens_counts, sentence_count, page_count, error_count


def _build_rows(pdf_paths: list[Path], lens_order: list[str]) -> tuple[list[dict], Counter, Counter]:
    rows: list[dict] = []
    lens_totals: Counter[str] = Counter()
    lens_pdf_totals: Counter[str] = Counter()

    for index, pdf_path in enumerate(pdf_paths, start=1):
        print(f"[{index}/{len(pdf_paths)}] {pdf_path.name}", flush=True)
        lens_counts, sentence_count, page_count, error_count = _scan_pdf_for_lenses(pdf_path, lens_order)
        total_hits = sum(lens_counts.values())
        dominant_lens = max(lens_counts.items(), key=lambda item: (item[1], item[0]))[0] if total_hits else ""
        row = {
            "pdf_name": pdf_path.name,
            "pages": page_count,
            "sentences": sentence_count,
            "total_hits": total_hits,
            "dominant_lens": dominant_lens,
            "scan_error": error_count,
        }
        for lens_name in lens_order:
            count = lens_counts[lens_name]
            row[f"{lens_name}_hits"] = count
            lens_totals[lens_name] += count
            if count:
                lens_pdf_totals[lens_name] += 1
        rows.append(row)

    return rows, lens_totals, lens_pdf_totals


def _write_csv(rows: list[dict], lens_order: list[str], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["pdf_name", "pages", "sentences", "total_hits", "dominant_lens", "scan_error"]
    fieldnames.extend(f"{lens_name}_hits" for lens_name in lens_order)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def _write_markdown(rows: list[dict], lens_order: list[str], summary: dict[str, object], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["PDF", *[lens.replace("_", " ").title() for lens in lens_order], "Total", "Dominant"]

    lines = ["# Construction Lens Evaluation", ""]
    lines.append(f"- PDFs evaluated: {summary['pdfs_evaluated']}")
    lines.append(f"- PDFs from keep manifest: {summary['manifest_pdfs']}")
    lines.append(f"- PDFs from review bucket: {summary['review_bucket_pdfs']}")
    lines.append(f"- PDFs added from triage: {summary['triaged_pdfs']}")
    lines.append("")

    lines.append("## Aggregate Hits")
    for lens_name in lens_order:
        lines.append(
            f"- {lens_name}: {summary['lens_total_hits'][lens_name]} hits across {summary['lens_pdf_hits'][lens_name]} PDFs"
        )
    lines.append("")

    lines.append("## Per-PDF Table")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in sorted(rows, key=lambda item: (-item["total_hits"], item["pdf_name"])):
        values = [
            row["pdf_name"],
            *[str(row[f"{lens_name}_hits"]) for lens_name in lens_order],
            str(row["total_hits"]),
            row["dominant_lens"] or "-",
        ]
        lines.append("| " + " | ".join(values) + " |")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate all construction lenses over the same PDF sample set")
    parser.add_argument("--cache-dir", type=Path, default=_default_cache_dir(), help="RSS cache directory")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_default_manifest_path(),
        help="Construction keep manifest used to seed the evaluation set",
    )
    parser.add_argument("--output-dir", type=Path, default=_default_output_dir(), help="Folder for evaluation outputs")
    parser.add_argument("--limit", type=int, default=25, help="Number of PDFs to evaluate")
    parser.add_argument(
        "--triage-limit",
        type=int,
        default=None,
        help="Optional maximum cache PDFs to triage when expanding beyond the keep manifest",
    )
    args = parser.parse_args(argv)

    lens_order = _select_lens_order()
    if not lens_order:
        print("ERROR: No construction lenses are available")
        return 1

    if not args.cache_dir.exists():
        print(f"ERROR: cache directory not found: {args.cache_dir}")
        return 1

    if not args.manifest.exists():
        print(f"ERROR: manifest file not found: {args.manifest}")
        return 1

    manifest_entries = _normalize_manifest_entries(args.manifest)
    pdf_paths = _collect_candidate_pdfs(
        args.cache_dir,
        manifest_entries,
        args.limit,
        args.triage_limit,
    )
    if not pdf_paths:
        print("ERROR: No construction PDFs were selected for evaluation")
        return 1

    rows, lens_totals, lens_pdf_totals = _build_rows(pdf_paths, lens_order)
    total_hits = sum(row["total_hits"] for row in rows)
    top_pdfs = sorted(rows, key=lambda row: (-row["total_hits"], row["pdf_name"]))[:10]
    manifest_selected_count = sum(1 for path in pdf_paths if path.resolve().as_posix() in manifest_entries)

    summary = {
        "pdfs_evaluated": len(rows),
        "manifest_pdfs": manifest_selected_count,
        "review_bucket_pdfs": sum(1 for path in pdf_paths if _is_review_bucket_pdf(path)),
        "triaged_pdfs": len(rows) - manifest_selected_count,
        "total_hits": total_hits,
        "lens_total_hits": dict(lens_totals),
        "lens_pdf_hits": dict(lens_pdf_totals),
        "top_pdfs": top_pdfs,
        "selected_pdfs": [_relative_repo_path(path) for path in pdf_paths],
    }

    output_dir = args.output_dir
    csv_path = _write_csv(rows, lens_order, output_dir / "construction_lens_comparison.csv")
    md_path = _write_markdown(rows, lens_order, summary, output_dir / "construction_lens_comparison.md")
    summary_path = output_dir / "construction_lens_comparison_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print("SUMMARY")
    print(f"pdfs_evaluated: {summary['pdfs_evaluated']}")
    print(f"total_hits: {summary['total_hits']}")
    for lens_name in lens_order:
        print(f"{lens_name}: hits={summary['lens_total_hits'][lens_name]} pdfs={summary['lens_pdf_hits'][lens_name]}")
    print("TOP PDFs")
    for row in top_pdfs:
        print(f"  {row['total_hits']:>4} hits | {row['pdf_name']}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())