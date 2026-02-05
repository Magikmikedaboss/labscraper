#!/usr/bin/env python3
"""
Analyze the construction science scraping results to see what entities and seeds are being extracted.
"""

import sqlite3
from pathlib import Path

def analyze_construction_results():
    """Analyze the construction science database results"""
    db_path = Path("db/runs.sqlite")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print("🏗️ CONSTRUCTION SCIENCE ENTITY ANALYSIS")
    print("=" * 60)
    print(f"📊 Analyzing database: {db_path.name}")
    print()
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Get entity types and counts
        print("📊 Entity Types Extracted:")
        cursor.execute('''
        SELECT e.entity_type, COUNT(*) as count
        FROM entities e
        JOIN event_entities ee ON e.entity_id = ee.entity_id
        JOIN research_events re ON ee.event_id = re.event_id
        WHERE re.research_domain = 'construction'
        GROUP BY e.entity_type
        ORDER BY count DESC
        ''')
        entity_stats = cursor.fetchall()
        for entity_type, count in entity_stats:
            print(f"  {entity_type}: {count} entities")
        print()
        
        # Get top entities by frequency
        print("🏆 Top 20 Most Frequent Entities:")
        cursor.execute('''
        SELECT e.entity_name, e.entity_type, COUNT(*) as frequency
        FROM entities e
        JOIN event_entities ee ON e.entity_id = ee.entity_id
        JOIN research_events re ON ee.event_id = re.event_id
        WHERE re.research_domain = 'construction'
        GROUP BY e.entity_name, e.entity_type
        ORDER BY frequency DESC
        LIMIT 20
        ''')
        top_entities = cursor.fetchall()
        for name, entity_type, freq in top_entities:
            print(f"  {name} ({entity_type}): {freq} occurrences")
        print()
        
        # Get sample evidence snippets
        print("🔍 Sample Evidence Snippets:")
        cursor.execute('''
        SELECT re.evidence_snippet, e.entity_name, e.entity_type
        FROM research_events re
        JOIN event_entities ee ON re.event_id = ee.event_id
        JOIN entities e ON ee.entity_id = e.entity_id
        WHERE re.research_domain = 'construction'
        ORDER BY re.created_at DESC
        LIMIT 5
        ''')
        samples = cursor.fetchall()
        for snippet, name, entity_type in samples:
            snippet_text = snippet or ""
            print(f"  {name} ({entity_type}): {snippet_text[:120]}...")
        print()
        
        # Get event types distribution
        print("📈 Event Types Distribution:")
        cursor.execute('''
        SELECT re.event_type, COUNT(*) as count
        FROM research_events re
        WHERE re.research_domain = 'construction'
        GROUP BY re.event_type
        ORDER BY count DESC
        ''')
        event_stats = cursor.fetchall()
        for event_type, count in event_stats:
            print(f"  {event_type}: {count} events")
        print()
        
        # Get failure reasons
        print("⚠️  Failure Reasons Found:")
        cursor.execute('''
        SELECT re.failure_reason, COUNT(*) as count
        FROM research_events re
        WHERE re.research_domain = 'construction' AND re.failure_reason != 'unknown'
        GROUP BY re.failure_reason
        ORDER BY count DESC
        ''')
        failure_stats = cursor.fetchall()
        for failure_reason, count in failure_stats:
            print(f"  {failure_reason}: {count} events")
        print()
        
        # Get study stages
        print("🔬 Study Stages Distribution:")
        cursor.execute('''
        SELECT re.study_stage, COUNT(*) as count
        FROM research_events re
        WHERE re.research_domain = 'construction'
        GROUP BY re.study_stage
        ORDER BY count DESC
        ''')
        stage_stats = cursor.fetchall()
        for stage, count in stage_stats:
            print(f"  {stage}: {count} events")
        print()
        
        # Get biological systems (should be construction systems)
        print("🏗️  Biological Systems (Construction Context):")
        cursor.execute('''
        SELECT re.biological_system, COUNT(*) as count
        FROM research_events re
        WHERE re.research_domain = 'construction' AND re.biological_system IS NOT NULL
        GROUP BY re.biological_system
        ORDER BY count DESC
        LIMIT 10
        ''')
        system_stats = cursor.fetchall()
        for system, count in system_stats:
            print(f"  {system}: {count} events")
        print()
        
        # Check for domain contamination (biomedical entities)
        print("🔒 Domain Contamination Check:")
        cursor.execute('''
        SELECT e.entity_type, COUNT(*) as count
        FROM entities e
        JOIN event_entities ee ON e.entity_id = ee.entity_id
        JOIN research_events re ON ee.event_id = re.event_id
        WHERE re.research_domain = 'construction' 
        AND e.entity_type IN ('peptide', 'compound', 'target', 'model', 'stem_cell', 'neural_cell')
        GROUP BY e.entity_type
        ''')
        contamination = cursor.fetchall()
        if contamination:
            print("❌ DOMAIN CONTAMINATION DETECTED:")
            for entity_type, count in contamination:
                print(f"  {entity_type}: {count} entities (should be 0)")
        else:
            print("✅ CLEAN: No biomedical entity contamination detected")
        print()
        
        # Summary statistics
        print("📊 SUMMARY STATISTICS:")
        cursor.execute('SELECT COUNT(*) FROM research_events WHERE research_domain = "construction"')
        total_events = cursor.fetchone()[0]
        print(f"  Total events: {total_events}")
        
        cursor.execute('SELECT COUNT(DISTINCT e.entity_id) FROM entities e JOIN event_entities ee ON e.entity_id = ee.entity_id JOIN research_events re ON ee.event_id = re.event_id WHERE re.research_domain = "construction"')
        total_entities = cursor.fetchone()[0]
        print(f"  Total unique entities: {total_entities}")
        
        cursor.execute('SELECT COUNT(DISTINCT re.source_id) FROM research_events re WHERE re.research_domain = "construction"')
        total_sources = cursor.fetchone()[0]
        print(f"  Total sources (PDFs): {total_sources}")
        
        print("\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    analyze_construction_results()