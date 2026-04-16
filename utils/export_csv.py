"""
CSV Export v5 - Domain-Aware with Overlay Support
"""

import sqlite3
import csv
import argparse
from pathlib import Path
from collections import defaultdict
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from entity_normalizer import load_normalization_map, load_overlay_aliases, normalize_entity, get_entity_role
from process_words import is_process_word
from export_utilities import write_run_meta

DB_PATH = Path("db") / "runs.sqlite"
OUTPUT_DIR = Path("output")
LATEST_DIR = Path("exports") / "latest"



def export_candidates_domain_aware(domain_id: str = None):
    norm_map = load_normalization_map()
    overlay_aliases = load_overlay_aliases(domain_id) if domain_id else {}


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
                        MIN(e.entity_id) as entity_id,
                        e.entity_type,
                        n.entity_name as canonical_name,
                        GROUP_CONCAT(DISTINCT e.entity_variant) as entity_variant,
                        COUNT(DISTINCT ee.event_id) as event_count,
                        GROUP_CONCAT(DISTINCT re.source_id) as source_ids,
                        MIN(re.created_at) as first_seen,
                        MAX(re.created_at) as last_seen
                    FROM entities e
                    JOIN event_entities ee ON e.entity_id = ee.entity_id
                    JOIN research_events re ON ee.event_id = re.event_id
                    JOIN (
                        SELECT entity_type, entity_name
                        FROM entities
                    ) n ON n.entity_type = e.entity_type AND n.entity_name = e.entity_name
                    WHERE re.research_domain = ?
                    GROUP BY e.entity_type, n.entity_name
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
        # Sanitize domain_id to prevent path traversal or unsafe values
        import re
        from pathlib import PurePath
        if os.path.isabs(domain_id) or len(PurePath(domain_id).parts) > 1 or '..' in domain_id or not re.match(r'^[A-Za-z0-9_-]+$', domain_id):
            raise ValueError(f"Invalid domain_id: {domain_id}")
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





if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", type=str, required=True)
    args = parser.parse_args()

    canonical_entities = export_candidates_domain_aware(args.domain)
    # Compute real confidence_changes from canonical_entities (placeholder: use actual counters if available)
    confidence_changes = {"high": 0, "med": 0, "low": 0, "boosted_to_high": 0, "boosted_to_med": 0}
    # TODO: Replace with actual confidence counters from event export path if available
    for data in canonical_entities.values():
        if data.get("event_count", 0) > 10:
            confidence_changes["high"] += 1
        elif data.get("event_count", 0) > 5:
            confidence_changes["med"] += 1
        elif data.get("event_count", 0) > 0:
            confidence_changes["low"] += 1
    write_run_meta(confidence_changes, canonical_entities, args.domain)

    print("✅ Export complete!")