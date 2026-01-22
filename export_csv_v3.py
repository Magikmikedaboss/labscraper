"""
CSV Export v3 - With Entity Normalization

Exports research events and candidates with:
- Entity normalization (variants → canonical forms)
- Context entity demotion (in vivo, serum, etc.)
- Primary entities ranked separately from context entities

Usage:
    python export_csv_v3.py
"""

import sqlite3
import csv
from pathlib import Path
from collections import defaultdict
from entity_normalizer import load_normalization_map, normalize_entity_list, get_primary_entities

DB_PATH = Path("output") / "peptide_intel.sqlite"
OUTPUT_DIR = Path("output")

def export_candidates_with_normalization():
    """Export candidates with normalized entity names and role classification"""
    
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # Load normalization map
    norm_map = load_normalization_map()
    
    # Get all entities with their event counts
    entities_data = cur.execute("""
        SELECT 
            e.entity_id,
            e.entity_type,
            e.entity_name,
            e.entity_variant,
            COUNT(DISTINCT ee.event_id) as event_count,
            GROUP_CONCAT(DISTINCT re.source_id) as source_ids,
            MIN(re.created_at) as first_seen,
            MAX(re.created_at) as last_seen
        FROM entities e
        JOIN event_entities ee ON e.entity_id = ee.entity_id
        JOIN research_events re ON ee.event_id = re.event_id
        GROUP BY e.entity_id
        ORDER BY event_count DESC
    """).fetchall()
    
    # Normalize entities and aggregate by canonical name
    canonical_entities = defaultdict(lambda: {
        "entity_type": None,
        "entity_variant": None,
        "event_count": 0,
        "paper_ids": set(),
        "first_seen": None,
        "last_seen": None,
        "original_names": set(),
        "role": None
    })
    
    for entity_id, etype, ename, evariant, event_count, source_ids, first_seen, last_seen in entities_data:
        # Normalize entity
        entity_dict = {
            "entity_type": etype,
            "entity_name": ename,
            "entity_variant": evariant
        }
        
        normalized = normalize_entity_list([entity_dict], norm_map)[0]
        canonical_name = normalized["entity_name"]
        role = normalized["role"]
        
        # Aggregate by canonical name
        key = (etype, canonical_name)
        canonical_entities[key]["entity_type"] = etype
        canonical_entities[key]["entity_variant"] = evariant
        canonical_entities[key]["event_count"] += event_count
        canonical_entities[key]["paper_ids"].update(source_ids.split(",") if source_ids else [])
        canonical_entities[key]["original_names"].add(ename)
        canonical_entities[key]["role"] = role
        
        # Track earliest/latest
        if canonical_entities[key]["first_seen"] is None or first_seen < canonical_entities[key]["first_seen"]:
            canonical_entities[key]["first_seen"] = first_seen
        if canonical_entities[key]["last_seen"] is None or last_seen > canonical_entities[key]["last_seen"]:
            canonical_entities[key]["last_seen"] = last_seen
    
    # Export primary entities (for rankings)
    primary_path = OUTPUT_DIR / "candidates_primary.csv"
    with open(primary_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'entity_type', 'entity_name', 'entity_variant', 'role',
            'event_count', 'paper_count', 'original_variants',
            'first_seen', 'last_seen'
        ])
        
        # Sort by event count
        sorted_entities = sorted(
            canonical_entities.items(),
            key=lambda x: x[1]["event_count"],
            reverse=True
        )
        
        for (etype, ename), data in sorted_entities:
            if data["role"] == "primary":
                writer.writerow([
                    etype,
                    ename,
                    data["entity_variant"],
                    data["role"],
                    data["event_count"],
                    len(data["paper_ids"]),
                    "; ".join(sorted(data["original_names"])),
                    data["first_seen"],
                    data["last_seen"]
                ])
    
    # Export context entities (for filters)
    context_path = OUTPUT_DIR / "candidates_context.csv"
    with open(context_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'entity_type', 'entity_name', 'entity_variant', 'role',
            'event_count', 'paper_count', 'original_variants',
            'first_seen', 'last_seen'
        ])
        
        for (etype, ename), data in sorted_entities:
            if data["role"] == "context":
                writer.writerow([
                    etype,
                    ename,
                    data["entity_variant"],
                    data["role"],
                    data["event_count"],
                    len(data["paper_ids"]),
                    "; ".join(sorted(data["original_names"])),
                    data["first_seen"],
                    data["last_seen"]
                ])
    
    # Export all entities (combined)
    all_path = OUTPUT_DIR / "candidates_export_v3.csv"
    with open(all_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'entity_type', 'entity_name', 'entity_variant', 'role',
            'event_count', 'paper_count', 'original_variants',
            'first_seen', 'last_seen'
        ])
        
        for (etype, ename), data in sorted_entities:
            writer.writerow([
                etype,
                ename,
                data["entity_variant"],
                data["role"],
                data["event_count"],
                len(data["paper_ids"]),
                "; ".join(sorted(data["original_names"])),
                data["first_seen"],
                data["last_seen"]
            ])
    
    con.close()
    
    # Print summary
    primary_count = sum(1 for _, data in canonical_entities.items() if data["role"] == "primary")
    context_count = sum(1 for _, data in canonical_entities.items() if data["role"] == "context")
    
    print(f"✅ Exported normalized candidates:")
    print(f"   Primary entities: {primary_count} → {primary_path}")
    print(f"   Context entities: {context_count} → {context_path}")
    print(f"   All entities: {len(canonical_entities)} → {all_path}")
    
    return canonical_entities


