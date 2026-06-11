"""Temporary cache-scan utility for climate lens extraction.

Use explicit limits when running this script; it is intended for ad-hoc/local
analysis rather than unattended production jobs.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pdfplumber

from lenses.construction_climate_v1 import detect
from utils.lens_scan_utils import _configure_logging, _env_limit
from utils.text_utils import chunk_sentences

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent


def _scan_pdf(pdf_path: Path) -> tuple[str, list[dict], int]:
    local_rows: list[dict] = []
    local_hits = 0
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                for sentence in chunk_sentences(text):
                    event, entities = detect(sentence)
                    if event is None:
                        continue
                    local_hits += 1
                    local_rows.append(
                        {
                            "pdf_name": pdf_path.name,
                            "page_number": page_index,
                            "event_type": event.event_type,
                            "outcome": event.outcome,
                            "confidence": event.confidence,
                            "context_strength": event.context_strength,
                            "entity_count": len(entities),
                            "entities": "; ".join(
                                f"{e['entity_type']}:{e.get('entity_name', '')}"
                                + (f"[{e['entity_variant']}]" if e.get('entity_variant') else "")
                                for e in entities
                            ),
                            "sentence": sentence,
                        }
                    )
    except Exception as exc:  # pragma: no cover - ad hoc report utility
        logger.exception("SKIP %s due to %s", pdf_path.name, exc)
    return pdf_path.name, local_rows, local_hits


def main(
    cache_dir: Path = Path("cache/rss"),
    out_dir: Path = Path("tmp/climate_lens_report"),
    max_pdfs: int | None = None,
    progress_interval: int = 25,
) -> int:
    max_pdfs = _env_limit("LABSCRAPER_MAX_PDFS") if max_pdfs is None else max_pdfs

    _configure_logging(logger, out_dir, "climate_lens_cache_results.log")

    pdf_paths = sorted(cache_dir.glob("*.pdf"))
    rows: list[dict] = []
    pdf_hits: dict[str, int] = {}

    logger.info("Starting climate lens cache scan cache_dir=%s max_pdfs=%s", cache_dir, max_pdfs)

    if max_pdfs is not None:
        pdf_paths = pdf_paths[:max_pdfs]

    with ThreadPoolExecutor(max_workers=4) as executor:
        for index, (pdf_name, local_rows, local_hits) in enumerate(executor.map(_scan_pdf, pdf_paths), start=1):
            rows.extend(local_rows)
            if local_hits:
                pdf_hits[pdf_name] = local_hits
            if progress_interval > 0 and index % progress_interval == 0:
                logger.info("Progress processed_pdfs=%s pdf_hits=%s rows=%s", index, len(pdf_hits), len(rows))

    csv_path = out_dir / "climate_lens_cache_hits.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "pdf_name",
                "page_number",
                "event_type",
                "outcome",
                "confidence",
                "context_strength",
                "entity_count",
                "entities",
                "sentence",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "pdfs_scanned": len(pdf_paths),
        "pdfs_with_hits": len(pdf_hits),
        "pdfs_without_hits": len(pdf_paths) - len(pdf_hits),
        "total_hits": len(rows),
        "event_type_counts": {},
        "top_pdfs": sorted(pdf_hits.items(), key=lambda item: (-item[1], item[0]))[:10],
        "csv_path": csv_path.resolve().relative_to(ROOT).as_posix(),
    }
    for row in rows:
        summary["event_type_counts"][row["event_type"]] = summary["event_type_counts"].get(row["event_type"], 0) + 1

    summary_path = out_dir / "climate_lens_cache_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    logger.info("Wrote %s", csv_path)
    logger.info("Wrote %s", summary_path)
    logger.info("climate: pdf_hits=%s, sentence_hits=%s", summary["pdfs_with_hits"], summary["total_hits"])
    for pdf_name, count in summary["top_pdfs"]:
        logger.info("  %s: %s", pdf_name, count)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default="cache/rss")
    parser.add_argument("--out-dir", default="tmp/climate_lens_report")
    parser.add_argument("--max-pdfs", type=int, default=None)
    args = parser.parse_args()
    raise SystemExit(main(cache_dir=Path(args.cache_dir), out_dir=Path(args.out_dir), max_pdfs=args.max_pdfs))
