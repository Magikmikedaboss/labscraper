"""Temporary cache-scan utility for building_physics lens extraction.

Use explicit limits when running this script; it is intended for ad-hoc/local
analysis rather than unattended production jobs.
"""

from __future__ import annotations

import argparse
import csv
import logging
import json
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from pathlib import Path

import pdfplumber

from lenses.construction_building_physics_v1 import detect
from utils.text_utils import chunk_sentences
from utils.lens_scan_utils import _configure_logging, _env_limit

logger = logging.getLogger(__name__)


def _scan_pdf(
    pdf_path: Path,
    source_type: str,
    max_pages_per_pdf: int | None,
    max_sentences_per_page: int | None,
) -> tuple[str, list[dict], int, dict[str, int]]:
    local_rows: list[dict] = []
    local_hits = 0
    local_event_counts: dict[str, int] = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = 0
            for page_index, page in enumerate(pdf.pages, start=1):
                if max_pages_per_pdf is not None and page_count >= max_pages_per_pdf:
                    break
                page_count += 1
                text = page.extract_text() or ''
                if not text.strip():
                    continue
                sentence_count = 0
                for sentence in chunk_sentences(text):
                    if max_sentences_per_page is not None and sentence_count >= max_sentences_per_page:
                        break
                    sentence_count += 1
                    event, entities = detect(sentence, source_type=source_type)
                    if event is None:
                        continue
                    local_hits += 1
                    local_event_counts[event.event_type] = local_event_counts.get(event.event_type, 0) + 1
                    local_rows.append({
                        'pdf_name': pdf_path.name,
                        'page': page_index,
                        'sentence': sentence,
                        'lens': event.lens or 'building_physics',
                        'event_type': event.event_type,
                        'outcome': event.outcome,
                        'confidence': event.confidence,
                        'context_strength': event.context_strength,
                        'source_weight': f'{event.source_weight:.2f}',
                        'tags': '|'.join(event.tags),
                        'entities': json.dumps(entities, ensure_ascii=True),
                    })
    except Exception:
        logger.exception(
            "SKIP %s after pdf_hits=%s total_hits=%s",
            pdf_path.name,
            local_hits,
            local_hits,
        )
    return pdf_path.name, local_rows, local_hits, local_event_counts


def main(
    cache_dir: Path = Path('cache/rss'),
    out_dir: Path = Path('exports/lens_cache_exports'),
    max_pdfs: int | None = None,
    max_pages_per_pdf: int | None = None,
    max_sentences_per_page: int | None = None,
    progress_interval: int = 25,
    source_type: str = 'research_paper',
) -> int:
    max_pdfs = _env_limit('LABSCRAPER_MAX_PDFS') if max_pdfs is None else max_pdfs
    max_pages_per_pdf = _env_limit('LABSCRAPER_MAX_PAGES_PER_PDF') if max_pages_per_pdf is None else max_pages_per_pdf
    max_sentences_per_page = (
        _env_limit('LABSCRAPER_MAX_SENTENCES_PER_PAGE') if max_sentences_per_page is None else max_sentences_per_page
    )

    _configure_logging(logger, out_dir, "building_physics_cache_results.log")

    rows = []
    pdf_hits: dict[str, int] = {}
    event_type_counts: dict[str, int] = {}
    processed_pdfs = 0

    logger.info(
        "Starting building_physics cache scan cache_dir=%s max_pdfs=%s max_pages_per_pdf=%s max_sentences_per_page=%s",
        cache_dir,
        max_pdfs,
        max_pages_per_pdf,
        max_sentences_per_page,
    )

    pdf_paths = sorted(cache_dir.glob('*.pdf'))
    if max_pdfs is not None:
        pdf_paths = pdf_paths[:max_pdfs]

    with ThreadPoolExecutor(max_workers=4) as executor:
        for processed_pdfs, (pdf_name, local_rows, local_hits, local_event_counts) in enumerate(
            executor.map(_scan_pdf, pdf_paths, repeat(source_type), repeat(max_pages_per_pdf), repeat(max_sentences_per_page)),
            start=1,
        ):
            logger.info("Scanning PDF %s (%s)", pdf_name, processed_pdfs)
            rows.extend(local_rows)
            if local_hits:
                pdf_hits[pdf_name] = local_hits
            for event_type, count in local_event_counts.items():
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + count

            if progress_interval > 0 and processed_pdfs % progress_interval == 0:
                logger.info(
                    "Progress processed_pdfs=%s pdfs_with_hits=%s total_hits=%s rows=%s",
                    processed_pdfs,
                    len(pdf_hits),
                    sum(pdf_hits.values()),
                    len(rows),
                )

    csv_path = out_dir / 'building_physics_cache_results_single_lens.csv'
    with csv_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['pdf_name', 'page', 'sentence', 'lens', 'event_type', 'outcome', 'confidence', 'context_strength', 'source_weight', 'tags', 'entities'])
        writer.writeheader()
        writer.writerows(rows)

    summary_path = out_dir / 'building_physics_single_lens_summary.json'
    summary = {
        'pdfs_scanned': processed_pdfs,
        'pdfs_with_hits': len(pdf_hits),
        'pdfs_without_hits': processed_pdfs - len(pdf_hits),
        'total_hits': sum(pdf_hits.values()),
        'event_type_counts': event_type_counts,
        'csv_path': csv_path.as_posix(),
        'top_pdfs': [[pdf_name, count] for pdf_name, count in sorted(pdf_hits.items(), key=lambda item: (-item[1], item[0]))[:10]],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    logger.info('Wrote %s', csv_path)
    logger.info('Wrote %s', summary_path)
    logger.info("building_physics: pdfs_scanned=%s, total_hits=%s", summary['pdfs_scanned'], summary['total_hits'])
    for pdf_name, count in summary['top_pdfs']:
        logger.info('  %s: %s', pdf_name, count)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache-dir', default='cache/rss')
    parser.add_argument('--out-dir', default='exports/lens_cache_exports')
    parser.add_argument('--max-pdfs', type=int, default=None)
    parser.add_argument('--source-type', default='research_paper', help='source_type passed to the building_physics detector')
    args = parser.parse_args()

    raise SystemExit(
        main(
            cache_dir=Path(args.cache_dir),
            out_dir=Path(args.out_dir),
            max_pdfs=args.max_pdfs,
            source_type=args.source_type,
        )
    )
