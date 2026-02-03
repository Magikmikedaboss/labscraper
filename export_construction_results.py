#!/usr/bin/env python3
"""
Export construction science results from db/runs.sqlite
"""

import sqlite3
import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

DB_PATH = Path("db/runs.sqlite")
OUTPUT_DIR = Path("output")
DOMAIN_ID = "construction_science"

def export_events():
    """Export research events from construction database"""
    print("🏗️  Exporting construction science events...")
    
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Get all events
        events = cur.execute("""
            SELECT 
                re.event_id,
                re.research_domain,
                re.event_type,
                re.study_stage,
                re.outcome,
                re.decision_driver,
                re.evidence_snippet,
                re.confidence,
                re.source_id,
                re.created_at,
                GROUP_CONCAT(e.entity_type || ':' || e.entity_name, '; ') as entities
            FROM research_events re
            LEFT JOIN event_entities ee ON re.event_id = ee.event_id
            LEFT JOIN entities e ON ee.entity_id = e.entity_id
            WHERE re.research_domain = ?
            GROUP BY re.event_id
            ORDER BY re.created_at DESC
        """, (DOMAIN_ID,)).fetchall()
    
    # Export events
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events_path = OUTPUT_DIR / f"events_export_{DOMAIN_ID}.csv"
    
    with open(events_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'event_id', 'domain', 'event_type', 'stage', 'outcome',
            'decision_driver', 'evidence_snippet', 'confidence',
            'entities', 'source_id', 'created_at'
        ])
        
        for event in events:
            writer.writerow([
                event['event_id'], event['research_domain'], event['event_type'], 
                event['study_stage'], event['outcome'], event['decision_driver'],
                event['evidence_snippet'], event['confidence'], event['entities'],
                event['source_id'], event['created_at']
            ])
    
    print(f"✅ Exported {len(events)} events to {events_path}")
    return events

def export_entities():
    """Export entities from construction database"""
    print("🏗️  Exporting construction science entities...")
    
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Get entity statistics
        entities = cur.execute("""
            SELECT 
                e.entity_type,
                e.entity_name,
                COUNT(DISTINCT ee.event_id) as event_count,
                COUNT(DISTINCT re.source_id) as paper_count,
                MIN(re.created_at) as first_seen,
                MAX(re.created_at) as last_seen
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            JOIN research_events re ON ee.event_id = re.event_id
            WHERE re.research_domain = ?
            GROUP BY e.entity_type, e.entity_name
            ORDER BY event_count DESC, e.entity_type
        """, (DOMAIN_ID,)).fetchall()
    
    # Export entities
    entities_path = OUTPUT_DIR / f"{DOMAIN_ID}_entities.csv"
    
    with open(entities_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'entity_type', 'entity_name', 'event_count', 'paper_count',
            'first_seen', 'last_seen'
        ])
        
        for entity in entities:
            writer.writerow([
                entity['entity_type'], entity['entity_name'], 
                entity['event_count'], entity['paper_count'],
                entity['first_seen'], entity['last_seen']
            ])
    
    print(f"✅ Exported {len(entities)} entities to {entities_path}")
    return entities

def export_event_entities():
    """Export event-entity relationships"""
    print("🏗️  Exporting event-entity relationships...")
    
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Get event-entity relationships
        relationships = cur.execute("""
            SELECT 
                re.event_id,
                re.research_domain,
                re.event_type,
                e.entity_type,
                e.entity_name,
                e.entity_variant
            FROM research_events re
            JOIN event_entities ee ON re.event_id = ee.event_id
            JOIN entities e ON ee.entity_id = e.entity_id
            WHERE re.research_domain = ?
            ORDER BY re.event_id, e.entity_type, e.entity_name
        """, (DOMAIN_ID,)).fetchall()
    
    # Export relationships
    relationships_path = OUTPUT_DIR / f"{DOMAIN_ID}_event_entities.csv"
    
    with open(relationships_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'event_id', 'domain', 'event_type', 'entity_type', 
            'entity_name', 'entity_variant'
        ])
        
        for rel in relationships:
            writer.writerow([
                rel['event_id'], rel['research_domain'], rel['event_type'],
                rel['entity_type'], rel['entity_name'], rel['entity_variant']
            ])
    
    print(f"✅ Exported {len(relationships)} relationships to {relationships_path}")
    return relationships

