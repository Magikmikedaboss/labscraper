# AXON Testing Guide

This guide describes the current testing workflow for AXON as a multi-domain research intelligence engine.

## Scope

This guide covers:
1. Database initialization and schema checks
2. PDF ingestion testing
3. RSS discovery testing
4. Entity extraction validation
5. Event extraction validation
6. Export validation
7. Multi-domain testing
8. Source provenance testing

## Prerequisites

- Run commands from repository root: C:\projects\labscraper
- Activate your virtual environment
- Install dependencies:

```bash
pip install -r requirements.txt
```

## 1. Database Initialization

Use a local test database for explicit schema-init tests:

```bash
python utils/init_db.py db/local.sqlite
```

Important:
- The explicit init script is guarded against direct initialization of db/runs.sqlite.
- Production-style runs usually initialize schema through pipeline scripts.

Verify expected tables exist:

```bash
python -c "import sqlite3; con=sqlite3.connect('db/local.sqlite'); cur=con.cursor(); print([r[0] for r in cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()])"
```

## 2. PDF Ingestion Testing

Single-domain ingestion:

```bash
python utils/run_engine.py --domain construction_science --input-dir input/pdfs/construction_science --output-db db/local.sqlite
```

Parallel ingestion:

```bash
python utils/scrape_pdfs_parallel.py --domain construction_science --input-dir input/pdfs/construction_science --output-db db/local.sqlite --workers 4
```

Validation checks:
- Command exits without traceback
- Events are inserted into research_events
- Entities are inserted and linked via event_entities

Quick DB sanity:

```bash
python -c "import sqlite3; con=sqlite3.connect('db/local.sqlite'); cur=con.cursor(); print('events', cur.execute('select count(*) from research_events').fetchone()[0]); print('entities', cur.execute('select count(*) from entities').fetchone()[0])"
```

## 3. RSS Discovery Testing

Probe feed health:

```bash
python tools/test_feeds.py --config config/feeds.json --save-working
```

Dry-run ingest (discovery only, no writes):

```bash
python run_rss_ingest.py --dry-run
```

Full ingest to RSS database:

```bash
python run_rss_ingest.py
```

Validation checks:
- Feed links are discovered
- PDF links are resolved when available
- Dry-run does not commit extracted records

## 4. Entity Extraction Validation

Run ingestion, then inspect entity distribution:

```bash
python utils/check_entity_types.py
```

What to validate:
- Entity types align with selected domain
- High-noise tokens are not dominating
- Canonical names and variants are reasonable

Do not rely on fixed counts. Counts vary with corpus, seeds, and extraction logic.

## 5. Event Extraction Validation

After ingestion, validate event quality:

```bash
python validate_db_results.py
```

What to validate:
- event_type is populated for extracted events
- confidence distribution is plausible
- evidence snippets are non-empty and traceable

Optional quick query:

```bash
python -c "import sqlite3; con=sqlite3.connect('db/local.sqlite'); cur=con.cursor(); print(cur.execute(\"select event_type, count(*) from research_events group by event_type order by 2 desc\").fetchmany(10))"
```

## 6. Export Validation

Domain-aware export:

```bash
python utils/export_csv.py --domain construction_science
```

Dual-lens export:

```bash
python utils/export/export_dual_lens.py db/local.sqlite construction_science
```

Validate output files:

```bash
python utils/check_output_files.py
```

Expected locations:
- exports/latest/<domain>/entities.csv
- exports/entities_dual_lens_<domain>.csv
- exports/events_dual_lens_<domain>.csv
- exports/dual_lens_report_<domain>.txt

## 7. Multi-Domain Testing

Run at least two domains to confirm separation:

```bash
python utils/run_engine.py --domain construction_science --input-dir input/pdfs/construction_science --output-db db/local.sqlite
python utils/run_engine.py --domain neuroscience_cognition --input-dir input/pdfs/neuroscience_cognition --output-db db/local.sqlite
```

Validate:
- research_domain values are present and correct
- exports generated per requested domain
- no single-domain assumptions in outputs

## 8. Source Provenance Testing

AXON schema includes provenance tables:
- sources
- documents
- chunks

Validate linkage integrity:

```bash
python -c "import sqlite3; con=sqlite3.connect('db/local.sqlite'); cur=con.cursor(); print('sources', cur.execute('select count(*) from sources').fetchone()[0]); print('documents', cur.execute('select count(*) from documents').fetchone()[0]); print('chunks', cur.execute('select count(*) from chunks').fetchone()[0]); print('events_with_source', cur.execute('select count(*) from research_events where source_id is not null').fetchone()[0])"
```

## Recommended Regression Set

Run before merges:

```bash
python -m ruff check .
python -m pytest -q
python tools/test_feeds.py --config config/feeds.json
python run_rss_ingest.py --dry-run
```

## Troubleshooting

No PDFs found:
- Verify input path exists and contains .pdf files
- Verify selected domain folder matches command path

Schema/init errors:
- Use db/local.sqlite for explicit init tests
- Recreate test DB and rerun ingestion

Export looks empty:
- Confirm ingestion inserted events for target domain
- Confirm export command domain matches ingested domain

RSS finds few PDFs:
- This is normal for some feeds
- RSS is discovery-first; PDF availability depends on source pages

## Legacy Guide

The prior seed-system-focused guide has been preserved at:
- LEGACY_SEED_SYSTEM_TESTING.md
