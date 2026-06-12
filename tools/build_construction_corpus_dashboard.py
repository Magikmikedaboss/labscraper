#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.evaluate_construction_lenses import (  # noqa: E402
    _default_gold_corpus_path,
    _default_manifest_path,
    _default_output_dir,
    _is_review_bucket_pdf,
    _load_gold_corpus_paths,
    _normalize_manifest_entries,
    _relative_repo_path,
)


LENS_COLUMNS = [
    "building_physics",
    "climate",
    "compliance",
    "failure",
    "insurance_risk",
    "materials",
]


def _default_summary_path() -> Path:
    return _default_output_dir() / "construction_lens_comparison_summary.json"


def _default_csv_path() -> Path:
    return _default_output_dir() / "construction_lens_comparison.csv"


def _source_name(path: Path, manifest_entries: set[str], gold_corpus_ids: set[str]) -> str:
    resolved = path.resolve().as_posix()
    if resolved in manifest_entries:
        return "keep_manifest"
    if _is_review_bucket_pdf(path):
        return "review_bucket"
    if resolved in gold_corpus_ids:
        return "gold_corpus"
    return "triage"


def _load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_dashboard_rows(summary: dict[str, object], csv_rows: list[dict[str, str]], manifest_path: Path, gold_corpus_path: Path) -> list[dict[str, object]]:
    selected_paths = summary.get("selected_pdfs", [])
    if not isinstance(selected_paths, list):
        selected_paths = []
    if len(selected_paths) != len(csv_rows):
        raise ValueError(
            f"dashboard row mismatch: selected_pdfs={len(selected_paths)} csv_rows={len(csv_rows)}"
        )

    manifest_entries = _normalize_manifest_entries(manifest_path)
    gold_corpus_ids = {path.resolve().as_posix() for path in _load_gold_corpus_paths(gold_corpus_path)}

    dashboard_rows: list[dict[str, object]] = []
    for selected_path, row in zip(selected_paths, csv_rows):
        path = Path(str(selected_path))
        source = _source_name(path, manifest_entries, gold_corpus_ids)
        pages = int(row.get("pages", 0) or 0)
        sentences = int(row.get("sentences", 0) or 0)
        total_hits = int(row.get("total_hits", 0) or 0)
        density = (total_hits / pages) if pages else 0.0
        lens_distribution = []
        for lens_name in LENS_COLUMNS:
            count = int(row.get(f"{lens_name}_hits", 0) or 0)
            if count:
                lens_distribution.append(f"{lens_name}={count}")
        dashboard_rows.append(
            {
                "path": _relative_repo_path(ROOT / path),
                "pdf_name": row.get("pdf_name", path.name),
                "source": source,
                "pages": pages,
                "sentences": sentences,
                "total_hits": total_hits,
                "hits_per_page": density,
                "dominant_lens": row.get("dominant_lens", "") or "-",
                "lens_distribution": "; ".join(lens_distribution) if lens_distribution else "-",
            }
        )

    dashboard_rows.sort(key=lambda item: (-item["total_hits"], item["path"]))
    return dashboard_rows


def _write_csv(rows: list[dict[str, object]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path",
        "pdf_name",
        "source",
        "pages",
        "sentences",
        "total_hits",
        "hits_per_page",
        "dominant_lens",
        "lens_distribution",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return output_path


def _write_markdown(summary: dict[str, object], rows: list[dict[str, object]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_counts = Counter(row["source"] for row in rows)

    lines = ["# Construction Corpus Dashboard", ""]
    lines.append(f"- Unique PDFs: {summary.get('pdfs_evaluated', 0)}")
    lines.append(f"- Duplicate PDFs collapsed by hash: {summary.get('duplicate_pdfs_collapsed', 0)}")
    lines.append(f"- Total hits: {summary.get('total_hits', 0)}")
    lines.append(
        f"- Top PDF concentration: {summary.get('top_pdf_concentration_ratio', 0.0):.1%} ({summary.get('top_pdf_hits', 0)} top hits)"
    )
    lines.append("")
    lines.append("## Source Mix")
    for source_name in ["keep_manifest", "review_bucket", "gold_corpus", "triage"]:
        lines.append(f"- {source_name}: {source_counts.get(source_name, 0)}")
    lines.append("")
    lines.append("## Lens Totals")
    lens_total_hits = summary.get("lens_total_hits", {})
    lens_pdf_hits = summary.get("lens_pdf_hits", {})
    for lens_name in LENS_COLUMNS:
        lines.append(
            f"- {lens_name}: {lens_total_hits.get(lens_name, 0)} hits across {lens_pdf_hits.get(lens_name, 0)} PDFs"
        )
    lines.append("")
    lines.append("## Per-PDF Table")
    lines.append("| PDF | Source | Pages | Sentences | Hits | Hits/Page | Dominant | Lens Distribution |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["path"]),
                    str(row["source"]),
                    str(row["pages"]),
                    str(row["sentences"]),
                    str(row["total_hits"]),
                    f"{row['hits_per_page']:.2f}",
                    str(row["dominant_lens"]),
                    str(row["lens_distribution"]),
                ]
            )
            + " |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _write_json(summary: dict[str, object], rows: list[dict[str, object]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"summary": summary, "rows": rows}
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a construction corpus dashboard from evaluation outputs")
    parser.add_argument("--summary", type=Path, default=_default_summary_path(), help="Comparison summary JSON")
    parser.add_argument("--csv", type=Path, default=_default_csv_path(), help="Comparison CSV with per-PDF rows")
    parser.add_argument("--manifest", type=Path, default=_default_manifest_path(), help="Keep manifest used for source mix")
    parser.add_argument("--gold-corpus", type=Path, default=_default_gold_corpus_path(), help="Core corpus used for source mix")
    parser.add_argument("--output-dir", type=Path, default=_default_output_dir(), help="Folder for dashboard outputs")
    args = parser.parse_args(argv)

    if not args.summary.exists():
        print(f"ERROR: summary file not found: {args.summary}")
        return 1
    if not args.csv.exists():
        print(f"ERROR: csv file not found: {args.csv}")
        return 1

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    csv_rows = _load_csv_rows(args.csv)
    dashboard_rows = _load_dashboard_rows(summary, csv_rows, args.manifest, args.gold_corpus)
    output_dir = args.output_dir
    csv_path = _write_csv(dashboard_rows, output_dir / "construction_corpus_dashboard.csv")
    md_path = _write_markdown(summary, dashboard_rows, output_dir / "construction_corpus_dashboard.md")
    json_path = _write_json(summary, dashboard_rows, output_dir / "construction_corpus_dashboard.json")

    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
