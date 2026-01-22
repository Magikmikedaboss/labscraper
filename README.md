# 🧬 Lab Scraper - Peptide Research Intelligence Engine

A production-ready Python engine that extracts structured research intelligence from scientific PDFs, with a focus on peptide degradation and stability research.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 What It Does

Transforms unstructured scientific PDFs into structured, queryable research intelligence:

**Input:** PDF research papers  
**Output:** Structured database + CSV exports with:
- Research events (stability issues, decision points, outcomes)
- Entities (compounds, targets, assays, pathways, models, indications)
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

### 📁 Export Formats
- **SQLite database** for complex queries
- **4 CSV files** for different use cases:
  - `candidates_primary.csv` - For rankings/dashboards (114 entities)
  - `candidates_context.csv` - For filters only (11 entities)
  - `candidates_export_v3.csv` - Complete data (125 entities)
  - `events_export_v3.csv` - All events with normalized entities (647 events)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Magikmikedaboss/labscraper.git
cd labscraper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py
```

### Usage

```bash
# Run the scraper on PDFs in input_pdfs/
python scrape_pdfs_phase1.py

# Export to CSV
python export_csv_v3.py

# View results
ls output/
# → candidates_primary.csv, events_export_v3.csv, peptide_intel.sqlite
```

---

## 📂 Project Structure

```
labscraper/
├── scrape_pdfs_phase1.py      # Main scraper (production)
├── entity_extractor.py         # Entity extraction logic
├── entity_normalizer.py        # Variant normalization
├── export_csv_v3.py            # CSV export with normalization
├── init_db.py                  # Database initialization
├── schema.sql                  # Database schema
├── requirements.txt            # Python dependencies
│
├── seeds/                      # Entity seed files
│   ├── assays.json            # 129 assay/method terms
│   ├── targets.txt            # 153 biological targets
│   ├── pathways.json          # 124 pathway terms
│   ├── compounds.txt          # 75 compound names
│   ├── models.txt             # 136 model systems
│   ├── indications.json       # 88 disease indications
│   ├── normalization.json     # Variant mapping rules
│   └── README.md              # Seed file documentation
│
├── input_pdfs/                 # Place PDFs here
│   └── *.pdf                  # Research papers to process
│
├── output/                     # Generated data
│   ├── peptide_intel.sqlite   # Main database
│   ├── candidates_primary.csv # Primary entities (for rankings)
│   ├── candidates_context.csv # Context entities (for filters)
│   ├── candidates_export_v3.csv # All entities
│   ├── events_export_v3.csv   # All events
│   └── README.md              # Output documentation
│
└── docs/                       # Documentation
    ├── NORMALIZATION_SUCCESS.md
    ├── CRASH_RECOVERY_SUMMARY.md
    └── COVERAGE_IMPROVEMENT.md
```

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
