# 🧬 Peptide Intelligence Scraper - Research Intelligence Engine

A production-ready Python engine that extracts structured research intelligence from scientific PDFs across multiple research domains, with advanced parallel processing and dual-lens analysis capabilities.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Parallel Processing](https://img.shields.io/badge/Parallel-4x%20Speedup-green.svg)](https://github.com/Magikmikedaboss/labscraper)

---

## 🎯 What It Does

Transforms unstructured scientific PDFs into structured, queryable research intelligence:

**Input:** PDF research papers  
**Output:** Structured database + CSV exports with:
- Research events (stability issues, decision points, outcomes, regulatory risks)
- Entities (compounds, targets, assays, pathways, models, indications, stem cells)
- Quantitative measurements (IC50, EC50, half-life, stability)
- Entity relationships (comparisons, analogs, derivatives)
- Normalized, deduplicated, and ranked data

---

## ✨ Key Features

### 🔍 Entity Extraction
- **7 entity types:** Compounds, Targets, Assays, Pathways, Models, Indications, Stem Cells
- **625+ seed terms** across all categories
- **Word boundary detection** prevents false positives
- **Case-insensitive matching** handles variant spellings

### 🧹 Entity Normalization
- **Variant consolidation:** LC-MS ← [LC-MS, LC-MS/MS, mass spectrometry, QTOF, triple quadrupole]
- **Context demotion:** Generic terms (HUMAN, SERUM) separated from research entities
- **Clean rankings:** Top entities are meaningful research items, not experimental conditions

### 📊 Data Quality
- **0% false positives** (ambiguous abbreviations removed)
- **41.4% entity coverage** (268/647 events have entities)
- **43.6% medium confidence** events (high-quality extractions)
- **137 unique entities** extracted and normalized to 125 canonical forms

```bash
# Clone the repository
git clone https://github.com/Magikmikedaboss/labscraper.git
cd labscraper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (development)
pip install -r requirements.txt

# For reproducible installs (production/CI):
pip install -r requirements-lock.txt

# To update the lock file after editing requirements.txt:
pip install -r requirements.txt
pip freeze > requirements-lock.txt
```

## 📦 Dependency Management

- **requirements.txt**: List direct dependencies with loose version constraints. Edit this file to add or update packages.
- **requirements-lock.txt**: Fully pinned, auto-generated manifest for reproducible installs. Always use this file for CI, production, or sharing exact environments.
- **How to update**: After editing requirements.txt, run:
  ```bash
  pip install -r requirements.txt
  pip freeze > requirements-lock.txt
  ```
  Commit both files if dependencies change.

## Initialize database

```bash
python init_db.py
```

## Usage

### Modular Pipeline (Development/Debug)

The modular pipeline is orchestrated by `utils/scrape_pdfs_phase1_full.py`. This script demonstrates the core PDF-to-database logic using only the new modular utility functions, and is ideal for debugging, development, or as a template for further customization.

```bash
# Run the modular pipeline (default input and db paths):
python utils/scrape_pdfs_phase1_full.py

# Specify custom input and database paths:
python utils/scrape_pdfs_phase1_full.py --input-dir input/pdfs --db-path db/dev.sqlite
```

- All logic is delegated to modular utilities in `utils/`.
- Use this script to test new entity extractors, event logic, or database schema changes.
- Output: Populates the specified SQLite database with parsed research events, entities, and measurements.

#### Basic Processing
```bash
# Single-threaded processing

The modular pipeline is orchestrated by `utils/scrape_pdfs_phase1_full.py`. This script demonstrates the core PDF-to-database logic using only the new modular utility functions, and is ideal for debugging, development, or as a template for further customization.

```bash
# Run the modular pipeline (default input and db paths):
python utils/scrape_pdfs_phase1_full.py

# Specify custom input and database paths:
python utils/scrape_pdfs_phase1_full.py --input-dir input/pdfs --db-path db/dev.sqlite
```

- All logic is delegated to modular utilities in `utils/`.
- Use this script to test new entity extractors, event logic, or database schema changes.
- Output: Populates the specified SQLite database with parsed research events, entities, and measurements.

#### Basic Processing
```bash
# Single-threaded processing
python utils/run_engine.py --domain construction_science --input-dir input/pdfs

# Export results
python utils/export_csv_v5_domain_aware.py --db-path db/runs.sqlite --domain construction_science
```

#### Parallel Processing (Recommended for large datasets)
```bash
# 4 parallel workers (recommended)
python utils/scrape_pdfs_parallel.py --domain construction_science --input-dir input/pdfs --workers 4

# 8 parallel workers (for powerful systems)
python utils/scrape_pdfs_parallel.py --domain construction_science --input-dir input/pdfs --workers 8
```

#### Advanced Analysis
```bash
# Dual-lens analysis (advanced export)
python utils/export_dual_lens.py --db-path db/runs.sqlite --domain construction_science
```

#### View Results
```bash
ls exports/
# → candidates_export.csv, events_export.csv, measurements_export.csv, relationships_export.csv
ls db/
# → runs.sqlite (main database)
```

---

## 📂 Project Structure

```
labscraper/
├── utils/                      # Core processing modules
│   ├── scrape_pdfs_parallel.py     # Parallel PDF processing (recommended)
│   ├── run_engine.py               # Single-threaded processing
│   ├── export_dual_lens.py         # Advanced dual-lens analysis
│   ├── export_csv_v5_domain_aware.py # Domain-aware CSV export
│   ├── scrape_pdfs_phase1_full.py  # Modular pipeline (development/debug)
│   ├── entities.py                 # Entity extraction utilities
│   ├── event_classification.py     # Event classification logic
│   ├── db_utils.py                 # Database helpers
│   ├── text_utils.py               # Text processing utilities
│   ├── data_extractors.py          # Quantitative data extraction
│   ├── metadata_utils.py           # PDF metadata extraction
│   ├── common.py                   # Common helpers (hashing, etc.)
│   ├── entity_extractor.py         # (legacy) Entity extraction logic
│   ├── entity_normalizer.py        # (legacy) Variant normalization
│   ├── init_db.py                  # Database initialization (run root init_db.py to create db/runs.sqlite)
│   └── scrape_pdfs_phase1.py       # Base scraper functions
├── schema.sql                  # Database schema
├── config/                     # Configuration files
│   ├── domains/               # Domain-specific configurations
│   ├── lenses/                # Overlay configurations
│   └── feeds.json             # RSS feed configurations
├── seeds/                      # Entity seed files
│   ├── compounds.txt          # 75 compound names
│   ├── targets.txt            # 153 biological targets
│   ├── models.txt             # 136 model systems
│   ├── assays.json            # 129 assay/method terms
│   ├── pathways.json          # 124 pathway terms
│   ├── indications.json       # 88 disease indications
│   ├── normalization.json     # Variant mapping rules
│   └── README.md              # Seed file documentation
├── input/                      # Input directories
│   ├── pdfs/                  # Default PDF input
│   └── pdfs/{domain}/         # Domain-specific PDF input
├── db/                        # Database files
│   ├── runs.sqlite           # Main processing database
│   └── all_pdfs.sqlite       # Combined database
├── exports/                   # Exported data
│   ├── candidates_export.csv # Entity-focused export
│   ├── events_export.csv     # Event export with metadata
│   ├── measurements_export.csv # Quantitative measurements
│   ├── relationships_export.csv # Entity relationships
│   └── latest/               # Latest export with metadata
├── logs/                      # Processing logs
├── output/                    # Legacy output directory
└── requirements.txt           # Python dependencies
```

## 🛠️ Development & Debugging

- To test or extend the modular pipeline, use `utils/scrape_pdfs_phase1_full.py`.
- All core logic is now modularized in `utils/` for easy reuse and testing.
- For production/parallel runs, use `utils/run_engine.py` or `utils/scrape_pdfs_parallel.py`.

---

## 📊 Data Schema

### Research Events
```sql
research_events (
    event_id TEXT PRIMARY KEY,
    research_domain TEXT,      -- e.g., "peptide"
    event_type TEXT,           -- stability_issue, decision_point, outcome
    study_stage TEXT,          -- in_vitro, in_vivo, clinical
    outcome TEXT,              -- positive, negative, neutral
    decision_driver TEXT,      -- what drove the decision
    evidence_snippet TEXT,     -- supporting text
    confidence TEXT,           -- high, med, low
    source_id TEXT,            -- PDF filename
    created_at TEXT
)
```

### Entities
```sql
entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT,          -- compound, target, assay, pathway, model, indication
    entity_name TEXT,          -- canonical name
    entity_variant TEXT,       -- subtype (e.g., "protein", "cell_line")
    created_at TEXT
)
```

### Event-Entity Links
```sql
event_entities (
    event_id TEXT,
    entity_id TEXT,
    role TEXT,                 -- primary, context
    PRIMARY KEY (event_id, entity_id)
)
```

---

## 🎨 Integration with Next.js

### Option 1: CSV Files (Quickest)
```typescript
// app/api/entities/route.ts
import { readFileSync } from 'fs';
import { parse } from 'csv-parse/sync';

