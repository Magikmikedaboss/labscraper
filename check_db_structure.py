#!/usr/bin/env python3
"""
Check database structure and domain filtering
"""

import sqlite3

def check_db_structure():
    """Check the database structure and domain filtering"""
    db_path = 'runs/construction_science.sqlite'
    
    try:
        # Use context manager for database connection
        with sqlite3.connect(db_path) as con:
            print("📊 Database Structure Analysis:")
            print("=" * 50)
            
            # Check events by domain
            print("\n📋 Events by Domain:")
            domains = con.execute('SELECT research_domain, COUNT(*) FROM research_events GROUP BY research_domain').fetchall()
            for d, c in domains:
                print(f"   {d}: {c} events")
            
            # Check entities
            print(f"\n🏗️  Total Entities: {con.execute('SELECT COUNT(*) FROM entities').fetchone()[0]}")
            
            # Check event_entities table
            print(f"\n🔗 Event-Entity Relationships: {con.execute('SELECT COUNT(*) FROM event_entities').fetchone()[0]}")
            
            # Check entities linked to construction science events
            print(f"\n🔍 Entities linked to construction_science events:")
            linked_entities = con.execute("""
                SELECT DISTINCT e.entity_name, e.entity_type 
                FROM entities e
                JOIN event_entities ee ON e.entity_id = ee.entity_id
                JOIN research_events re ON ee.event_id = re.event_id
                WHERE re.research_domain = 'construction_science'
            """).fetchall()
            
            print(f"   Found {len(linked_entities)} entities:")
            for name, etype in linked_entities:
                print(f"     - {name} ({etype})")
            
            # Check for entities NOT linked to construction science
            print(f"\n⚠️  Entities NOT linked to construction_science events:")
            unlinked_entities = con.execute("""
                SELECT DISTINCT e.entity_name, e.entity_type 
                FROM entities e
                WHERE e.entity_id NOT IN (
                    SELECT DISTINCT ee.entity_id 
                    FROM event_entities ee
                    JOIN research_events re ON ee.event_id = re.event_id
                    WHERE re.research_domain = 'construction_science'
                )
            """).fetchall()
            
            print(f"   Found {len(unlinked_entities)} entities:")
            for name, etype in unlinked_entities:
                print(f"     - {name} ({etype})")
            
            print(f"\n✅ Analysis complete!")
            print(f"   - Database contains {len(domains)} domain(s)")
            print(f"   - {len(linked_entities)} entities are properly linked to construction_science")
            print(f"   - {len(unlinked_entities)} entities appear to be from other domains")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    check_db_structure()