# Seed Files - Entity Extraction

This directory contains seed lists for entity extraction. These files make the system domain-agnostic and easy to extend without editing Python code.

## 📁 Files

### `compounds.txt`
List of therapeutic compounds, drugs, and small molecules.
- **Format**: One compound per line, case-insensitive
- **Examples**: liraglutide, metformin, rapamycin
- **Current count**: ~50 compounds

### `targets.txt`
List of biological targets (genes, proteins, receptors).
- **Format**: One target per line, case-insensitive
- **Examples**: MTOR, GLP1R, AMPK
- **Current count**: ~70 targets

### `models.txt`
List of experimental models (organisms, cell lines, biofluids, tissues).
- **Format**: One model per line, case-insensitive
- **Examples**: mouse, HEK293, serum, organoid
- **Current count**: ~100 models

### `stopwords.txt`
List of terms to EXCLUDE from entity extraction.
- **Format**: One term per line, case-insensitive
- **Examples**: PEPTIDE, CLINICAL, SYNTHESIS
- **Current count**: ~120 stopwords

## 🔧 How to Use

### Adding New Entities

1. Open the appropriate seed file
2. Add one entity per line
3. Re-run the scraper: `python scrape_pdfs.py`
4. No code changes needed!

### Example: Adding a New Compound

```bash
# Edit seeds/compounds.txt
echo "ozempic" >> seeds/compounds.txt

# Re-run scraper
python scrape_pdfs.py

# Export results
python export_csv.py
```

### Domain-Specific Profiles (Future)

You can create domain-specific seed packs:

```
seeds/domains/
  peptide/
    compounds.txt    # Peptide-specific compounds
    targets.txt      # Peptide-specific targets
    models.txt       # Peptide-specific models
  stem_cell/
    compounds.txt    # Stem cell compounds
    targets.txt      # Stem cell markers
    models.txt       # Stem cell models
  oncology/
    compounds.txt    # Cancer drugs
    targets.txt      # Oncogenes
    models.txt       # Cancer cell lines
```

Then run with domain flag:
```bash
python scrape_pdfs.py --domain peptide
python scrape_pdfs.py --domain stem_cell
```

## 📝 Format Rules

### All Files
- One entity per line
- Case-insensitive (will match "MTOR", "mTOR", "mtor")
- Lines starting with `#` are comments
- Empty lines are ignored
- Whitespace is trimmed

### Compounds
- Drug names (generic or brand)
- Small molecules
- Peptide therapeutics
- Antibodies (common ones)

### Targets
- Gene symbols (MTOR, AMPK)
- Protein names (NF-κB, TNF-α)
- Receptor names (GLP1R, EGFR)
- Use standard nomenclature

### Models
- Organisms (mouse, rat, human)
- Cell lines (HEK293, HeLa)
- Biofluids (serum, plasma)
- Tissues (liver, brain)
- 3D models (organoid, spheroid)

### Stopwords
- English words that look like sequences
- Generic lab terms
- Document structure words
- Statistical terms

## 🎯 Best Practices

### 1. Start Small
- Begin with 30-50 entities per category
- Add more as you discover them in your PDFs

### 2. Use Standard Names
- Compounds: Use generic names (metformin, not Glucophage)
- Targets: Use gene symbols (MTOR, not mammalian target of rapamycin)
- Models: Use common abbreviations (HEK293, not Human Embryonic Kidney 293)

### 3. Add Variants
If a term has multiple spellings, add all:
```
GLP1R
GLP-1R
GLP 1R
```

### 4. Review Extractions
After running the scraper:
```bash
python check_entity_types.py
```

If you see false positives, add them to `stopwords.txt`.
If you see missed entities, add them to the appropriate seed file.

## 🔄 Maintenance

### Weekly
- Review `candidates_export.csv` for new entities
- Add legitimate entities to seed files
- Add false positives to stopwords

### Monthly
- Review entity counts by type
- Balance seed lists (don't let one category dominate)
- Update domain profiles if using multiple domains

## 📊 Current Coverage

Based on the peptide dataset (13 PDFs):

| Category  | Seed Count | Extracted | Coverage |
|-----------|------------|-----------|----------|
| Compounds | ~50        | 5         | 10%      |
| Targets   | ~70        | 0         | 0%       |
| Models    | ~100       | 4         | 4%       |
| Peptides  | N/A        | 3         | N/A      |
| Stem Cells| N/A        | 4         | N/A      |

**Note**: Low extraction counts are expected - these PDFs focus on peptide stability, not protein targets or diverse compounds.

## 🚀 Future Enhancements

1. **Synonym Mapping**: Map variants to canonical names
   - rapamycin → sirolimus
   - GLP-1R → GLP1R

2. **Hierarchies**: Group related entities
   - GLP-1 agonists: liraglutide, semaglutide, dulaglutide
   - mTOR inhibitors: rapamycin, everolimus, temsirolimus

3. **Confidence Scores**: Weight entities by source quality
   - DrugBank compounds: high confidence
   - User-added compounds: medium confidence

4. **Auto-Discovery**: Suggest new entities from extractions
   - "Found 'tirzepatide' 5 times - add to compounds.txt?"

## 📚 Resources

- **DrugBank**: https://go.drugbank.com/ (compound names)
- **HUGO Gene Nomenclature**: https://www.genenames.org/ (gene symbols)
- **Cellosaurus**: https://www.cellosaurus.org/ (cell line names)
- **NCBI Taxonomy**: https://www.ncbi.nlm.nih.gov/taxonomy (organism names)

## ❓ FAQ

**Q: Why are seed files better than hardcoded lists?**
A: You can update entities without touching Python code. Non-programmers can maintain the lists.

**Q: How do I know if my seeds are working?**
A: Run `python check_entity_types.py` and review the entity counts.

**Q: Can I use this for other research domains?**
A: Yes! Just update the seed files with domain-specific terms.

**Q: What if I want domain-specific extraction?**
A: Create `seeds/domains/[domain]/` folders and use `--domain` flag.

**Q: How do I handle synonyms?**
A: Add all variants to the seed file. Future versions will support synonym mapping.

---

**Last Updated**: 2024
**Maintainer**: Research Intelligence Team
