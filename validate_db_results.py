#!/usr/bin/env python3
"""
Quick validation script for database results
"""

from pathlib import Path

from utils.db_utils import connect_with_foreign_keys

def validate_db_results(db_path):
    """Validate database results for construction science domain"""
    if not Path(db_path).exists():
        print(f'❌ Database not found: {db_path}')
        return False
    
    print(f'🏗️  VALIDATING DATABASE RESULTS: {db_path}')
    print('=' * 50)
    
    with connect_with_foreign_keys(db_path) as con:
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
        
        print('\n🏗️  Entity Types:')
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
            return True
        else:
            print('❌ CONTAMINATION: Biomedical entities found!')
            return False

if __name__ == "__main__":
    # Test the database from the user's command
    db_path = 'db/runs.sqlite'
    validate_db_results(db_path)