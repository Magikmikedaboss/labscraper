"""
CSV Export v4 - Professional Polish
- Reclassifies process-words as tags (not primary entities)
- Adds safe confidence boost rule
- Adds entity count columns
- Generates run_meta.json for reproducibility
"""

import sqlite3
import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from entity_normalizer import load_normalization_map, normalize_entity_list

DB_PATH = Path("output") / "peptide_intel.sqlite"
OUTPUT_DIR = Path("output")

# Process words that should be tags, not primary assay entities
PROCESS_WORDS_TO_DEMOTE = {
    "quantification", "quantitation", "chromatography", "purification",
    "calibration", "validation", "optimization", "quality control"
}

def is_process_word(entity_name: str) -> bool:
    """Check if entity is a process word that should be demoted to tag"""
    return entity_name.lower() in PROCESS_WORDS_TO_DEMOTE

def safe_confidence_boost(entities_str: str, current_conf: str) -> str:
    """
    Safe confidence promotion rule:
    Promote to HIGH if event has:
    - (compound OR target OR stem_cell) AND
    - assay AND
    - model context (in vivo/in vitro/human/rat/plasma/serum)
    
    This is objective, not subjective.
    """
    if current_conf == "high":
        return "high"  # Already high
    
    if not entities_str:
        return current_conf
    
    # Parse entities
    entities = entities_str.split("; ") if entities_str else []
    entity_types = set()
    entity_names_lower = set()
    
    for e in entities:
        if ":" in e:
            etype, ename = e.split(":", 1)
            entity_types.add(etype.lower())
            entity_names_lower.add(ename.lower())
    
    # Check for high-value entity (compound, target, or stem_cell)
    has_high_value = bool(entity_types & {"compound", "target", "stem_cell"})
    
    # Check for assay
    has_assay = "assay" in entity_types
    
    # Check for model context
    model_context_terms = {
        "in vivo", "in vitro", "human", "rat", "mouse", "plasma", "serum",
        "blood", "tissue", "cell culture", "fbs"
    }
    has_model_context = bool(entity_names_lower & model_context_terms)
    
    # Promote if all three conditions met
    if has_high_value and has_assay and has_model_context:
        return "high"
    
    # Promote to med if has high-value entity + assay (even without model context)
    if has_high_value and has_assay and current_conf == "low":
        return "med"
    
    return current_conf

def count_entities_by_role(entities_str: str, norm_map: dict) -> tuple:
    """
    Count primary and context entities in a semicolon-separated string.
    Also demotes process words to tags.
    Returns: (primary_count, context_count, primary_str, context_str, all_str)
    """
    if not entities_str:
        return (0, 0, "", "", "")
    
    # Parse entities
    entity_pairs = [e.split(':', 1) for e in entities_str.split('; ') if ':' in e]
    entity_dicts = [
        {"entity_type": etype, "entity_name": ename}
        for etype, ename in entity_pairs
    ]
    
    # Normalize
    normalized = normalize_entity_list(entity_dicts, norm_map)
    
    # Separate by role, demoting process words
    primary = []
    context = []
    
    for e in normalized:
        # Demote process words to context
        if e['entity_type'] == 'assay' and is_process_word(e['entity_name']):
            e['role'] = 'context'  # Override role
        
        entity_str = f"{e['entity_type']}:{e['entity_name']}"
        
        if e['role'] == 'primary':
            primary.append(entity_str)
        else:
            context.append(entity_str)
    
    primary_str = "; ".join(primary) if primary else ""
    context_str = "; ".join(context) if context else ""
    all_str = "; ".join([f"{e['entity_type']}:{e['entity_name']}" for e in normalized])
    
    return (len(primary), len(context), primary_str, context_str, all_str)

def export_events_professional():
    """Export events with professional polish"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    norm_map = load_normalization_map()
    
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
        GROUP BY re.event_id
        ORDER BY re.created_at DESC
    """).fetchall()
    
    # Export with enhancements
    events_path = OUTPUT_DIR / "events_export_v4.csv"
    with open(events_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'event_id', 'domain', 'event_type', 'stage', 'outcome',
            'decision_driver', 'evidence_snippet', 'confidence_original', 'confidence_boosted',
            'primary_entity_count', 'context_entity_count',
            'entities_primary', 'entities_context', 'entities_all',
            'paper_id', 'created_at'
        ])
        
        confidence_changes = {"low": 0, "med": 0, "high": 0, "boosted_to_high": 0, "boosted_to_med": 0}
        
        for event in events:
            event_id, domain, etype, stage, outcome, decision, snippet, conf_orig, source_id, created_at, entities_str = event
            
            # Count entities and separate by role
            primary_count, context_count, primary_str, context_str, all_str = count_entities_by_role(entities_str, norm_map)
            
            # Apply safe confidence boost
            conf_boosted = safe_confidence_boost(all_str, conf_orig)
            
            # Track changes
            confidence_changes[conf_boosted] += 1
            if conf_orig != conf_boosted:
                if conf_boosted == "high":
                    confidence_changes["boosted_to_high"] += 1
                elif conf_boosted == "med":
                    confidence_changes["boosted_to_med"] += 1
            
            writer.writerow([
                event_id, domain, etype, stage, outcome,
                decision, snippet, conf_orig, conf_boosted,
                primary_count, context_count,
                primary_str, context_str, all_str,
                source_id, created_at
            ])
    
    con.close()
    
    print(f"✅ Exported professional events: {len(events)} → {events_path}")
    print(f"\n📊 Confidence Distribution (After Boost):")
    print(f"   High: {confidence_changes['high']} ({confidence_changes['high']/len(events)*100:.1f}%)")
    print(f"   Med: {confidence_changes['med']} ({confidence_changes['med']/len(events)*100:.1f}%)")
    print(f"   Low: {confidence_changes['low']} ({confidence_changes['low']/len(events)*100:.1f}%)")
    print(f"\n🚀 Confidence Boosts Applied:")
    print(f"   Boosted to HIGH: {confidence_changes['boosted_to_high']}")
    print(f"   Boosted to MED: {confidence_changes['boosted_to_med']}")
    
    return confidence_changes

