#!/usr/bin/env python3
"""
Export construction science results from db/runs.sqlite
"""

import sqlite3
import csv
from pathlib import Path

DB_PATH = Path("db/runs.sqlite")
OUTPUT_DIR = Path("output")
DOMAIN_ID = "construction_science"


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def ensure_db_exists():
    if not DB_PATH.exists():
        print(f"❌ Database file not found: {DB_PATH}")
        raise SystemExit(1)




# ---------------------------------------------------------
# EXPORT EVENTS
# ---------------------------------------------------------
def export_events():
    print("🏗️  Exporting construction science events...")
    ensure_db_exists()

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

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


# ---------------------------------------------------------
# EXPORT ENTITIES
# ---------------------------------------------------------
def export_entities():
    print("🏗️  Exporting construction science entities...")
    ensure_db_exists()

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

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


# ---------------------------------------------------------
# EXPORT RELATIONSHIPS
# ---------------------------------------------------------
def export_event_entities():
    print("🏗️  Exporting event-entity relationships...")
    ensure_db_exists()

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

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


if __name__ == "__main__":
    ensure_db_exists()
    events = export_events()
    entities = export_entities()
    relationships = export_event_entities()
    print(
        f"Summary: events={len(events)}, entities={len(entities)}, event_entities={len(relationships)}"
    )