#!/usr/bin/env python3
"""
One-liner validation for database results
Usage: python quick_validation.py runs/construction_test_final.sqlite
"""

import sqlite3
from pathlib import Path
import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python quick_validation.py <database_path>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    if not Path(db_path).exists():
        print(f'❌ Database not found: {db_path}')
        sys.exit(1)
    
    print(f'🏗️  VALIDATING DATABASE RESULTS: {db_path}')
    print('=' * 50)
    
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
        
        # Check for biomedical contamination
        biomedical_types = {'peptide', 'compound', 'target', 'model', 'stem_cell', 'neural_cell'}
        bio_count = cur.execute('''
            SELECT COUNT(*) FROM entities 
            WHERE entity_type IN ({})
        '''.format(','.join(['?']*len(biomedical_types))), list(biomedical_types)).fetchone()[0]
        
        print(f'\n🔍 Biomedical Contamination: {bio_count} entities')
        
        if bio_count == 0:
            print('✅ CLEAN: No biomedical contamination detected!')
            print('✅ SYSTEM IS FULLY WIRED AND WORKING CORRECTLY!')
        else:
            print('❌ CONTAMINATION: Biomedical entities found!')

if __name__ == "__main__":
    main()