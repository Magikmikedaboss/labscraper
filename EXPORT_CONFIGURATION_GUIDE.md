# Export Configuration Reference

This is the advanced export configuration reference.

Use this guide when you need command behavior details, domain constraints, or troubleshooting.

If you only need output file names and paths, read:
- [EXPORT_FILES_GUIDE.md](EXPORT_FILES_GUIDE.md)

## Purpose

This guide explains:
- Which export commands to run
- Domain requirements
- Data source behavior
- Common failure modes and fixes

## Primary Commands

### 1) Domain-aware entities export

```bash
python utils/export_csv.py --domain construction_science
```

Behavior:
- Requires `--domain`
- Reads from `db/runs.sqlite`
- Writes `exports/latest/<domain>/entities.csv`

### 2) Dual-lens export

```bash
python utils/export/export_dual_lens.py db/runs.sqlite construction_science
```

Behavior:
- Reads from the DB path you pass in
- Uses domain overlays from config
- Writes dual-lens CSV/report files under `exports/`

## Domain Configuration

Available domain configs are in:
- `config/domains/*.json`

Current domains:
- `biohacking_longevity`
- `construction_science`
- `drug_discovery`
- `methods_tooling`
- `neuroscience_cognition`
- `stem_cells_regen`

This list matches `VALID_DOMAIN_IDS` in `utils/export/export_dual_lens.py`.

Notes:
- `utils/export_csv.py` requires `--domain`
- Execute once per domain when publishing multiple domains
## Data Source Rules

### `utils/export_csv.py`
- Fixed DB source: `db/runs.sqlite`
- Best for standard, canonical export flow

### `utils/export/export_dual_lens.py`
- DB path is an argument
- Use this when your data is in a non-default DB

Example with custom DB:

```bash
python utils/export/export_dual_lens.py db/local.sqlite construction_science
```

## Typical Ingest + Export Flow

```bash
# Ingest
python utils/run_engine.py --domain construction_science --input-dir input/pdfs/construction_science --output-db db/runs.sqlite

# Standard entities export
python utils/export_csv.py --domain construction_science

# Dual-lens export
python utils/export/export_dual_lens.py db/runs.sqlite construction_science
```

## Troubleshooting

### Export is empty
- Confirm ingestion wrote events for that domain:

```bash
python -c "import sqlite3; c=sqlite3.connect('db/runs.sqlite'); cur=c.cursor(); print(cur.execute('select research_domain,count(*) from research_events group by research_domain').fetchall())"
```

### Wrong database used
- `export_csv.py` always reads `db/runs.sqlite`
- Use `export_dual_lens.py` for custom DBs

### Invalid domain error
- Use one of the domain IDs listed in `config/domains/`

### Dual-lens warning about overlay mode
- Ensure the selected domain has dual-lens overlay configuration

## Related Docs

- [EXPORT_FILES_GUIDE.md](EXPORT_FILES_GUIDE.md) (primary output map)
- [QUICK_START.md](QUICK_START.md) (minimal command flow)
- [TESTING_GUIDE.md](TESTING_GUIDE.md) (validation and regression workflow)
