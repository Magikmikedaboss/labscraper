# Folder Organization Plan

## Current Issues
- Root `input/` folder contains 100+ biomedical PDFs that should be in domain-specific folders
- `input_pdfs_test/` folder contains contaminated PDFs
- Missing proper `methods_tooling/` folder structure
- RSS feeds configuration is empty

## Proper Structure

```text
input/
├── pdfs/
│   ├── construction_science/     # ✅ Clean construction PDFs (27 files)
│   ├── biohacking_longevity/     # ✅ Clean biohacking PDFs (31 files)
│   ├── neuroscience_cognition/   # ✅ Clean neuroscience PDFs (100+ files)
│   ├── stem_cells_regen/         # ✅ Clean stem cell PDFs (100+ files)
│   ├── methods_tooling/          # ❌ Missing - should contain methods/tooling PDFs
│   └── input_pdfs_test/          # ❌ Contaminated - needs cleanup
├── rss_cache/                    # ✅ For RSS downloads
└── [root PDFs]                   # ❌ Should be moved to appropriate folders
```

## What Needs to be Done

### 1. Move Root PDFs to Appropriate Folders
The 100+ PDFs in `input/` root should be categorized:
- **Stem cell/Regenerative medicine PDFs** → `input/pdfs/stem_cells_regen/`
- **Methods/Tooling PDFs** → `input/pdfs/methods_tooling/`
- **Biomedical PDFs** → `input/pdfs/biohacking_longevity/`

### 2. Clean Up Test Folder
- Remove contaminated PDFs from `input/pdfs/input_pdfs_test/`
- Keep only legitimate test PDFs

### 3. Create Methods & Tooling Folder
- Move methodological PDFs to `input/pdfs/methods_tooling/`
- These are PDFs about research methods, assays, protocols

### 4. RSS Configuration
- Populate `config/feeds.json` with RSS feeds for each domain
- Set up automated RSS ingestion

## Domain-Specific Processing

Each domain folder should be processed with its corresponding domain parameter:

```bash
# Construction science
python utils/run_engine.py --domain construction_science --input-dir input/pdfs/construction_science

# Biohacking longevity  
python utils/run_engine.py --domain biohacking_longevity --input-dir input/pdfs/biohacking_longevity

# Neuroscience cognition
python utils/run_engine.py --domain neuroscience_cognition --input-dir input/pdfs/neuroscience_cognition

# Stem cells & regeneration
python utils/run_engine.py --domain stem_cells_regen --input-dir input/pdfs/stem_cells_regen

# Methods & tooling
python utils/run_engine.py --domain methods_tooling --input-dir input/pdfs/methods_tooling
```

## Next Steps
1. Categorize and move PDFs from root `input/` folder
2. Clean up `input_pdfs_test/` folder
3. Create proper `methods_tooling/` folder
4. Update RSS feeds configuration
5. Test domain-specific processing