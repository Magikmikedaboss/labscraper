"""
Test Phase 1 Results - Analyze entity extraction
"""
import sqlite3
from pathlib import Path
from collections import Counter

DB_PATH = Path("output") / "peptide_intel.sqlite"

def analyze_phase1_results():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    print("=" * 60)
    print("PHASE 1 RESULTS ANALYSIS")
    print("=" * 60)
    
    # 1. Overall stats
    total_events = cur.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]
    total_entities = cur.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    events_with_entities = cur.execute("""
        SELECT COUNT(DISTINCT event_id) 
        FROM event_entities
    """).fetchone()[0]
    
    coverage = (events_with_entities / total_events * 100) if total_events > 0 else 0
    
    print(f"\n📊 Overall Stats:")
    print(f"   Total events: {total_events}")
    print(f"   Total unique entities: {total_entities}")
    print(f"   Events with entities: {events_with_entities}/{total_events} ({coverage:.1f}%)")
    print(f"   Target: ≥70% coverage")
    print(f"   Status: {'✅ PASS' if coverage >= 70 else '❌ FAIL'}")
    
    # 2. Entity type breakdown
    print(f"\n📋 Entity Types Extracted:")
    entity_types = cur.execute("""
        SELECT entity_type, COUNT(*) as count
        FROM entities
        GROUP BY entity_type
        ORDER BY count DESC
    """).fetchall()
    
    for etype, count in entity_types:
        print(f"   {etype}: {count}")
    
    # 3. Top entities by type
    print(f"\n🔝 Top 10 Entities Overall:")
    top_entities = cur.execute("""
        SELECT e.entity_type, e.entity_name, COUNT(ee.event_id) as event_count
        FROM entities e
        JOIN event_entities ee ON e.entity_id = ee.entity_id
        GROUP BY e.entity_id
        ORDER BY event_count DESC
        LIMIT 10
    """).fetchall()
    
    for etype, name, count in top_entities:
        print(f"   {name} ({etype}): {count} events")
    
    # 4. NEW entity types (assays, pathways, indications)
    print(f"\n🆕 NEW Entity Types (Phase 1):")
    for new_type in ['assay', 'pathway', 'indication']:
        count = cur.execute("""
            SELECT COUNT(*) FROM entities WHERE entity_type = ?
        """, (new_type,)).fetchone()[0]
        
        events_count = cur.execute("""
            SELECT COUNT(DISTINCT ee.event_id)
            FROM event_entities ee
            JOIN entities e ON ee.entity_id = e.entity_id
            WHERE e.entity_type = ?
        """, (new_type,)).fetchone()[0]
        
        print(f"   {new_type}: {count} unique, {events_count} events")
        
        # Show top 5 for this type
        if count > 0:
            top = cur.execute("""
                SELECT e.entity_name, COUNT(ee.event_id) as cnt
                FROM entities e
                JOIN event_entities ee ON e.entity_id = ee.entity_id
                WHERE e.entity_type = ?
                GROUP BY e.entity_id
                ORDER BY cnt DESC
                LIMIT 5
            """, (new_type,)).fetchall()
            
            for name, cnt in top:
                print(f"      - {name}: {cnt} events")
    
    # 5. Events without entities - why?
    print(f"\n❓ Events Without Entities:")
    events_without = total_events - events_with_entities
    print(f"   Count: {events_without} ({(events_without/total_events*100):.1f}%)")
    
    # Sample some events without entities
    sample = cur.execute("""
        SELECT event_type, evidence_snippet
        FROM research_events
        WHERE event_id NOT IN (SELECT DISTINCT event_id FROM event_entities)
        LIMIT 5
    """).fetchall()
    
    print(f"\n   Sample events without entities:")
    for i, (etype, snippet) in enumerate(sample, 1):
        print(f"   {i}. [{etype}] {snippet[:100]}...")
    
    # 6. Confidence distribution
    print(f"\n📈 Confidence Distribution:")
    conf_dist = cur.execute("""
        SELECT confidence, COUNT(*) as count
        FROM research_events
        GROUP BY confidence
        ORDER BY 
            CASE confidence 
                WHEN 'high' THEN 1 
                WHEN 'med' THEN 2 
                WHEN 'low' THEN 3 
            END
    """).fetchall()
    
    for conf, count in conf_dist:
        pct = (count / total_events * 100) if total_events > 0 else 0
        print(f"   {conf}: {count} ({pct:.1f}%)")
    
    con.close()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    analyze_phase1_results()
