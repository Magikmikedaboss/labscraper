# Quick Start Guide - Peptide Research Scraper

## Installation

```bash
# Install dependencies
pip install pdfplumber tqdm

# Initialize database
python init_db.py
```

## Basic Usage

```bash
# Run scraper on default input_pdfs/ directory
python scrape_pdfs.py

# Export results to CSV
python export_csv.py
```

## Advanced Usage

```bash
# Specify research domain
python scrape_pdfs.py --domain stem_cell

# Custom input directory
python scrape_pdfs.py --input-dir my_papers/

# Custom output database
python scrape_pdfs.py --output-db results/my_data.sqlite

# Combine options
python scrape_pdfs.py --domain oncology --input-dir cancer_papers/ --output-db cancer.sqlite
```

## Output Files

### CSV Exports (in `output/`)
1. **events_export.csv** - All research events with entities and tags
2. **candidates_export.csv** - Entity-focused view (peptides, stem cells, etc.)
3. **measurements_export.csv** - Quantitative data (IC50, half-life, etc.)
4. **relationships_export.csv** - Entity comparisons

### Database
- **peptide_intel.sqlite** - Full SQLite database with all data

## Understanding Results

### Entity Types
- **peptide**: Amino acid sequences (8-100 AA)
- **stem_cell**: Stem cell markers (MSC, iPSC, etc.)

### Event Types
- **stability_issue**: Degradation, instability
- **efficacy_result**: Activity, potency data
- **toxicity_flag**: Cytotoxicity, safety concerns
- **regulatory_risk**: Compliance, safety issues
- **manufacturing_constraint**: Scale-up, yield problems
- **decision_point**: Abandoned, modified, continued

### Confidence Levels
- **high**: Strong evidence with entities and measurements
- **med**: Moderate evidence
- **low**: Weak or uncertain evidence

## Customization

### Add Known Peptides (Whitelist)
Edit `scrape_pdfs.py`:
```python
KNOWN_PEPTIDES = {
    "ETELCALCETIDE", "PLECANATIDE",
    "YOUR_PEPTIDE_HERE",  # Add your peptide
}
```

### Add False Positives (Stoplist)
Edit `scrape_pdfs.py`:
```python
FAKE_SEQUENCE_STOPLIST = {
    "MALDI", "HPLC", "PEPTIDE",
    "YOUR_FALSE_POSITIVE",  # Add false positive
}
```

### Add New Event Types
Edit `scrape_pdfs.py`:
```python
FAILURE_PHRASES = {
    "your_new_type": ["phrase1", "phrase2"],
}
```

## Troubleshooting

### No entities found
- Check that PDFs contain explicit sequence presentations
- Verify sequences are 8-100 amino acids
- Check stoplist for over-filtering

### Too many false positives
- Add false positives to `FAKE_SEQUENCE_STOPLIST`
- Verify sequence presentation patterns are working

### PDF extraction errors
- Some PDFs may have font issues (warnings are normal)
- Check `failed_pdfs` list in output
- Try re-downloading problematic PDFs

## Performance

- **Speed**: ~5-10 seconds per PDF
- **Memory**: Low (processes one PDF at a time)
- **Scalability**: Tested with 13 PDFs, scales to hundreds

## Support

See documentation files:
- `README.md` - Full documentation
- `PRODUCTION_READY.md` - Implementation details
- `FINAL_FIXES.md` - Technical fixes applied
