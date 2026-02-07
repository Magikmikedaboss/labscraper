"""
CSV Export v5 - Domain-Aware with Overlay Support
- All v4 features (process words demoted, confidence boost, entity counts, run_meta)
- NEW: Supports domain_id and overlay_id columns
- NEW: Uses overlay aliases for normalization (MSC→mesenchymal stem cell)
- NEW: Tracks which lens was used for each export
"""

import sqlite3
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from entity_normalizer import load_normalization_map, load_overlay_aliases, normalize_entity, get_entity_role
from axon_domains import get_domain_by_id
from process_words import PROCESS_WORDS_TO_DEMOTE, is_process_word
from export_utilities import safe_confidence_boost, count_entities_by_role

DB_PATH = Path("runs") / "peptide_intel.sqlite"
OUTPUT_DIR = Path("output")

def export_events_domain_aware(domain_id: str = None):
    """Export events with domain awareness"""
    norm_map = load_normalization_map()
    overlay_aliases = load_overlay_aliases(domain_id) if domain_id else {}
    
    # Get domain info
    domain = get_domain_by_id(domain_id) if domain_id else None
    domain_name = domain.name if domain else "All Domains"
    overlay_id = f"{domain_id}_v1" if domain_id else None
    
    # Use context manager for database connection
    with sqlite3.connect(DB_PATH) as con:
        con.execute("PRAGMA foreign_keys = ON;")
        cur = con.cursor()
        
        # Get all events (with optional domain filter)
        if domain_id:
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
            """, (domain_id,)).fetchall()
        else:
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
    
    # Export with enhancements (outside DB context)
    suffix = f"_{domain_id}" if domain_id else "_v5"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events_path = OUTPUT_DIR / f"events_export{suffix}.csv"
    with open(events_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'event_id', 'domain', 'event_type', 'stage', 'outcome',
            'decision_driver', 'evidence_snippet', 'confidence_original', 'confidence_boosted',
            'primary_entity_count', 'context_entity_count',
            'entities_primary', 'entities_context', 'entities_all',
            'domain_id', 'domain_name', 'overlay_id',
            'paper_id', 'created_at'
        ])
        
        confidence_changes = {"low": 0, "med": 0, "high": 0, "other": 0, "boosted_to_high": 0, "boosted_to_med": 0}
        
        for event in events:
            event_id, domain_col, etype, stage, outcome, decision, snippet, conf_orig, source_id, created_at, entities_str = event

            # Count entities and separate by role (with overlay aliases)
            primary_count, context_count, primary_str, context_str, all_str = count_entities_by_role(
                entities_str, norm_map, overlay_aliases
            )

            # Apply safe confidence boost
            conf_boosted = safe_confidence_boost(all_str, conf_orig, domain_id)

            # Normalize for fair comparison
            conf_orig_norm = str(conf_orig).strip().lower() if conf_orig is not None else ''
            conf_boosted_norm = str(conf_boosted).strip().lower() if conf_boosted is not None else ''

            # Track changes
            if conf_boosted_norm in confidence_changes:
                confidence_changes[conf_boosted_norm] += 1
            else:
                confidence_changes["other"] += 1

            if conf_orig_norm != conf_boosted_norm:
                if conf_boosted_norm == "high":
                    confidence_changes["boosted_to_high"] += 1
                elif conf_boosted_norm == "med":
                    confidence_changes["boosted_to_med"] += 1

            writer.writerow([
                event_id, domain_col, etype, stage, outcome,
                decision, snippet, conf_orig, conf_boosted,
                primary_count, context_count,
                primary_str, context_str, all_str,
                domain_id or "", domain_name, overlay_id or "",
                source_id, created_at
            ])
    
    print(f"✅ Exported domain-aware events: {len(events)} → {events_path}")
    if domain_id and overlay_aliases:
        print(f"   Domain: {domain_name}")
        print(f"   Overlay: {overlay_id}")
        print(f"   Aliases used: {len(overlay_aliases)}")
        # Show a sample of actual aliases used
        sample_aliases = list(overlay_aliases.items())[:3]
        alias_samples = [f"{k}→{v}" for k, v in sample_aliases]
        print(f"   Sample aliases: {', '.join(alias_samples)}...")
    elif domain_id:
        print(f"   Domain: {domain_name}")
        print(f"   Overlay: {overlay_id}")
        print("   Aliases used: 0 (no overlay aliases found)")
    
    # Safe percentage calculation
    if len(events) > 0:
        print("\n📊 Confidence Distribution (After Boost):")
        print(f"   High: {confidence_changes['high']} ({confidence_changes['high']/len(events)*100:.1f}%)")
        print(f"   Med: {confidence_changes['med']} ({confidence_changes['med']/len(events)*100:.1f}%)")
        print(f"   Low: {confidence_changes['low']} ({confidence_changes['low']/len(events)*100:.1f}%)")
    
    print("\n🚀 Confidence Boosts Applied:")
    print(f"   Boosted to HIGH: {confidence_changes['boosted_to_high']}")
    print(f"   Boosted to MED: {confidence_changes['boosted_to_med']}")
    
    return confidence_changes

def export_candidates_domain_aware(domain_id: str = None):
    """Export candidates with domain awareness and overlay aliases"""
    norm_map = load_normalization_map()
    overlay_aliases = load_overlay_aliases(domain_id) if domain_id else {}
    
    # Get domain info
    domain = get_domain_by_id(domain_id) if domain_id else None
    domain_name = domain.name if domain else "All Domains"
    overlay_id = f"{domain_id}_v1" if domain_id else None
    
    # Use context manager for database connection
    with sqlite3.connect(DB_PATH) as con:
        con.execute("PRAGMA foreign_keys = ON;")
        cur = con.cursor()
        
        # Get all entities (with optional domain filter)
        if domain_id:
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
                WHERE re.research_domain = ?
                GROUP BY e.entity_id
                ORDER BY event_count DESC
            """, (domain_id,)).fetchall()
        else:
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
        
        # Normalize and aggregate (with overlay aliases) - inside context
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
            
            # Normalize with overlay aliases
            normalized = normalize_entity(entity_dict, norm_map, overlay_aliases)
            canonical_name = normalized["entity_name"]
            role = get_entity_role(normalized, norm_map)
            
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
    
    # Export primary (outside DB context)
    suffix = f"_{domain_id}" if domain_id else "_v5"
    primary_path = OUTPUT_DIR / f"candidates_primary{suffix}.csv"
    with open(primary_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'entity_type', 'entity_name', 'entity_variant', 'role',
            'event_count', 'paper_count', 'original_variants',
            'domain_id', 'domain_name', 'overlay_id',
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
                    domain_id or "", domain_name, overlay_id or "",
                    data["first_seen"], data["last_seen"]
                ])
    
    primary_count = sum(1 for _, data in canonical_entities.items() if data["role"] == "primary")
    context_count = sum(1 for _, data in canonical_entities.items() if data["role"] == "context")
    
    print("✅ Exported domain-aware candidates:")
    print(f"   Primary entities: {primary_count} → {primary_path}")
    print(f"   Context entities: {context_count}")
    if domain_id:
        print(f"   Domain: {domain_name}")
        print(f"   Overlay: {overlay_id}")
    
    return canonical_entities

