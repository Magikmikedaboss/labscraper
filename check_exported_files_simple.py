#!/usr/bin/env python3
"""
Check the exported construction science files (simple version)
"""

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
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f'✅ {file_path}: {len(lines)} lines')
                
                # Show first few lines to verify content
                if len(lines) > 0:
                    print(f'   Header: {lines[0].strip()}')
                    if len(lines) > 1:
                        print(f'   Sample: {lines[1].strip()}')
        else:
            print(f'❌ {file_path}: Not found')

if __name__ == "__main__":
    check_exported_files()