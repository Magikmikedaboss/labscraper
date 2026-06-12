# Export Configuration Reference

This guide covers export commands, database expectations, and the current canonical ingest-to-export flow.

If you only need file names and output locations, read [EXPORT_FILES_GUIDE.md](EXPORT_FILES_GUIDE.md).

## Purpose

Use this guide for:

- export command behavior
- database source expectations
- domain constraints
- common failure modes

## Current Flow

The current canonical flow is:

```bash
python run_rss_ingest.py --feeds config/feeds.json --db db/runs.sqlite
python utils/export_csv.py --domain construction_science
python utils/export/export_dual_lens.py db/runs.sqlite construction_science
```

In other words:

1. Ingest with `run_rss_ingest.py`
2. Store results in `db/runs.sqlite`
3. Export with `utils/export_csv.py` or `utils/export/export_dual_lens.py`

## Primary Commands

### 1) Domain-aware entities export

```bash
python utils/export_csv.py --domain construction_science
```

Behavior:

- requires `--domain`
- reads from `db/runs.sqlite`
- writes `exports/latest/<domain>/entities.csv`

### 2) Dual-lens export

```bash
python utils/export/export_dual_lens.py db/runs.sqlite construction_science
```

Behavior:

- reads from the database path you pass in
- uses domain overlays from config
- writes dual-lens CSV and report files under `exports/`

## Domain Configuration

Available domain configs live in `config/domains/*.json`.

Current domains:

- `biohacking_longevity`
- `construction_science`
- `drug_discovery`
- `methods_tooling`
- `neuroscience_cognition`
- `stem_cells_regen`

This list matches the valid domain IDs used by `utils/export/export_dual_lens.py`.

Notes:

- `utils/export_csv.py` requires `--domain`
- run the export once per domain when publishing multiple domains

## Data Source Rules

### `utils/export_csv.py`

- fixed DB source: `db/runs.sqlite`
- best for the standard export flow

### `utils/export/export_dual_lens.py`

- DB path is an argument
- use this when your data is in a non-default DB

### `export_construction_results.py`

- legacy/manual export script
- writes to `output/`
- prefer the `utils/export_csv.py` and `utils/export/export_dual_lens.py` paths for current work

Example with a custom DB:

```bash
python utils/export/export_dual_lens.py db/local.sqlite construction_science
```

## Troubleshooting

### Export is empty

Confirm ingestion wrote events for that domain:

```bash
python -c "import sqlite3; c=sqlite3.connect('db/runs.sqlite'); cur=c.cursor(); print(cur.execute('select research_domain,count(*) from research_events group by research_domain').fetchall())"
```

### Wrong database used

- `utils/export_csv.py` always reads `db/runs.sqlite`
- use `utils/export/export_dual_lens.py` for custom DBs

### Invalid domain error

- use one of the domain IDs listed in `config/domains/`

### Dual-lens warning about overlay mode

- ensure the selected domain has dual-lens overlay configuration

## Related Docs

- [EXPORT_FILES_GUIDE.md](EXPORT_FILES_GUIDE.md) - primary output map
- [QUICK_START.md](QUICK_START.md) - minimal command flow
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - validation and regression workflow
