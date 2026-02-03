#!/usr/bin/env python3
"""
Check the exported construction science files
"""

import pandas as pd
import os

def check_exported_files():
    print('📁 CHECKING EXPORTED FILES')
    print('=' * 40)
    
    # Check if files exist
    files_to_check = [
        'output/construction_entities.csv',
        'output/construction_events.csv',
        'output/construction_event_entities.csv'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f'✅ {file_path}: {len(df)} rows')
            if 'entity_type' in df.columns:
                print(f'   Entity types: {df["entity_type"].unique()}')
            elif 'event_type' in df.columns:
                print(f'   Event types: {df["event_type"].unique()}')
        else:
            print(f'❌ {file_path}: Not found')

if __name__ == "__main__":
    check_exported_files()