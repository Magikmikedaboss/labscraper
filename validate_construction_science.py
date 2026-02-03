#!/usr/bin/env python3
"""
Comprehensive validation script for construction science scraper results
"""

import sqlite3
import json
from pathlib import Path

def validate_construction_science():
    print("🏗️  CONSTRUCTION SCIENCE VALIDATION")
    print("=" * 60)
    
    db_path = Path("runs/construction_science_final.sqlite")
    
    if not db_path.exists():
        print("❌ Database not found:", db_path)
        return False
    
    print(f"✅ Database found: {db_path}")
    
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Check tables
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"📊 Tables found: {[t['name'] for t in tables]}")
        
        # Check domain
        domain_check = cur.execute("SELECT DISTINCT research_domain FROM research_events").fetchall()
        print(f"🎯 Research domain: {[d['research_domain'] for d in domain_check]}")
        
        # Check entity types
        entity_types = cur.execute("""
            SELECT entity_type, COUNT(*) as count
            FROM entities 
            GROUP BY entity_type 
            ORDER BY count DESC
        """).fetchall()
        
        print(f"\n🏗️  Entity Types (Construction Science):")
        construction_entities = 0
        biomedical_contamination = 0
        
        for row in entity_types:
            entity_type = row['entity_type']
            count = row['count']
            
            # Construction science entity types
            construction_types = {
                'material', 'materials', 'system', 'systems', 
                'environment', 'environments', 'failure_mode', 'failure_modes',
                'hazard', 'hazards', 'test_method', 'test_methods', 'code', 'codes'
            }
            
            # Biomedical entity types (contamination)
            biomedical_types = {
                'peptide', 'compound', 'target', 'pathway', 'indication',
                'model', 'stem_cell', 'neural_cell', 'assay'
            }
            
            if entity_type in construction_types:
                construction_entities += count
                print(f"   ✅ {entity_type}: {count}")
            elif entity_type in biomedical_types:
                biomedical_contamination += count
                print(f"   ❌ {entity_type}: {count} (BIOMEDICAL CONTAMINATION)")
            else:
                print(f"   ⚠️  {entity_type}: {count} (UNKNOWN TYPE)")
        
        # Check events
        event_counts = cur.execute("""
            SELECT COUNT(*) as total_events
            FROM research_events
        """).fetchone()
        
        print(f"\n📈 Total Events: {event_counts['total_events']}")
        
        # Check confidence distribution
        confidence_counts = cur.execute("""
            SELECT confidence, COUNT(*) as count
            FROM research_events
            GROUP BY confidence
        """).fetchall()
        
        print(f"\n🎯 Confidence Distribution:")
        for row in confidence_counts:
            print(f"   {row['confidence']}: {row['count']}")
        
        # Check top entities
        top_entities = cur.execute("""
            SELECT e.entity_name, e.entity_type, COUNT(ee.event_id) as event_count
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            GROUP BY e.entity_id
            ORDER BY event_count DESC
            LIMIT 15
        """).fetchall()
        
        print(f"\n🏆 Top 15 Entities by Event Count:")
        for i, row in enumerate(top_entities, 1):
            print(f"   {i:2}. {row['entity_name']} ({row['entity_type']}): {row['event_count']} events")
        
        # Check biological systems (should be None for construction)
        bio_systems = cur.execute("""
            SELECT biological_system, COUNT(*) as count
            FROM research_events
            GROUP BY biological_system
        """).fetchall()
        
        print(f"\n🔬 Biological Systems:")
        for row in bio_systems:
            print(f"   {row['biological_system']}: {row['count']}")
        
        # Check event types
        event_types = cur.execute("""
            SELECT event_type, COUNT(*) as count
            FROM research_events
            GROUP BY event_type
            ORDER BY count DESC
        """).fetchall()
        
        print(f"\n📋 Event Types:")
        for row in event_types:
            print(f"   {row['event_type']}: {row['count']}")
        
        # Check measurements
        measurements = cur.execute("""
            SELECT COUNT(*) as total_measurements
            FROM quantitative_measurements
        """).fetchone()
        
        print(f"\n📏 Total Measurements: {measurements['total_measurements']}")
        
        # Check relationships
        relationships = cur.execute("""
            SELECT COUNT(*) as total_relationships
            FROM entity_relationships
        """).fetchone()
        
        print(f"🔗 Total Relationships: {relationships['total_relationships']}")
        
        # Validation summary
        print(f"\n🔍 VALIDATION SUMMARY:")
        print(f"   Construction entities: {construction_entities}")
        print(f"   Biomedical contamination: {biomedical_contamination}")
        
        if biomedical_contamination > 0:
            print(f"   ❌ CONTAMINATION DETECTED: {biomedical_contamination} biomedical entities found")
            return False
        else:
            print(f"   ✅ CLEAN: No biomedical contamination detected")
        
        if construction_entities > 0:
            print(f"   ✅ CONSTRUCTION ENTITIES: {construction_entities} construction entities found")
        else:
            print(f"   ❌ NO CONSTRUCTION ENTITIES: No construction entities found")
            return False
        
        if event_counts['total_events'] > 0:
            print(f"   ✅ EVENTS: {event_counts['total_events']} events extracted")
        else:
            print(f"   ❌ NO EVENTS: No events extracted")
            return False
        
        print(f"\n🎉 VALIDATION COMPLETE!")
        print(f"   Construction science scraper is working correctly!")
        return True

if __name__ == "__main__":
    success = validate_construction_science()
    if success:
        print("\n✅ ALL TESTS PASSED - Construction science scraper is ready!")
    else:
        print("\n❌ VALIDATION FAILED - Issues detected in construction science scraper")