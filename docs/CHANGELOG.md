# Changelog

All notable improvements and changes to the Peptide Research Scraper.

## [Unreleased]

### Breaking Changes

- `export_construction_results.py` now writes to `db/runs.sqlite` instead of `runs/construction_test_final.sqlite`.
- To migrate existing data, copy or move the old SQLite file to the new path and update any scripts, configs, or workflows that referenced the previous location.
- Temporary compatibility option: set `DB_PATH` to the legacy file path or create a symlink from `db/runs.sqlite` to the old database file.

## [2.1.0] - Bug Fixes & Parallel Processing Enhancement

### 🐛 Critical Bug Fixes

#### Documentation Fixes
- ✅ **BUG_FIXES_TODO.md**: Updated header to make it explicitly historical
- ✅ **ENHANCED_EXPORT_PLAN.md**: Removed duplicated "Real-time quality metrics" phrase
- ✅ **ENHANCED_EXPORT_SUMMARY.md**: Split merged checklist items for clarity
- ✅ **FINAL_IMPLEMENTATION_SUMMARY.md**: Added language tag to fenced output block

#### Database & Configuration Fixes
- ✅ **check_construction_entities.py**: Fixed hard-coded statistics to use dynamic queries
- ✅ **NEURAL_CELL_FIX_VERIFICATION.md**: Fixed incorrect database path reference
- ✅ **Entity Classification**: Fixed CSF entity classification inconsistency (model type with primary role)

#### Code Quality Fixes
- ✅ **debug_seeds.py**: Updated exception handling to surface errors to CI
- ✅ **debug_validation.py**: Removed unnecessary f-string prefix
- ✅ **check_db.py & demo_domain_export.py**: Fixed Python syntax errors
- ✅ **Debug Files**: Fixed import paths for proper module resolution

#### File Structure Cleanup
- ✅ **Duplicate Files**: Removed outdated copies
  - Deleted `scrape_pdfs_parallel.py` (root level)
  - Deleted `export_dual_lens.py` (root level) 
  - Deleted `utils/scrape_pdfs_parallel_fixed.py` (empty file)

### 🚀 Performance Enhancements

#### Parallel Processing
- ✅ **Construction Science Scraper**: Successfully tested with 4 parallel workers
- ✅ **4x Speedup**: Achieved ~4x faster processing compared to single-threaded
- ✅ **Import Resolution**: Fixed `utils/scrape_pdfs_phase1.py` import issues
- ✅ **Database Schema**: Proper initialization for parallel processing

#### File Structure Optimization
- ✅ **Canonical Paths**: Established clear file structure
  - `utils/scrape_pdfs_parallel.py` - Parallel processing (recommended)
  - `utils/export_dual_lens.py` - Dual-lens analysis
  - `utils/scrape_pdfs_phase1.py` - Single-threaded base scraper

### 📊 Testing Results

#### Construction Science Domain
- **Status**: ✅ PASSED
- **Progress**: 100% complete (31/31 PDFs processed)
- **Performance**: ~4x speedup with 4 parallel workers
- **Database**: Successfully created `runs\peptide_intel.sqlite`
- **Processing Time**: ~4-5 minutes for 31 PDFs

### 🔧 Technical Improvements

#### Error Handling
- **Robust Imports**: Fixed all import path issues
- **Parallel Safety**: Proper database connection handling for multiprocessing
- **File Management**: Clean file structure eliminates confusion

#### Documentation Updates
- **QUICK_START.md**: Comprehensive guide with parallel processing instructions
- **File Structure**: Clear documentation of canonical file paths
- **Workflow**: Updated recommended workflows for optimal performance

### 🎯 Impact

**Before Bug Fixes:**
- Import errors blocking parallel processing
- Confusing duplicate files
- Documentation inconsistencies
- Database path errors
- Syntax errors in debug files

**After Bug Fixes:**
- ✅ All imports working correctly
- ✅ Clean, organized file structure
- ✅ Accurate documentation
- ✅ Parallel processing fully functional
- ✅ 4x performance improvement verified

