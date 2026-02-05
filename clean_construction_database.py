#!/usr/bin/env python3
"""
Clean the construction database to remove biomedical contamination
"""

import sqlite3
from pathlib import Path

def clean_construction_database():
    """Remove biomedical entities from construction database"""
    # Make path relative to script location for resilience to working-directory changes
    script_dir = Path(__file__).parent
    db_path = script_dir / "db/runs.sqlite"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print("🧹 CLEANING CONSTRUCTION DATABASE")
    print("=" * 50)
    print("Removing biomedical contamination...")
    
    # Biomedical entity types that shouldn't be in construction database
    biomedical_entity_types = [
        'peptide', 'compound', 'target', 'model', 'stem_cell', 
        'neural_cell', 'cell_line', 'organism'
    ]
    
    # Construction entity types that should be kept (unused variable - kept for future validation)
    # construction_entity_types = [
    #     'material', 'environment', 'process', 'structure', 
    #     'component', 'system', 'property'
    # ]
    
    try:
        conn = None
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get current entity counts
        print("\n📊 BEFORE CLEANING:")
        cursor.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type')
        before_stats = cursor.fetchall()
        for entity_type, count in before_stats:
            print(f"   {entity_type}: {count}")
        
        # Get construction events
        cursor.execute('SELECT COUNT(*) FROM research_events WHERE research_domain = "construction"')
        construction_events = cursor.fetchone()[0]
        print(f"   Construction events: {construction_events}")
        
        # Find biomedical entities in construction events
        cursor.execute('''
            SELECT DISTINCT e.entity_id, e.entity_name, e.entity_type
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            JOIN research_events re ON ee.event_id = re.event_id
            WHERE re.research_domain = "construction" 
            AND e.entity_type IN ({})

        '''.format(','.join(['?'] * len(biomedical_entity_types))), biomedical_entity_types)
        
        biomedical_entities = cursor.fetchall()
        print(f"\n❌ Found {len(biomedical_entities)} biomedical entities in construction events:")
        for _, entity_name, entity_type in biomedical_entities:
            print(f"   - {entity_name} ({entity_type})")
        
        # Initialize counters to prevent NameError if no biomedical entities found
        removed_relationships = 0
        removed_entities = 0
        
        if biomedical_entities:
            # Remove event-entity relationships for biomedical entities in construction events
            # Fix SQLite parameter limit by processing in chunks of 900
            print("\n🧹 Removing biomedical entity relationships...")
            entity_ids = [e[0] for e in biomedical_entities]
            chunk_size = 900
            
            for i in range(0, len(entity_ids), chunk_size):
                chunk = entity_ids[i:i + chunk_size]
                placeholders = ','.join(['?'] * len(chunk))
                
                # Delete relationships for this chunk
                cursor.execute(f'''
                    DELETE FROM event_entities 
                    WHERE entity_id IN ({placeholders})
                    AND event_id IN (SELECT event_id FROM research_events WHERE research_domain = "construction")
                ''', chunk)
                
                removed_relationships += cursor.rowcount
            
            print(f"   Removed {removed_relationships} event-entity relationships")
            
            # Remove biomedical entities that are no longer referenced
            # Use the same chunking approach
            print("\n🗑️  Removing orphaned biomedical entities...")
            
            for i in range(0, len(entity_ids), chunk_size):
                chunk = entity_ids[i:i + chunk_size]
                placeholders = ','.join(['?'] * len(chunk))
                
                # Delete entities for this chunk
                cursor.execute(f'''
                    DELETE FROM entities 
                    WHERE entity_id IN ({placeholders})
                    AND entity_id NOT IN (SELECT DISTINCT entity_id FROM event_entities)
                ''', chunk)
                
                removed_entities += cursor.rowcount
            
            print(f"   Removed {removed_entities} orphaned entities")
        
        # Verify cleaning
        print("\n📊 AFTER CLEANING:")
        cursor.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type')
        after_stats = cursor.fetchall()
        for entity_type, count in after_stats:
            print(f"   {entity_type}: {count}")
        
        # Check for remaining biomedical contamination
        cursor.execute('''
            SELECT COUNT(*) FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            JOIN research_events re ON ee.event_id = re.event_id
            WHERE re.research_domain = "construction" 
            AND e.entity_type IN ({})

        '''.format(','.join(['?'] * len(biomedical_entity_types))), biomedical_entity_types)
        
        remaining_contamination = cursor.fetchone()[0]
        
        if remaining_contamination == 0:
            print("\n✅ SUCCESS: No biomedical contamination found in construction events!")
        else:
            print(f"\n⚠️  WARNING: {remaining_contamination} biomedical entities still found")
        
        # Summary
        print("\n📋 CLEANING SUMMARY:")
        print(f"   Construction events: {construction_events}")
        print(f"   Biomedical entities detected: {len(biomedical_entities)}")
        print(f"   Relationships removed: {removed_relationships}")
        print(f"   Entities removed: {removed_entities}")
        
        conn.commit()
        print("\n✅ Database cleaning complete!")
        
    except Exception as e:
        print(f"❌ Error during cleaning: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    clean_construction_database()