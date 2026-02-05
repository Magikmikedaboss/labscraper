#!/usr/bin/env python3
"""
Display sample events from construction science export
"""

import csv
from pathlib import Path

def show_sample_events():
    """Display first 5 events from the export"""
    events_file = Path('output/events_export_construction_science.csv')
    
    if not events_file.exists():
        print("❌ Events file not found")
        return
    
    print('🏗️  SAMPLE EVENTS (First 5):')
    print('=' * 80)
    
    with open(events_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 5:
                break
            print(f'Event {i+1}: {row["event_id"]}')
            print(f'  Domain: {row["domain"]}')
            print(f'  Type: {row["event_type"]}')
            print(f'  Stage: {row["stage"]}')
            print(f'  Confidence: {row["confidence"]}')
            print(f'  Outcome: {row["outcome"][:100]}...')
            print(f'  Entities: {row["entities"]}')
            print(f'  Source: {row["source_id"]}')
            print('-' * 40)

if __name__ == "__main__":
    show_sample_events()