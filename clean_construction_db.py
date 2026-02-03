#!/usr/bin/env python3
"""
Clean contaminated construction science database by removing biomedical entities.
"""

import sqlite3
import sys
from pathlib import Path

# Import our domain enforcement system
sys.path.append('utils')
from domain_enforcement import ALLOWED_ENTITY_TYPES_BY_DOMAIN

def clean_construction_database(db_path):
    """Clean a contaminated construction science database."""
    
    print("🧹 CLEANING CONTAMINATED CONSTRUCTION DATABASE")
    print("=" * 60)
    print(f"Database: {db_path}")
    print()
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    # Get the list of contaminated entity types for construction
    construction_allowed = ALLOWED_ENTITY_TYPES_BY_DOMAIN["construction_science"]
    all_possible_types = {
        "peptide", "compound", "target", "pathway", "indication",
        "model", "stem_cell", "neural_cell", "assay",
        "material", "materials", "system", "systems",
        "failure_mode", "failure_modes", "environment", "environments",
        "hazard", "hazards", "test_method", "test_methods",
        "code", "codes", "property", "properties"
    }
    contaminated_types = all_possible_types - construction_allowed
    
    print(f"🏗️  Construction-allowed entity types: {sorted(construction_allowed)}")
    print(f"🚫 Contaminated entity types to remove: {sorted(contaminated_types)}")
    print()
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Count current entities by type
        print("📊 Current entity distribution:")
        cursor.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type ORDER BY COUNT(*) DESC')
        current_counts = cursor.fetchall()
        for entity_type, count in current_counts:
            status = "✅" if entity_type in construction_allowed else "❌"
            print(f"  {status} {entity_type}: {count}")
        print()
        
        # Count events by biological system
        print("🔬 Current biological systems:")
        cursor.execute('SELECT biological_system, COUNT(*) FROM research_events GROUP BY biological_system ORDER BY COUNT(*) DESC')
        bio_systems = cursor.fetchall()
        for bio_sys, count in bio_systems:
            print(f"  {bio_sys}: {count} events")
        print()
        
        # Remove contaminated entities
        print("🧹 Removing contaminated entities...")
        removed_count = 0
        
        for entity_type in contaminated_types:
            # First, remove event_entities references
            cursor.execute('DELETE FROM event_entities WHERE entity_id IN (SELECT entity_id FROM entities WHERE entity_type = ?)', (entity_type,))
            removed_refs = cursor.rowcount
            
            # Then remove the entities themselves
            cursor.execute('DELETE FROM entities WHERE entity_type = ?', (entity_type,))
            removed_entities = cursor.rowcount
            
            if removed_entities > 0:
                print(f"  Removed {removed_entities} entities of type '{entity_type}' + {removed_refs} references")
                removed_count += removed_entities
        
        # Remove events with biological systems (should be None for construction)
        print("🧹 Removing events with biological systems...")
        cursor.execute('DELETE FROM research_events WHERE biological_system IS NOT NULL AND biological_system != "None"')
        removed_events = cursor.rowcount
        print(f"  Removed {removed_events} events with biological systems")
        
        # Clean up any orphaned event_entities
        print("🧹 Cleaning up orphaned event-entity relationships...")
        cursor.execute('DELETE FROM event_entities WHERE event_id NOT IN (SELECT event_id FROM research_events)')
        orphaned_refs = cursor.rowcount
        print(f"  Removed {orphaned_refs} orphaned event-entity relationships")
        
        conn.commit()
        
        # Verify cleanup
        print("\n✅ VERIFICATION - After cleanup:")
        
        # Check remaining entities
        cursor.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type ORDER BY COUNT(*) DESC')
        remaining_counts = cursor.fetchall()
        print("📊 Remaining entity distribution:")
        for entity_type, count in remaining_counts:
            status = "✅" if entity_type in construction_allowed else "❌"
            print(f"  {status} {entity_type}: {count}")
        
        # Check remaining events
        cursor.execute('SELECT COUNT(*) FROM research_events')
        total_events = cursor.fetchone()[0]
        print(f"\n📈 Total remaining events: {total_events}")
        
        # Check biological systems
        cursor.execute('SELECT biological_system, COUNT(*) FROM research_events GROUP BY biological_system ORDER BY COUNT(*) DESC')
        remaining_bio_systems = cursor.fetchall()
        print("🔬 Remaining biological systems:")
        for bio_sys, count in remaining_bio_systems:
            print(f"  {bio_sys}: {count} events")
        
        print(f"\n🎉 CLEANUP COMPLETE!")
        print(f"   Removed {removed_count} contaminated entities")
        print(f"   Removed {removed_events} events with biological systems")
        print(f"   Database is now construction-science pure!")

if __name__ == "__main__":
    # Clean the test database
    clean_construction_database('runs/test_construction_fix.sqlite')