def write_run_meta(confidence_changes, canonical_entities, domain_id=None):
    """Write run metadata for reproducibility"""
    domain = get_domain_by_id(domain_id) if domain_id else None
    overlay_id = f"{domain_id}_v1" if domain_id else None
    
    # Ensure overlay aliases are loaded and applied for normalization
    overlay_aliases = load_overlay_aliases(domain_id) if domain_id else {}
    overlay_aliases_count = len(overlay_aliases)

    # Re-normalize canonical_entities with overlay aliases if not already
    norm_map = load_normalization_map()
    normalized_entities = {}
    for (etype, ename), data in canonical_entities.items():
        norm_e = normalize_entity({"entity_type": etype, "entity_name": ename}, norm_map, overlay_aliases)
        canonical_name = norm_e["entity_name"]
        key = (etype, canonical_name)
        if key not in normalized_entities:
            # Deep copy with new sets for mutable fields
            normalized_entities[key] = {
                **data,
                "entity_name": canonical_name,
                "paper_ids": set(data["paper_ids"]) if "paper_ids" in data else set(),
                "original_names": set(data["original_names"]) if "original_names" in data else set(),
            }
        else:
            # Merge event counts and paper_ids if duplicate after normalization
            normalized_entities[key]["event_count"] += data["event_count"]
            if not isinstance(normalized_entities[key]["paper_ids"], set):
                normalized_entities[key]["paper_ids"] = set(normalized_entities[key]["paper_ids"])
            if not isinstance(data["paper_ids"], set):
                data_paper_ids = set(data["paper_ids"])
            else:
                data_paper_ids = data["paper_ids"]
            normalized_entities[key]["paper_ids"].update(data_paper_ids)
            if not isinstance(normalized_entities[key]["original_names"], set):
                normalized_entities[key]["original_names"] = set(normalized_entities[key]["original_names"])
            if not isinstance(data["original_names"], set):
                data_original_names = set(data["original_names"])
            else:
                data_original_names = data["original_names"]
            normalized_entities[key]["original_names"].update(data_original_names)

    # Convert set-valued fields to lists for JSON serialization
    for ent in normalized_entities.values():
        if isinstance(ent.get("paper_ids"), set):
            ent["paper_ids"] = list(ent["paper_ids"])
        if isinstance(ent.get("original_names"), set):
            ent["original_names"] = list(ent["original_names"])

    meta = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "engine_version": "v5_domain_aware",
        "timestamp": datetime.now().isoformat(),
        "database": str(DB_PATH.as_posix()),
        "seeds_version": "2026-01-22",
        "domain_id": domain_id or None,
        "domain_name": domain.name if domain else "All Domains",
        "overlay_id": overlay_id,
        "overlay_aliases_count": overlay_aliases_count,
        "counts": {
            "total_events": confidence_changes["high"] + confidence_changes["med"] + confidence_changes["low"] + confidence_changes.get("other", 0),
            "total_entities": len(normalized_entities),
            "primary_entities": sum(1 for _, data in normalized_entities.items() if data["role"] == "primary"),
            "context_entities": sum(1 for _, data in normalized_entities.items() if data["role"] == "context")
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
                "name": data["entity_name"],
                "type": etype,
                "event_count": data["event_count"],
                "role": data["role"]
            }
            for (etype, _), data in sorted(
                normalized_entities.items(),
                key=lambda x: x[1]["event_count"],
                reverse=True
            )[:20]
        ],
        "process_words_demoted": list(PROCESS_WORDS_TO_DEMOTE),
        "confidence_boost_rule": "Domain-specific: construction_science uses (material|system|failure_mode|environment|hazard) + assay + model_context; biomedical domains use (compound|target|stem_cell) + assay + model_context"
    }
    
    suffix = f"_{domain_id}" if domain_id else "_v5"
    meta_path = OUTPUT_DIR / f"run_meta{suffix}.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    
    print(f"✅ Wrote run metadata: {meta_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export CSV with domain awareness")
    parser.add_argument("--domain", type=str, help="Domain ID (stem_cells_regen, neuroscience_cognition, biohacking_longevity)")
    args = parser.parse_args()
    
    print("=" * 70)
    print("CSV EXPORT v5 - DOMAIN-AWARE WITH OVERLAY SUPPORT")
    print("=" * 70)
    
    if args.domain:
        print(f"\n🔍 Using domain: {args.domain}")
        domain = get_domain_by_id(args.domain)
        if domain:
            print(f"   Name: {domain.name}")
            print(f"   Description: {domain.description[:80]}...")
        else:
            print("   ⚠️  Domain not found, proceeding without domain filter")
            args.domain = None
    else:
        print("\n📊 Exporting all domains (no filter)")
    
    canonical_entities = export_candidates_domain_aware(args.domain)
    confidence_changes = export_events_domain_aware(args.domain)
    write_run_meta(confidence_changes, canonical_entities, args.domain)
    
    print("\n✅ Domain-aware export complete!")
    print("\nKey features:")
    print("  ✅ Domain ID and overlay ID columns added")
    if args.domain:
        overlay_aliases = load_overlay_aliases(args.domain)
        if overlay_aliases:
            print(f"  ✅ Overlay aliases used for normalization ({len(overlay_aliases)} aliases)")
            # Show a sample of actual aliases used
            sample_aliases = list(overlay_aliases.items())[:3]
            alias_samples = [f"{k}→{v}" for k, v in sample_aliases]
            print(f"     Sample: {', '.join(alias_samples)}...")
        else:
            print("  ✅ Overlay aliases used for normalization (0 aliases - no domain overlay)")
    else:
        print("  ✅ Overlay aliases used for normalization (no domain filter)")
    print("  ✅ Process words demoted to context")
    print("  ✅ Safe confidence boost applied")
    print("  ✅ Entity count columns included")
    print("  ✅ run_meta.json tracks which lens was used")
