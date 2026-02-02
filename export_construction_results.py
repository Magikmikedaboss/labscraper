#!/usr/bin/env python3
"""
Export construction science results to CSV files for analysis.
"""

import sqlite3
import csv
from pathlib import Path
import os

def export_construction_results():
    """Export construction science results to CSV files"""
    db_path = Path("runs/construction_clean.sqlite")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print("📊 EXPORTING CONSTRUCTION SCIENCE RESULTS")
    print("=" * 60)
    print(f"📁 Database: {db_path.name}")
    print()
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Export entities
        print("📝 Exporting entities...")
        entities_file = output_dir / "construction_entities.csv"
        with open(entities_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['entity_id', 'entity_type', 'entity_name', 'entity_variant', 'organism', 'created_at'])
            
            cursor.execute('''
            SELECT e.entity_id, e.entity_type, e.entity_name, e.entity_variant, e.organism, e.created_at
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            JOIN research_events re ON ee.event_id = re.event_id
            WHERE re.research_domain = 'construction_science'
            ORDER BY e.entity_type, e.entity_name
            ''')
            
            entities = cursor.fetchall()
            writer.writerows(entities)
            print(f"   ✅ {len(entities)} entities exported to {entities_file.name}")
        
        # Export events
        print("📝 Exporting events...")
        events_file = output_dir / "construction_events.csv"
        with open(events_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['event_id', 'research_domain', 'event_type', 'study_stage', 'biological_system', 
                           'application_area', 'outcome', 'failure_reason', 'decision_taken', 'decision_driver',
                           'evidence_snippet', 'evidence_strength', 'confidence', 'source_id', 'doc_id', 
                           'chunk_id', 'page_number', 'created_at'])
            
            cursor.execute('''
            SELECT re.event_id, re.research_domain, re.event_type, re.study_stage, re.biological_system,
                   re.application_area, re.outcome, re.failure_reason, re.decision_taken, re.decision_driver,
                   re.evidence_snippet, re.evidence_strength, re.confidence, re.source_id, re.doc_id,
                   re.chunk_id, re.page_number, re.created_at
            FROM research_events re
            WHERE re.research_domain = 'construction_science'
            ORDER BY re.created_at
            ''')
            
            events = cursor.fetchall()
            writer.writerows(events)
            print(f"   ✅ {len(events)} events exported to {events_file.name}")
        
        # Export event-entities relationships
        print("📝 Exporting event-entity relationships...")
        relationships_file = output_dir / "construction_event_entities.csv"
        with open(relationships_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['event_id', 'entity_id', 'role'])
            
            cursor.execute('''
            SELECT ee.event_id, ee.entity_id, ee.role
            FROM event_entities ee
            JOIN research_events re ON ee.event_id = re.event_id
            WHERE re.research_domain = 'construction_science'
            ORDER BY ee.event_id, ee.entity_id
            ''')
            
            relationships = cursor.fetchall()
            writer.writerows(relationships)
            print(f"   ✅ {len(relationships)} relationships exported to {relationships_file.name}")
        
        # Export sources
        print("📝 Exporting sources...")
        sources_file = output_dir / "construction_sources.csv"
        with open(sources_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['source_id', 'pdf_file', 'title', 'authors', 'year', 'doi', 'imported_at'])
            
            cursor.execute('''
            SELECT DISTINCT s.source_id, s.pdf_file, s.title, s.authors, s.year, s.doi, s.imported_at
            FROM sources s
            JOIN research_events re ON s.source_id = re.source_id
            WHERE re.research_domain = 'construction_science'
            ORDER BY s.source_id
            ''')
            
            sources = cursor.fetchall()
            writer.writerows(sources)
            print(f"   ✅ {len(sources)} sources exported to {sources_file.name}")
        
        # Export summary statistics
        print("📝 Exporting summary statistics...")
        summary_file = output_dir / "construction_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            # Entity types summary
            cursor.execute('''
            SELECT e.entity_type, COUNT(*) as count
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            JOIN research_events re ON ee.event_id = re.event_id
            WHERE re.research_domain = 'construction_science'
            GROUP BY e.entity_type
            ORDER BY count DESC
            ''')
            entity_stats = cursor.fetchall()
            
            f.write("🏗️ CONSTRUCTION SCIENCE SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Database: {db_path.name}\n")
            f.write(f"Domain: construction_science\n\n")
            
            f.write("📊 Entity Types:\n")
            for entity_type, count in entity_stats:
                f.write(f"  {entity_type}: {count}\n")
            f.write("\n")
            
            # Top entities
            cursor.execute('''
            SELECT e.entity_name, e.entity_type, COUNT(*) as frequency
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            JOIN research_events re ON ee.event_id = re.event_id
            WHERE re.research_domain = 'construction_science'
            GROUP BY e.entity_name, e.entity_type
            ORDER BY frequency DESC
            LIMIT 20
            ''')
            top_entities = cursor.fetchall()
            
            f.write("🏆 Top 20 Entities:\n")
            for name, entity_type, freq in top_entities:
                f.write(f"  {name} ({entity_type}): {freq}\n")
            f.write("\n")
            
            # Event types
            cursor.execute('''
            SELECT re.event_type, COUNT(*) as count
            FROM research_events re
            WHERE re.research_domain = 'construction_science'
            GROUP BY re.event_type
            ORDER BY count DESC
            ''')
            event_stats = cursor.fetchall()
            
            f.write("📈 Event Types:\n")
            for event_type, count in event_stats:
                f.write(f"  {event_type}: {count}\n")
            f.write("\n")
            
            # Summary stats
            cursor.execute('SELECT COUNT(*) FROM research_events WHERE research_domain = "construction_science"')
            total_events = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(DISTINCT e.entity_id) FROM entities e JOIN event_entities ee ON e.entity_id = ee.entity_id JOIN research_events re ON ee.event_id = re.event_id WHERE re.research_domain = "construction_science"')
            total_entities = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(DISTINCT re.source_id) FROM research_events re WHERE re.research_domain = "construction_science"')
            total_sources = cursor.fetchone()[0]
            
            f.write("📊 Summary Statistics:\n")
            f.write(f"  Total events: {total_events}\n")
            f.write(f"  Total unique entities: {total_entities}\n")
            f.write(f"  Total sources (PDFs): {total_sources}\n")
            f.write(f"  Export date: {os.popen('date').read().strip()}\n")
        
        print(f"   ✅ Summary exported to {summary_file.name}")
        print()
        print("🎉 EXPORT COMPLETE!")
        print(f"📁 All files saved to: {output_dir.resolve()}")
        print()
        print("📋 Exported files:")
        print(f"   - {entities_file.name} ({len(entities)} entities)")
        print(f"   - {events_file.name} ({len(events)} events)")
        print(f"   - {relationships_file.name} ({len(relationships)} relationships)")
        print(f"   - {sources_file.name} ({len(sources)} sources)")
        print(f"   - {summary_file.name} (summary statistics)")
        
    except Exception as e:
        print(f"❌ Error during export: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_construction_results()