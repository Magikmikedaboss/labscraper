from __future__ import annotations

import csv
import json
from pathlib import Path

import pdfplumber

from lenses.construction_building_physics_v1 import detect
from utils.text_utils import chunk_sentences

cache_dir = Path('cache/rss')
out_dir = Path('exports/lens_cache_exports')
out_dir.mkdir(parents=True, exist_ok=True)

rows = []
pdf_hits = {}
sentence_hits = 0

for pdf_path in sorted(cache_dir.glob('*.pdf')):
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ''
                if not text.strip():
                    continue
                for sentence in chunk_sentences(text):
                    event, entities = detect(sentence, source_type='research_paper')
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
    except Exception as exc:
        print(f'SKIP {pdf_path.name}: {type(exc).__name__}: {exc}')

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
    'csv_path': str(csv_path).replace('\\', '/'),
    'top_pdfs': sorted(pdf_hits.items(), key=lambda item: (-item[1], item[0]))[:10],
}
summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(f'Wrote {csv_path}')
print(f'Wrote {summary_path}')
print(f"building_physics: pdf_hits={summary['pdf_hits']}, sentence_hits={summary['sentence_hits']}")
for pdf_name, count in summary['top_pdfs']:
    print(f'  {pdf_name}: {count}')