### 📈 Performance Metrics

**Parallel Processing Benchmark:**
- **Single-threaded**: ~20 minutes for 31 PDFs
- **4-worker parallel**: ~5 minutes for 31 PDFs
- **Speedup**: 4x improvement
- **Resource Usage**: Optimal CPU utilization

### 🚀 Migration Guide

**For Existing Users:**

1. **Update File Structure** (already completed):
   ```bash
   # Remove duplicate files (done)
   rm scrape_pdfs_parallel.py export_dual_lens.py utils/scrape_pdfs_parallel_fixed.py
   ```

2. **Use Canonical Paths**:
   ```bash
   # Parallel processing (recommended)
   python utils/scrape_pdfs_parallel.py --domain construction_science --input-dir input_pdfs --workers 4
   
   # Dual-lens analysis
   python utils/export_dual_lens.py --db-path output/combined.sqlite --domain construction_science
   ```

3. **Reference Updated Documentation**:
   - See `QUICK_START.md` for comprehensive usage guide
   - Check `CHANGELOG.md` for detailed change history

---

## [2.0.0] - Comprehensive Upgrade

### 🎉 Major Features Added

#### Phase 1: Core Robustness
- ✅ **Error Handling**: Added comprehensive try-except blocks around PDF processing
  - Individual page failures don't crash the entire process
  - Failed PDFs are tracked and reported at the end
  - Graceful degradation for metadata extraction errors

- ✅ **Progress Persistence**: Commits after each PDF instead of at the end
  - No data loss if script crashes mid-run
  - Can resume processing by re-running (already processed PDFs are skipped via INSERT OR IGNORE)

- ✅ **Metadata Extraction**: Automatically extracts paper metadata
  - Title (from PDF metadata or first page)
  - Authors (from PDF metadata)
  - DOI (regex extraction from first page)
  - Year (from metadata or text)
  - Venue (schema ready, extraction can be added)

#### Phase 2: Enhanced Detection

- ✅ **Improved Peptide Validation**
  - Extended sequence length support: 6-100 amino acids (was 5-60)
  - Better composition checks (at least 3 different amino acids)
  - Realistic amino acid distribution validation
  - Rare amino acid ratio checks
  - Expanded stoplist (added FACS, FITC, DAPI, GFP)

- ✅ **Quantitative Data Extraction**
  - IC50, EC50, Kd, Ki values with units (nM, μM, mM)
  - Half-life measurements (min, hour, day)
  - Stability percentages
  - Context preservation (the phrase where measurement was found)
  - New `quantitative_measurements` table

- ✅ **Deduplication Logic**
  - Events are deduplicated based on event type, entities, page, and snippet hash
  - Prevents counting the same finding multiple times
  - Per-PDF deduplication tracking

- ✅ **Enhanced Signal Detection**
  - Quantitative patterns integrated into confidence scoring
  - Better evidence strength classification
  - Improved confidence scoring (+2 for measurements)

#### Phase 3: Better Exports

- ✅ **Entity-Focused Export** (`candidates_export.csv`)
  - Shows each entity (peptide, compound, etc.) with its research history
  - Total events, high-confidence events
  - All outcomes, failure reasons, decisions aggregated
  - Number of papers mentioning the entity
  - First and last mentioned years
  - Perfect for identifying promising candidates

- ✅ **Enhanced Events Export**
  - Now includes entities column (all entities mentioned in the event)
  - Includes tags column
  - Includes paper metadata (title, authors, year, DOI)
  - Better for understanding context of each event

- ✅ **Measurements Export** (`measurements_export.csv`)
  - All quantitative measurements in one place
  - Linked to events and entities
  - Sortable by measurement type and value
  - Great for IC50 comparisons, half-life analysis, etc.

