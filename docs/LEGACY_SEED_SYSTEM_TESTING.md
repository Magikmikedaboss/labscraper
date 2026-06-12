# Legacy Testing Guide - Seed File System

This document describes the legacy seed system. For the current seed system, use the active seed files under `seeds/base/life_sciences/`.

##  Simple Step-by-Step Instructions

###  Step 1: Check Your Current Setup

First, let's see what you have:

```powershell
# Open PowerShell in your project folder
# You should be in: <project-root>

# Check if seed files exist
Get-ChildItem seeds/base/life_sciences/

# You should see:
# - compounds.txt
# - targets.txt
# - models.txt
# - assays.txt
# - indications.json
# - stopwords.txt
```

Legacy root seed files have been removed from active use. Edit all seed files under `seeds/base/life_sciences/`.

---

###  Step 2: Clean Start (Recommended for Testing)

**Why?** Starting fresh ensures you see the new seed system working without old data interfering.

```powershell
# Delete the old database (don't worry, we'll recreate it)
Remove-Item db/runs.sqlite -ErrorAction SilentlyContinue

# Delete old CSV exports
Remove-Item output/*.csv -ErrorAction SilentlyContinue

# Recreate the database with fresh schema
python utils/init_db.py db/runs.sqlite --force
```

**Expected Output:**
```
 Database initialized: db/runs.sqlite
   Created 10 tables
```

---

###  Step 3: Test Seed File Loading

Run the scraper to see if seed files load:

```powershell
python utils/run_engine.py --domain methods_tooling --input-dir input/pdfs/methods_tooling
```

**Expected Output (First Few Lines):**
```
 Loaded seeds:
   Compounds: 50
   Targets: 70
   Models: 100
   Stopwords: 120

PDFs: 100%|| 13/13 [01:00<00:00,  4.62s/it]

 Done!
   Inserted: ~442 research events
   Measurements: 0
   Relationships: 0
   DB: <project-root>\db\runs.sqlite
```

** Success Indicators:**
- You see " Loaded seeds:" with counts
- No errors about missing seed files
- Scraper processes all 13 PDFs
- Creates events in database

** If You See Errors:**
- "Seed file not found"  Check that `seeds/` folder exists
- "No PDFs found"  Check that `input/pdfs/methods_tooling/` has PDF files
- Python errors  Make sure you're in the right directory

---

###  Step 4: Export and Check Results

```powershell
# Export data to CSV files
python utils/export_csv.py --domain methods_tooling
```

**Expected Output:**
```
Exported 16 entities to output/candidates_export.csv
Exported 442 events to output/events_export.csv
Exported 0 measurements to output/measurements_export.csv
Exported 0 relationships to output/relationships_export.csv

Database Summary:
==================
Sources: 13
Events: 442
Entities: 16
Event-Entity Links: 71
Tags: 6
```

---

###  Step 5: Verify Entity Extraction

Check what entities were extracted:

```powershell
# Quick check of entities
python utils/check_entity_types.py
```

**Expected Output:**
```
Total entities: 16

Compounds: 5
- LIRAGLUTIDE (6 events)
- SEMAGLUTIDE (2 events)
- ETELCALCETIDE (1 events)
- LINACLOTIDE (1 events)
- PLECANATIDE (1 events)

Models: 4
- SERUM (18 events)
- HUMAN (16 events)
- PLASMA (4 events)
- MICE (1 events)

Peptides: 3
Methods: 4
```

** Success Indicators:**
- You see compounds from `seeds/base/life_sciences/compounds.txt` (liraglutide, semaglutide, etc.)
- You see models from `seeds/base/life_sciences/models.txt` (serum, human, plasma, mice)
- Total entities: ~16 (may vary slightly)

---

###  Step 6: Test Adding a New Entity

Let's test that you can add entities without editing Python code:

```powershell
# Add a new compound to the seed file
Add-Content -Path seeds/base/life_sciences/compounds.txt -Value "ozempic"

# Re-run scraper (it will load the new seed)
python utils/run_engine.py --domain methods_tooling --input-dir input/pdfs/methods_tooling

# Export again
python utils/export_csv.py --domain methods_tooling

# Check if "ozempic" was extracted
python utils/check_entity_types.py
```

**Expected Result:**
- If "ozempic" appears in any of your PDFs, it will now be extracted
- If not in PDFs, it won't appear (which is correct!)

---

##  Troubleshooting

### Problem: "Seed file not found"

**Solution:**
```powershell
# Check if seeds folder exists
Get-ChildItem seeds/base/life_sciences/

# If missing, create it:
New-Item -ItemType Directory -Path seeds/base/life_sciences -Force

# Then create the seed files (see seeds/base/life_sciences/*.txt in this repo for canonical contents)
```

### Problem: "No PDFs found"

**Solution:**
```powershell
# Check if input_pdfs folder has PDFs
Get-ChildItem input/pdfs/methods_tooling/

# Should show 13 PDF files
# If empty, add your PDF files to this folder
```

