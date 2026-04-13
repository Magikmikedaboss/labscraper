"""
CSV Export v5 - Domain-Aware with Overlay Support
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

DB_PATH = Path("db") / "runs.sqlite"
OUTPUT_DIR = Path("output")
LATEST_DIR = Path("exports") / "latest"



def export_candidates_domain_aware(domain_id: str = None):
    norm_map = load_normalization_map()
    overlay_aliases = load_overlay_aliases(domain_id) if domain_id else {}

    domain = get_domain_by_id(domain_id) if domain_id else None
    domain_name = domain.name if domain else "All Domains"
    overlay_id = f"{domain_id}_v1" if domain_id else None

    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()

        if domain_id:
            event_count = cur.execute(
                "SELECT COUNT(*) FROM research_events WHERE research_domain = ?",
                (domain_id,),
            ).fetchone()[0]

            if event_count == 0:
                entities_data = []
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
            """).fetchall()  # ✅ FIXED HERE

        canonical_entities = defaultdict(lambda: {
            "entity_type": None,
            "entity_variant": None,
            "event_count": 0,
            "paper_ids": set(),
            "original_names": set(),
            "role": None
        })

        for entity_id, etype, ename, evariant, event_count, source_ids, first_seen, last_seen in entities_data:
            entity_dict = {
                "entity_type": etype,
                "entity_name": ename,
                "entity_variant": evariant
            }

            normalized = normalize_entity(entity_dict, norm_map, overlay_aliases)
            canonical_name = normalized["entity_name"]
            role = get_entity_role(normalized, norm_map)

            if etype == "assay" and is_process_word(canonical_name):
                role = "context"

            key = (etype, canonical_name)
            canonical_entities[key]["entity_type"] = etype
            canonical_entities[key]["entity_variant"] = evariant
            canonical_entities[key]["event_count"] += event_count
            canonical_entities[key]["paper_ids"].update(source_ids.split(",") if source_ids else [])
            canonical_entities[key]["original_names"].add(ename)
            canonical_entities[key]["role"] = role

    # Write to exports/latest/<domain>/entities.csv if domain_id is given
    if domain_id:
        latest_dir = LATEST_DIR / domain_id
        latest_dir.mkdir(parents=True, exist_ok=True)
        entities_path = latest_dir / "entities.csv"
        with open(entities_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['entity_name', 'entity_type', 'entity_variant', 'event_count'])
            # Only write rows if there are any entities
            for (etype, ename), data in canonical_entities.items():
                writer.writerow([
                    ename,
                    etype,
                    data["entity_variant"] if data["entity_variant"] else '',
                    data["event_count"]
                ])
        print(f"✅ Wrote filtered entities: {entities_path}")
    print("✅ Exported domain-aware candidates")
    return canonical_entities


def write_run_meta(confidence_changes, canonical_entities, domain_id=None):

    # Compute v5 fields
    engine_version = "v5_domain_aware"
    # Dummy confidence distribution for compatibility; real values should be computed if available
    confidence_distribution = {
        "high": 0,
        "med": 0,
        "low": 0,
        "boosted_to_high": 0,
        "boosted_to_med": 0
    }
    # Top entities by event count (if available)
    top_entities = []
    for (etype, ename), data in sorted(canonical_entities.items(), key=lambda x: x[1]["event_count"], reverse=True)[:20]:
        top_entities.append({
            "name": ename,
            "type": etype,
            "event_count": data["event_count"],
            "role": data["role"]
        })
    # Dummy process_words_demoted and confidence_boost_rule for compatibility
    process_words_demoted = []
    confidence_boost_rule = None

    meta = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "engine_version": engine_version,
        "timestamp": datetime.now().isoformat(),
        "database": str(DB_PATH.as_posix()),
        "domain_id": domain_id,
        "domain_name": None,
        "overlay_id": None,
        "overlay_aliases_count": 0,
        "counts": {
            "total_entities": len(canonical_entities)
        },
        "confidence_distribution": confidence_distribution,
        "top_entities": top_entities,
        "process_words_demoted": process_words_demoted,
        "confidence_boost_rule": confidence_boost_rule,
        "confidence_changes": confidence_changes if confidence_changes else None
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    meta_path = OUTPUT_DIR / "run_meta.json"

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"✅ Wrote run metadata: {meta_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", type=str)
    args = parser.parse_args()

    canonical_entities = export_candidates_domain_aware(args.domain)
    # TODO: confidence_changes is currently unimplemented; passing {} for now. Update this argument and the confidence_changes parameter in write_run_meta when confidence tracking is added.
    write_run_meta({}, canonical_entities, args.domain)

    print("✅ Export complete!")