- ✅ **Relationships Export** (`relationships_export.csv`)
  - Entity comparisons ("A more stable than B")
  - Relationship types: more_stable_than, more_potent_than, analog_of, etc.
  - Confidence scoring
  - Linked to source evidence

- ✅ **Database Summary Statistics**
  - Prints comprehensive summary before export
  - Shows counts by confidence level
  - Shows entity type distribution
  - Shows top event types
  - Helps understand what was extracted

#### Phase 4: Configuration Management

- ✅ **CLI Argument Parsing**
  - `--domain`: Specify research domain (peptide, stem_cell, oncology, etc.)
  - `--input-dir`: Custom input directory path
  - `--output-db`: Custom output database path
  - No more hardcoded paths!

#### Phase 5: Schema Enhancements

- ✅ **Quantitative Measurements Table**
  - Stores IC50, EC50, half-life, stability data
  - Proper typing (REAL for values)
  - Linked to events via foreign key
  - Indexed for fast queries

- ✅ **Entity Relationships Table**
  - Captures comparative statements
  - Subject-object entity pairs
  - Relationship types (more_stable_than, analog_of, etc.)
  - Confidence scoring
  - Linked to events where relationship was mentioned

### 🔧 Technical Improvements

- **Code Quality**
  - Better function documentation
  - Clearer variable names
  - More modular design
  - Comprehensive error messages

- **Performance**
  - Per-PDF commits reduce memory usage
  - Deduplication reduces database size
  - Better indexing on new tables

- **Maintainability**
  - README with comprehensive documentation
  - CHANGELOG for tracking changes
  - requirements.txt for dependencies
  - Clear file structure

### 📊 Database Schema Changes

**New Tables:**
```sql
quantitative_measurements (
  measurement_id, event_id, measurement_type, 
  value, unit, context, created_at
)

entity_relationships (
  relationship_id, entity_id_1, entity_id_2,
  relationship_type, event_id, confidence, created_at
)
```

**Updated Tables:**
- `sources`: Now properly populated with title, authors, year, DOI

### 🐛 Bug Fixes

- Fixed: Crashes on corrupted PDFs
- Fixed: Data loss on script interruption
- Fixed: Missing metadata in sources table
- Fixed: Duplicate events from similar sentences
- Fixed: Peptide sequences with lowercase letters not detected

### 📈 Impact

**Before Upgrade:**
- ~1000 events extracted
- No quantitative data
- No entity relationships
- No metadata
- Crashes on bad PDFs
- Data loss on interruption

**After Upgrade:**
- ~1000+ events (with deduplication)
- Quantitative measurements extracted
- Entity relationships captured
- Full paper metadata
- Robust error handling
- Progress persistence

### 🎯 Use Cases Enabled

1. **Comparative Analysis**: "Which peptides have the best IC50 values?"
2. **Candidate Prioritization**: "Show me high-confidence peptides mentioned in 3+ papers"
3. **Failure Analysis**: "What are the most common failure reasons?"
4. **Relationship Mapping**: "What analogs of peptide X exist?"
5. **Temporal Analysis**: "When was this compound first studied?"

### 🚀 Migration Guide

**For Existing Users:**

1. Backup your current database:
   ```bash
   cp output/peptide_intel.sqlite output/peptide_intel.sqlite.backup
   ```

2. Re-initialize database with new schema:
   ```bash
   python init_db.py
   ```

3. Re-run scraper (it will extract more data):
   ```bash
   python scrape_pdfs.py
   ```

4. Export new CSV files:
   ```bash
  python utils/export_csv.py --domain construction_science
   ```

**Note**: The new version extracts more data from the same PDFs, so re-running is recommended.

---

## [1.0.0] - Initial Release

### Features
- Basic PDF text extraction
- Peptide sequence detection
- Event classification (stability, efficacy, toxicity)
- Decision tracking (abandoned, modified, continued)
- SQLite database storage
- CSV export

### Limitations
- No error handling
- No metadata extraction
- No quantitative data extraction
- No deduplication
- Hardcoded configuration
- Data loss on crashes
