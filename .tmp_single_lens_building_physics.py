"""Temporary cache-scan utility for building_physics lens extraction.

Use explicit limits when running this script; it is intended for ad-hoc/local
analysis rather than unattended production jobs.
"""

from __future__ import annotations

import argparse
import csv
import logging
import json
import os
from pathlib import Path

import pdfplumber

from lenses.construction_building_physics_v1 import detect
from utils.text_utils import chunk_sentences

logger = logging.getLogger(__name__)


def _env_limit(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    trimmed_value = value.strip()
    try:
        return int(trimmed_value)
    except ValueError as exc:
        raise ValueError(f"Environment variable '{name}' has non-integer value: '{trimmed_value}'") from exc


def _configure_logging(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    log_path = out_dir / "building_physics_cache_results.log"

    has_file_handler = any(
        isinstance(handler, logging.FileHandler)
        and Path(getattr(handler, "baseFilename", "")).resolve() == log_path.resolve()
        for handler in logger.handlers
    )
    if not has_file_handler:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    has_stream_handler = any(type(handler) is logging.StreamHandler for handler in logger.handlers)
    if not has_stream_handler:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)


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

    _configure_logging(out_dir)

    rows = []
    pdf_hits = {}
    sentence_hits = 0
    processed_pdfs = 0

    logger.info(
        "Starting building_physics cache scan cache_dir=%s max_pdfs=%s max_pages_per_pdf=%s max_sentences_per_page=%s",
        cache_dir,
        max_pdfs,
        max_pages_per_pdf,
        max_sentences_per_page,
    )

    for pdf_path in sorted(cache_dir.glob('*.pdf')):
        if max_pdfs is not None and processed_pdfs >= max_pdfs:
            break
        processed_pdfs += 1
        logger.info("Scanning PDF %s (%s)", pdf_path.name, processed_pdfs)
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
                        pdf_hits[pdf_path.name] = pdf_hits.get(pdf_path.name, 0) + 1
                        sentence_hits += 1
                        rows.append({
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
                "SKIP %s after pdf_hits=%s sentence_hits=%s",
                pdf_path.name,
                pdf_hits.get(pdf_path.name, 0),
                sentence_hits,
            )

        if progress_interval > 0 and processed_pdfs % progress_interval == 0:
            logger.info(
                "Progress processed_pdfs=%s pdf_hits=%s sentence_hits=%s rows=%s",
                processed_pdfs,
                len(pdf_hits),
                sentence_hits,
                len(rows),
            )

    csv_path = out_dir / 'building_physics_cache_results_single_lens.csv'
    with csv_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['pdf_name', 'page', 'sentence', 'lens', 'event_type', 'outcome', 'confidence', 'context_strength', 'source_weight', 'tags', 'entities'])
        writer.writeheader()
        writer.writerows(rows)

    summary_path = out_dir / 'building_physics_single_lens_summary.json'
    summary = {
        'lens': 'building_physics',
        'pdf_hits': len(pdf_hits),
        'sentence_hits': sentence_hits,
        'csv_path': csv_path.as_posix(),
        'top_pdfs': sorted(pdf_hits.items(), key=lambda item: (-item[1], item[0]))[:10],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    logger.info('Wrote %s', csv_path)
    logger.info('Wrote %s', summary_path)
    logger.info("building_physics: pdf_hits=%s, sentence_hits=%s", summary['pdf_hits'], summary['sentence_hits'])
    for pdf_name, count in summary['top_pdfs']:
        logger.info('  %s: %s', pdf_name, count)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-type', default='research_paper', help='source_type passed to the building_physics detector')
    args = parser.parse_args()

    raise SystemExit(main(source_type=args.source_type))
