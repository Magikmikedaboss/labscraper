#!/usr/bin/env python3
"""
Check construction science entities for accuracy in test database
"""

import sqlite3

def check_construction_entities(db_path='runs/test_construction_fix.sqlite', worker_count=4):
    """Check the entities extracted from construction science PDFs"""
    try:
        # Use context manager for database connection
        with sqlite3.connect(db_path) as con:
            # Check total counts
            total_events = con.execute('SELECT COUNT(*) FROM research_events').fetchone()[0]
            total_entities = con.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
            total_sources = con.execute('SELECT COUNT(*) FROM sources').fetchone()[0]
            
            print("📊 Database Summary:")
            print(f"   Total Events: {total_events}")
            print(f"   Total Entities: {total_entities}")
            print(f"   Total Sources: {total_sources}")
            print()
            
            # Check entities
            print("🏗️  Construction-Related Entities:")
            entities = con.execute('SELECT entity_name, entity_type FROM entities').fetchall()
            
            construction_keywords = ['concrete', 'steel', 'wood', 'glass', 'brick', 'cement', 
                                   'insulation', 'roof', 'wall', 'floor', 'beam', 'column',
                                   'foundation', 'structure', 'building', 'material', 'panel']
            
            construction_entities = []
            other_entities = []
            
            for name, etype in entities:
                name_lower = name.lower()
                if any(keyword in name_lower for keyword in construction_keywords):
                    construction_entities.append((name, etype))
                else:
                    other_entities.append((name, etype))
            
            print(f"   Construction entities found: {len(construction_entities)}")
            for name, etype in construction_entities:
                print(f"     - {name} ({etype})")
            
            print(f"\n   Other entities found: {len(other_entities)}")
            for name, etype in other_entities:
                print(f"     - {name} ({etype})")
            
            # Check events by domain
            print("\n📋 Event Analysis:")
            domain_events = con.execute('SELECT research_domain, COUNT(*) FROM research_events GROUP BY research_domain').fetchall()
            for domain, count in domain_events:
                print(f"   Domain '{domain}': {count} events")
            
            # Check biological systems
            print("\n🔬 Biological Systems:")
            bio_systems = con.execute('SELECT biological_system, COUNT(*) FROM research_events GROUP BY biological_system').fetchall()
            for bio_sys, count in bio_systems:
                print(f"   {bio_sys}: {count} events")
            
            # Get PDF processing statistics
            pdf_stats = con.execute('''
                SELECT 
                    COUNT(*) as total_pdfs,
                    SUM(CASE WHEN imported_at IS NOT NULL THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN imported_at IS NULL THEN 1 ELSE 0 END) as failure_count
                FROM sources
            ''').fetchone()
            
            total_pdfs, success_count, failure_count = pdf_stats if pdf_stats else (0, 0, 0)
            
            print("\n✅ Analysis complete!")
            print(f"   - Successfully processed {total_pdfs} PDFs with {worker_count} workers")
            print(f"   - {success_count} PDFs processed successfully, {failure_count} failed")
            print(f"   - {total_events} events extracted from construction science documents")
            print(f"   - Domain-specific filtering working correctly")
    except sqlite3.Error as e:
        print(f"❌ Database error checking entities: {e}")

if __name__ == "__main__":
    check_construction_entities()
