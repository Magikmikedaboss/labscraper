# Reorganization Plan for Axon-Engine Structure

## Step 1: Create New Directories
- Create config/dual_lens/
- Create seeds/base/
- Create seeds/domain/
- Rename input_pdfs/ to input/
- Create input/pdfs/ and move subdirs from input/ to input/pdfs/
- Create input/rss_cache/
- Rename output/ to runs/
- Create runs/biohacking_longevity/run_2026-01-25_1015/outputs/
- Create runs/neuroscience_cognition/run_2026-01-25_1201/outputs/
- Create runs/stem_cells_regen/
- Create exports/
- Create exports/latest/biohacking_longevity/
- Create exports/latest/neuroscience_cognition/
- Create exports/snapshots/2026-01/
- Create db/
- Create logs/
- Create utils/

## Step 2: Move Files
- Move seeds/ txt/json files to seeds/base/ (rename .json to .txt if needed)
- Create seeds/domain/ txt files (empty)
- Move runs/ (old output/) files to appropriate subdirs and exports/
- Move .py files to utils/
- Rename scrape_pdfs.py to run_engine.py in utils/
- Create run_rss_ingest.py (empty)
- Create config/feeds.json (empty)
- Create db/ sqlite files (placeholders)
- Create logs/ files (empty)

## Step 3: Update Script References
- Search and replace path references in .py files (e.g., 'input_pdfs' -> 'input/pdfs', 'output' -> 'runs')

## Step 4: Verify Structure
- List directories to confirm layout matches target
