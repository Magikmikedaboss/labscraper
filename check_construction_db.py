#!/usr/bin/env python3
"""
Simple script to check the construction science database contents
"""

import sqlite3
from pathlib import Path

def main():
    # Check the actual construction science test database
    db_path = Path('runs/construction_science_test.sqlite')
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print(f'📊 Checking {db_path}:')
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Check entity types
        entity_counts = cur.execute('''
            SELECT entity_type, COUNT(*) as count
            FROM entities 
            GROUP BY entity_type 
            ORDER BY count DESC
        ''').fetchall()
        
        print('🏗️ Top Entity Types:')
        for row in entity_counts[:10]:
            print(f'   {row["entity_type"]}: {row["count"]}')
        
        # Check events
        event_count = cur.execute('SELECT COUNT(*) as total FROM research_events').fetchone()
        print(f'\n📈 Total Events: {event_count["total"]}')
        
        # Check top entities
        top_entities = cur.execute('''
            SELECT e.entity_name, e.entity_type, COUNT(ee.event_id) as event_count
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            GROUP BY e.entity_id
            ORDER BY event_count DESC
            LIMIT 10
        ''').fetchall()
        
        print('\n🏆 Top 10 Entities by Event Count:')
        for i, row in enumerate(top_entities, 1):
            print(f'   {i}. {row["entity_name"]} ({row["entity_type"]}): {row["event_count"]} events')

if __name__ == "__main__":
    main()