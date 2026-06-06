# Export Files Guide

## Overview

This guide describes the files produced by the current export pipeline and where they are written.

Use this as the primary export guide.

## Data Source

Export files are generated from records already stored in SQLite (typically `db/runs.sqlite`).
The normal chain is: PDF processing -> SQLite records -> CSV/TXT exports.

## Typical Workflow

1. Process PDFs
2. Store extracted events/entities in SQLite
3. Run export command(s)
4. Review generated files in `exports/`
5. Load files into spreadsheets, dashboards, or analytics tools

For advanced command behavior and domain configuration, see:
- [EXPORT_CONFIGURATION_GUIDE.md](EXPORT_CONFIGURATION_GUIDE.md)

## Export Commands

### Domain-aware entities export
```bash
python utils/export_csv.py --domain construction_science
```

Writes:
- `exports/latest/<domain>/entities.csv`

### Dual-lens export
```bash
python utils/export/export_dual_lens.py db/runs.sqlite construction_science
```

Dual-lens exports apply overlay configuration(s) to score entities and events from different research perspectives.

Writes:
- `exports/entities_dual_lens_<domain>.csv`
- `exports/events_dual_lens_<domain>.csv`
- `exports/dual_lens_report_<domain>.txt`
- `exports/latest/<domain>/entities_dual_lens.csv`
- `exports/latest/<domain>/events_dual_lens.csv`

## Example

Command:

```bash
python utils/export_csv.py --domain construction_science
```

Output:

```text
exports/
`-- latest/
    `-- construction_science/
        `-- entities.csv
```

## File Details

### `exports/latest/<domain>/entities.csv`
- Produced by `utils/export_csv.py`
- One row per canonical entity for the selected domain
- Core columns: `entity_name`, `entity_type`, `entity_variant`, `event_count`

### `exports/entities_dual_lens_<domain>.csv`
- Produced by `utils/export/export_dual_lens.py`
- Entity-level dual-lens scoring output
- Includes per-overlay score and bucket columns

### `exports/events_dual_lens_<domain>.csv`
- Produced by `utils/export/export_dual_lens.py`
- Event-level output with overlay scores
- Core columns: `event_id`, `event_type`, `stage`, `confidence_original`, `evidence_snippet`

### `exports/dual_lens_report_<domain>.txt`
- Human-readable summary report
- Includes top-ranked entities and bucket distribution by overlay

## Validation Checklist

1. Confirm files exist under `exports/` and `exports/latest/<domain>/`
2. Confirm each file is non-empty
3. Confirm domain naming is correct in output filenames
4. Spot-check key columns for expected values

## Notes

- Export outputs are domain-scoped; run per domain as needed.
- Legacy files in `output/` may still exist from older workflows, but current exporters write to `exports/`.

## Related Docs

- [QUICK_START.md](QUICK_START.md)
- [EXPORT_CONFIGURATION_GUIDE.md](EXPORT_CONFIGURATION_GUIDE.md)
- [TESTING_GUIDE.md](TESTING_GUIDE.md)
