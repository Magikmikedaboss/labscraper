#!/usr/bin/env python3
"""
Test the new construction science database to verify results
"""

import sqlite3
from pathlib import Path

def test_new_database():
    db_path = Path('runs/construction_science_final.sqlite')
    if not db_path.exists():
        print('❌ New database not found')
        return
    
    print('🏗️  TESTING NEW CONSTRUCTION SCIENCE DATABASE')
    print('=' * 60)
    
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Check events
        event_count = cur.execute('SELECT COUNT(*) FROM research_events').fetchone()[0]
        print(f'📈 Total Events: {event_count}')
        
        # Check entity types
        entity_types = cur.execute('''
            SELECT entity_type, COUNT(*) as count
            FROM entities 
            GROUP BY entity_type 
            ORDER BY count DESC
        ''').fetchall()
        
        print(f'\n🏗️  Entity Types:')
        for row in entity_types:
            print(f'   {row["entity_type"]}: {row["count"]}')
        
        # Check top entities
        top_entities = cur.execute('''
            SELECT e.entity_name, e.entity_type, COUNT(ee.event_id) as event_count
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            GROUP BY e.entity_id
            ORDER BY event_count DESC
            LIMIT 10
        ''').fetchall()
        
        print(f'\n🏆 Top 10 Entities:')
        for i, row in enumerate(top_entities, 1):
            print(f'   {i}. {row["entity_name"]} ({row["entity_type"]}): {row["event_count"]} events')
        
        # Check for biomedical contamination
        biomedical_types = {'peptide', 'compound', 'target', 'model', 'stem_cell', 'neural_cell'}
        bio_count = cur.execute('''
            SELECT COUNT(*) FROM entities 
            WHERE entity_type IN ({})
        '''.format(','.join(['?']*len(biomedical_types))), list(biomedical_types)).fetchone()[0]
        
        print(f'\n🔍 Biomedical Contamination: {bio_count} entities')
        
        if bio_count == 0:
            print('✅ CLEAN: No biomedical contamination detected!')
        else:
            print('❌ CONTAMINATION: Biomedical entities found!')

if __name__ == "__main__":
    test_new_database()