export async function GET() {
  const csv = readFileSync('public/data/candidates_primary.csv', 'utf-8');
  const entities = parse(csv, { columns: true });
  return Response.json(entities);
}
```

### Option 2: Flask API Wrapper (Production)
See `docs/INTEGRATION_GUIDE.md` for complete API setup.

---

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| **PDFs Processed** | 19 papers |
| **Events Extracted** | 647 |
| **Unique Entities** | 137 (125 after normalization) |
| **Entity Coverage** | 41.4% (268/647 events) |
| **False Positive Rate** | 0% |
| **Top Entity** | LC-MS (85 events, 6 variants consolidated) |
| **Confidence Distribution** | 43.6% med, 50.5% low, 5.9% high |

---

## 🛠️ Maintenance

### Adding New Seed Terms
```bash
# Edit seed files
nano seeds/assays.json

# Validate (prevents crashes from ambiguous abbreviations)
python lint_seeds.py

# Re-run scraper
python scrape_pdfs_phase1.py
```

### Adding Normalization Rules
```json
// seeds/normalization.json
{
  "assay": {
    "HPLC": ["hplc", "liquid chromatography", "rp-hplc", "uplc"]
  }
}
```

---

## 📚 Documentation

- **[Normalization System](docs/NORMALIZATION_SUCCESS.md)** - How variant consolidation works
- **[Crash Recovery](docs/CRASH_RECOVERY_SUMMARY.md)** - Debugging guide
- **[Coverage Improvement](docs/COVERAGE_IMPROVEMENT.md)** - Seed expansion details
- **[Seed Files](seeds/README.md)** - Entity seed documentation
- **[Output Files](output/README.md)** - Export file usage guide

---

## 🧪 Testing

```bash
# Test entity extraction
python test_phase1_results.py

# Test normalization
python -c "from entity_normalizer import *; test_normalization()"

# Validate seed files
python lint_seeds.py
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built for peptide degradation research intelligence
- Seed files curated from scientific literature
- Normalization rules based on common variant patterns

---

## 📧 Contact

**Project Link:** [https://github.com/Magikmikedaboss/labscraper](https://github.com/Magikmikedaboss/labscraper)

---

## 🎯 Roadmap

- [ ] Add more entity types (cell lines, organisms)
- [ ] Implement confidence calibration
- [ ] Add multi-domain support (beyond peptides)
- [ ] Build REST API wrapper
- [ ] Create web dashboard
- [ ] Add PDF upload interface

---

**Status:** ✅ Production Ready

Last Updated: 2026-01-22
