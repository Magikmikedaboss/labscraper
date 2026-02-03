#!/usr/bin/env python3
"""
Check the exported construction science files
"""

import pandas as pd
import os
from pathlib import Path

def check_exported_files():
    print('📁 CHECKING EXPORTED FILES')
    print('=' * 40)
    
    # Make paths relative to script location for resilience to working-directory changes
    script_dir = Path(__file__).parent
    output_dir = script_dir / "output"
    
    # Check if files exist
    files_to_check = [
        output_dir / 'construction_entities.csv',
        output_dir / 'construction_events.csv',
        output_dir / 'construction_event_entities.csv'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                print(f'✅ {file_path}: {len(df)} rows')
                if 'entity_type' in df.columns:
                    print(f'   Entity types: {df["entity_type"].unique()}')
                elif 'event_type' in df.columns:
                    print(f'   Event types: {df["event_type"].unique()}')
            except pd.errors.ParserError as e:
                print(f'❌ {file_path}: CSV parsing error - {e}')
            except pd.errors.EmptyDataError as e:
                print(f'❌ {file_path}: Empty CSV file - {e}')
            except Exception as e:
                # Avoid blind Exception catch - re-raise after logging
                print(f'❌ {file_path}: Unexpected error - {e}')
                raise
        else:
            print(f'❌ {file_path}: Not found')

if __name__ == "__main__":
    check_exported_files()