def export_sources():
    """Export source information for construction-related sources only"""
    print("🏗️  Exporting source information...")
    
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Get source information for sources that have construction events
        sources = cur.execute("""
            SELECT DISTINCT
                s.source_id,
                s.pdf_file,
                s.title,
                s.authors,
                s.year,
                s.doi,
                s.imported_at
            FROM sources s
            WHERE s.source_id IN (
                SELECT DISTINCT re.source_id 
                FROM research_events re 
                WHERE re.research_domain = ?
            )
            ORDER BY s.imported_at DESC
        """, (DOMAIN_ID,)).fetchall()
    
    # Export sources
    sources_path = OUTPUT_DIR / f"{DOMAIN_ID}_sources.csv"
    
    with open(sources_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'source_id', 'pdf_file', 'title', 'authors',
            'year', 'doi', 'imported_at'
        ])
        
        for source in sources:
            writer.writerow([
                source['source_id'], source['pdf_file'], source['title'],
                source['authors'], source['year'], source['doi'],
                source['imported_at']
            ])
    
    print(f"✅ Exported {len(sources)} sources to {sources_path}")
    return sources

def write_run_meta(events, entities, relationships, sources):
    """Write run metadata for reproducibility"""
    print("🏗️  Writing run metadata...")
    
    meta = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "engine_version": "construction_science_export_v1",
        "timestamp": datetime.now().isoformat(),
        "database": str(DB_PATH.as_posix()),
        "domain": DOMAIN_ID,
        "counts": {
            "total_events": len(events),
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "total_sources": len(sources),
            "entity_types": {}
        },
        "entity_type_breakdown": {},
        "date_range": {
            "earliest_event": None,
            "latest_event": None
        }
    }
    
    # Count entity types
    entity_type_counts = defaultdict(int)
    for entity in entities:
        entity_type_counts[entity['entity_type']] += 1
    
    meta["counts"]["entity_types"] = dict(entity_type_counts)
    
    # Entity type breakdown
    for entity_type, count in entity_type_counts.items():
        meta["entity_type_breakdown"][entity_type] = count
    
    # Date range
    if events:
        meta["date_range"]["earliest_event"] = min(e['created_at'] for e in events)
        meta["date_range"]["latest_event"] = max(e['created_at'] for e in events)
    
    # Top entities by event count
    meta["top_entities"] = [
        {
            "name": entity['entity_name'],
            "type": entity['entity_type'],
            "event_count": entity['event_count'],
            "paper_count": entity['paper_count']
        }
        for entity in sorted(entities, key=lambda x: x['event_count'], reverse=True)[:20]
    ]
    
    # Top events by confidence using priority mapping
    confidence_priority = {'high': 3, 'med': 2, 'low': 1}
    meta["top_events"] = [
        {
            "event_id": event['event_id'],
            "type": event['event_type'],
            "confidence": event['confidence'],
            "outcome": event['outcome'][:100] + "..." if event['outcome'] and len(event['outcome']) > 100 else (event['outcome'] or "")
        }
        for event in sorted(events, key=lambda x: confidence_priority.get(x['confidence'], 0), reverse=True)[:10]
    ]
    
    meta_path = OUTPUT_DIR / f"run_meta_{DOMAIN_ID}.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    
    print(f"✅ Wrote run metadata: {meta_path}")
    return meta

def main():
    """Main export function"""
    print("=" * 70)
    print("🏗️  CONSTRUCTION SCIENCE RESULTS EXPORT")
    print("=" * 70)
    
    # Export all data
    events = export_events()
    entities = export_entities()
    relationships = export_event_entities()
    sources = export_sources()
    
    # Write metadata
    meta = write_run_meta(events, entities, relationships, sources)
    
    # Summary
    print("\n📊 EXPORT SUMMARY:")
    print(f"   Events: {len(events)}")
    print(f"   Entities: {len(entities)}")
    print(f"   Relationships: {len(relationships)}")
    print(f"   Sources: {len(sources)}")
    
    print("\n🏗️  Entity Type Breakdown:")
    for entity_type, count in meta["entity_type_breakdown"].items():
        print(f"   {entity_type}: {count}")
    
    print("\n📈 Top 5 Entities by Event Count:")
    for i, entity in enumerate(meta["top_entities"][:5], 1):
        print(f"   {i}. {entity['name']} ({entity['type']}) - {entity['event_count']} events, {entity['paper_count']} papers")
    
    print("\n🎯 Top 5 Events by Confidence:")
    for i, event in enumerate(meta["top_events"][:5], 1):
        print(f"   {i}. Event {event['event_id']} - {event['confidence']} confidence")
        outcome = event['outcome'] or ""
        if outcome and len(outcome) > 80:
            print(f"      Outcome: {outcome[:80]}...")
        elif outcome:
            print(f"      Outcome: {outcome}")
        else:
            print("      Outcome: <empty>")
    
    print("\n✅ All exports completed successfully!")
    print(f"📁 Output directory: {OUTPUT_DIR.absolute()}")
    print("📋 Files created:")
    print("   - events_export_construction_science.csv")
    print("   - construction_entities.csv")
    print("   - construction_event_entities.csv")
    print("   - construction_sources.csv")
    print("   - run_meta_construction_science.json")

if __name__ == "__main__":
    main()