def export_events_with_normalization():
    """Export events with normalized entity names"""
    
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # Load normalization map
    norm_map = load_normalization_map()
    
    # Get all events with their entities
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
        GROUP BY re.event_id
        ORDER BY re.created_at DESC
    """).fetchall()
    
    # Export events
    events_path = OUTPUT_DIR / "events_export_v3.csv"
    with open(events_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'event_id', 'domain', 'event_type', 'stage', 'outcome',
            'decision_driver', 'evidence_snippet', 'confidence',
            'entities_primary', 'entities_context', 'entities_all',
            'paper_id', 'created_at'
        ])
        
        for event in events:
            event_id, domain, etype, stage, outcome, decision, snippet, conf, source_id, created_at, entities_str = event
            
            # Parse and normalize entities
            if entities_str:
                entity_pairs = [e.split(':', 1) for e in entities_str.split('; ') if ':' in e]
                entity_dicts = [
                    {"entity_type": etype, "entity_name": ename}
                    for etype, ename in entity_pairs
                ]
                
                normalized = normalize_entity_list(entity_dicts, norm_map)
                
                # Separate primary and context
                primary = [f"{e['entity_type']}:{e['entity_name']}" for e in normalized if e['role'] == 'primary']
                context = [f"{e['entity_type']}:{e['entity_name']}" for e in normalized if e['role'] == 'context']
                all_entities = [f"{e['entity_type']}:{e['entity_name']}" for e in normalized]
                
                entities_primary = "; ".join(primary) if primary else ""
                entities_context = "; ".join(context) if context else ""
                entities_all = "; ".join(all_entities) if all_entities else ""
            else:
                entities_primary = ""
                entities_context = ""
                entities_all = ""
            
            writer.writerow([
                event_id, domain, etype, stage, outcome,
                decision, snippet, conf,
                entities_primary, entities_context, entities_all,
                source_id, created_at
            ])
    
    con.close()
    
    print(f"✅ Exported normalized events: {len(events)} → {events_path}")


def print_top_entities(canonical_entities):
    """Print top entities by role"""
    
    print("\n" + "=" * 70)
    print("TOP ENTITIES (NORMALIZED)")
    print("=" * 70)
    
    # Primary entities
    print("\n⭐ PRIMARY ENTITIES (for rankings):")
    primary = [(k, v) for k, v in canonical_entities.items() if v["role"] == "primary"]
    primary_sorted = sorted(primary, key=lambda x: x[1]["event_count"], reverse=True)
    
    for i, ((etype, ename), data) in enumerate(primary_sorted[:20], 1):
        variants = data["original_names"]
        variant_str = f" [{', '.join(sorted(variants))}]" if len(variants) > 1 else ""
        print(f"   {i:2d}. {ename} ({etype}): {data['event_count']} events{variant_str}")
    
    # Context entities
    print("\n🔧 CONTEXT ENTITIES (for filters only):")
    context = [(k, v) for k, v in canonical_entities.items() if v["role"] == "context"]
    context_sorted = sorted(context, key=lambda x: x[1]["event_count"], reverse=True)
    
    for i, ((etype, ename), data) in enumerate(context_sorted[:10], 1):
        variants = data["original_names"]
        variant_str = f" [{', '.join(sorted(variants))}]" if len(variants) > 1 else ""
        print(f"   {i:2d}. {ename} ({etype}): {data['event_count']} events{variant_str}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("=" * 70)
    print("CSV EXPORT v3 - With Entity Normalization")
    print("=" * 70)
    
    canonical_entities = export_candidates_with_normalization()
    export_events_with_normalization()
    print_top_entities(canonical_entities)
    
    print("\n✅ Export complete!")
    print("\nFiles created:")
    print("   - candidates_primary.csv (for rankings/dashboards)")
    print("   - candidates_context.csv (for filters only)")
    print("   - candidates_export_v3.csv (all entities)")
    print("   - events_export_v3.csv (with normalized entities)")