def export_candidates_professional():
    """Export candidates with process words demoted"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    norm_map = load_normalization_map()
    
    # Get all entities
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
    
    # Normalize and aggregate
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
        entity_dict = {
            "entity_type": etype,
            "entity_name": ename,
            "entity_variant": evariant
        }
        
        normalized = normalize_entity_list([entity_dict], norm_map)[0]
        canonical_name = normalized["entity_name"]
        role = normalized["role"]
        
        # Demote process words
        if etype == "assay" and is_process_word(canonical_name):
            role = "context"
        
        key = (etype, canonical_name)
        canonical_entities[key]["entity_type"] = etype
        canonical_entities[key]["entity_variant"] = evariant
        canonical_entities[key]["event_count"] += event_count
        canonical_entities[key]["paper_ids"].update(source_ids.split(",") if source_ids else [])
        canonical_entities[key]["original_names"].add(ename)
        canonical_entities[key]["role"] = role
        
        if canonical_entities[key]["first_seen"] is None or first_seen < canonical_entities[key]["first_seen"]:
            canonical_entities[key]["first_seen"] = first_seen
        if canonical_entities[key]["last_seen"] is None or last_seen > canonical_entities[key]["last_seen"]:
            canonical_entities[key]["last_seen"] = last_seen
    
    # Export primary
    primary_path = OUTPUT_DIR / "candidates_primary_v4.csv"
    with open(primary_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'entity_type', 'entity_name', 'entity_variant', 'role',
            'event_count', 'paper_count', 'original_variants',
            'first_seen', 'last_seen'
        ])
        
        sorted_entities = sorted(
            canonical_entities.items(),
            key=lambda x: x[1]["event_count"],
            reverse=True
        )
        
        for (etype, ename), data in sorted_entities:
            if data["role"] == "primary":
                writer.writerow([
                    etype, ename, data["entity_variant"], data["role"],
                    data["event_count"], len(data["paper_ids"]),
                    "; ".join(sorted(data["original_names"])),
                    data["first_seen"], data["last_seen"]
                ])
    
    con.close()
    
    primary_count = sum(1 for _, data in canonical_entities.items() if data["role"] == "primary")
    context_count = sum(1 for _, data in canonical_entities.items() if data["role"] == "context")
    
    print(f"✅ Exported professional candidates:")
    print(f"   Primary entities: {primary_count} → {primary_path}")
    print(f"   Context entities: {context_count}")
    
    return canonical_entities

def write_run_meta(confidence_changes, canonical_entities):
    """Write run metadata for reproducibility"""
    meta = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "engine_version": "v4_professional",
        "timestamp": datetime.now().isoformat(),
        "database": str(DB_PATH),
        "seeds_version": "2026-01-22",
        "counts": {
            "total_events": confidence_changes["high"] + confidence_changes["med"] + confidence_changes["low"],
            "total_entities": len(canonical_entities),
            "primary_entities": sum(1 for _, data in canonical_entities.items() if data["role"] == "primary"),
            "context_entities": sum(1 for _, data in canonical_entities.items() if data["role"] == "context")
        },
        "confidence_distribution": {
            "high": confidence_changes["high"],
            "med": confidence_changes["med"],
            "low": confidence_changes["low"],
            "boosted_to_high": confidence_changes["boosted_to_high"],
            "boosted_to_med": confidence_changes["boosted_to_med"]
        },
        "top_entities": [
            {
                "name": ename,
                "type": etype,
                "event_count": data["event_count"],
                "role": data["role"]
            }
            for (etype, ename), data in sorted(
                canonical_entities.items(),
                key=lambda x: x[1]["event_count"],
                reverse=True
            )[:20]
        ],
        "process_words_demoted": list(PROCESS_WORDS_TO_DEMOTE),
        "confidence_boost_rule": "HIGH if (compound|target|stem_cell) + assay + model_context; MED if (compound|target|stem_cell) + assay"
    }
    
    meta_path = OUTPUT_DIR / "run_meta.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    
    print(f"✅ Wrote run metadata: {meta_path}")

if __name__ == "__main__":
    print("=" * 70)
    print("CSV EXPORT v4 - PROFESSIONAL POLISH")
    print("=" * 70)
    
    canonical_entities = export_candidates_professional()
    confidence_changes = export_events_professional()
    write_run_meta(confidence_changes, canonical_entities)
    
    print("\n✅ Professional export complete!")
    print("\nKey improvements:")
    print("  ✅ Process words (quantification, chromatography, etc.) demoted to context")
    print("  ✅ Safe confidence boost applied (objective criteria)")
    print("  ✅ Entity count columns added to events")
    print("  ✅ run_meta.json created for reproducibility")