### Problem: "Module not found" errors

**Solution:**
```powershell
# Install required packages
pip install -r requirements.txt
```

### Problem: Database is locked

**Solution:**
```powershell
# Close any programs that might be using the database
# Then delete and recreate:
Remove-Item db/runs.sqlite -Force
python utils/init_db.py db/runs.sqlite --force
python utils/run_engine.py --domain methods_tooling --input-dir input/pdfs/methods_tooling
```

---

##  What to Look For (Success Checklist)

###  Seed Loading
- [ ] Scraper shows " Loaded seeds:" with counts
- [ ] Compounds: ~50
- [ ] Targets: ~70
- [ ] Models: ~100
- [ ] Stopwords: ~120

###  Entity Extraction
- [ ] Compounds extracted (5 expected: liraglutide, semaglutide, etc.)
- [ ] Models extracted (4 expected: Serum, Human, Plasma, Mice)
- [ ] Peptides extracted (3 expected)
- [ ] Stem cells extracted (4 expected)
- [ ] Total entities: ~16

###  CSV Exports
- [ ] `candidates_export.csv` created (16 entities)
- [ ] `events_export.csv` created (442 events)
- [ ] Files can be opened in Excel
- [ ] Entity names match seed file contents

###  Seed File Modifications
- [ ] Can add new entities to seed files
- [ ] Re-running scraper picks up new entities
- [ ] No Python code editing required

---

##  Quick Test Commands (Copy-Paste)

### Full Clean Test
```powershell
# Clean everything
Remove-Item db/runs.sqlite -ErrorAction SilentlyContinue
Remove-Item output/*.csv -ErrorAction SilentlyContinue

# Rebuild
python utils/init_db.py db/runs.sqlite --force
python utils/run_engine.py --domain methods_tooling --input-dir input/pdfs/methods_tooling
python utils/export_csv.py --domain methods_tooling
python utils/check_entity_types.py
```

### Quick Re-run (Keep Database)
```powershell
# Just re-run scraper and export
python utils/run_engine.py --domain methods_tooling --input-dir input/pdfs/methods_tooling
python utils/export_csv.py --domain methods_tooling
python utils/check_entity_types.py
```

### View Results in Excel
```powershell
# Open CSV files
Start-Process output/candidates_export.csv
Start-Process output/events_export.csv
```

---

##  Next Steps After Testing

Once testing is successful:

1. **Review Results**
   - Open `candidates_export.csv` in Excel
   - Check if entities look correct
   - Look for any false positives

2. **Add Domain-Specific Entities**
   - Edit `seeds/base/life_sciences/compounds.txt` to add compounds relevant to your research
   - Edit `seeds/base/life_sciences/targets.txt` to add targets you care about
   - Edit `seeds/base/life_sciences/models.txt` to add experimental models you use

3. **Remove False Positives**
   - If you see incorrect entities, add them to `seeds/base/life_sciences/stopwords.txt`
   - Re-run scraper

4. **Use the Data**
   - Import CSVs into Excel for analysis
   - Use database for queries
   - Build a website (Next.js + TypeScript + Tailwind)

---

##  FAQ

**Q: Do I need to delete the database every time?**
A: No! Only delete it when:
- Testing major changes
- You want a completely fresh start
- Database seems corrupted

For normal use, just run `python utils/run_engine.py --domain methods_tooling --input-dir input/pdfs/methods_tooling` and it will update the existing database.

**Q: What if I don't see any compounds extracted?**
A: This is normal if your PDFs don't mention the compounds in `seeds/base/life_sciences/compounds.txt`. The seed system only extracts entities that:
1. Are in the seed file
2. Actually appear in your PDFs

**Q: Can I have multiple seed files for different projects?**
A: Yes. Run separate commands per domain, for example:

The examples below intentionally switch domains to show separate projects, and each command is labeled by domain.

```powershell
# construction_science example
python utils/run_engine.py --domain construction_science --input-dir input/pdfs/construction_science
# neuroscience_cognition example
python utils/run_engine.py --domain neuroscience_cognition --input-dir input/pdfs/neuroscience_cognition
```

**Q: How do I know if seed files are being used vs hardcoded lists?**
A: Look for " Loaded seeds:" in the output. If you see this, seed files are being used!

---

##  Need Help?

If you run into issues:

1. Check the error message carefully
2. Look at the "Troubleshooting" section above
3. Make sure you're in the right directory: `<project-root>`
4. Check that all files exist:
   - `seeds/base/life_sciences/compounds.txt`
   - `seeds/base/life_sciences/targets.txt`
   - `seeds/base/life_sciences/models.txt`
   - `seeds/base/life_sciences/stopwords.txt`
   - `input/pdfs/methods_tooling/*.pdf` (13 PDFs)

---

**Happy Testing! **

Remember: The seed file system is designed to be simple. If something seems complicated, it probably shouldn't be - let me know and we can simplify it!


