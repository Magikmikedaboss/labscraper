"""
CSV Export v5 - Domain-Aware with Overlay Support
"""

import sqlite3
import csv
import argparse
import logging
from pathlib import Path
from collections import defaultdict
from utils.entity_normalizer import load_normalization_map, load_overlay_aliases, normalize_entity, get_entity_role
from utils.process_words import is_process_word
from utils.path_validation import validate_domain_id

DB_PATH = Path("db") / "runs.sqlite"
OUTPUT_DIR = Path("output")
LATEST_DIR = Path("exports") / "latest"
ENTITY_VARIANT_DELIM = "|||"
logger = logging.getLogger(__name__)



def export_candidates_domain_aware(domain_id: str = None):
    if domain_id:
        domain_id = validate_domain_id(domain_id)

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
                # canonical_name is currently just entity_name; if normalization/aliasing is added, update here
                entities_data = cur.execute("""
                    SELECT 
                        MIN(e.entity_id) as entity_id,
                        e.entity_type,
                        e.entity_name as canonical_name,
                        (
                            SELECT GROUP_CONCAT(v.entity_variant, '|||')
                            FROM (
                                SELECT DISTINCT e2.entity_variant AS entity_variant
                                FROM entities e2
                                JOIN event_entities ee2 ON e2.entity_id = ee2.entity_id
                                JOIN research_events re2 ON ee2.event_id = re2.event_id
                                WHERE re2.research_domain = ?
                                  AND e2.entity_type = e.entity_type
                                  AND e2.entity_name = e.entity_name
                                  AND e2.entity_variant IS NOT NULL
                                  AND TRIM(e2.entity_variant) <> ''
                            ) v
                        ) as entity_variant,
                        COUNT(DISTINCT ee.event_id) as event_count,
                        GROUP_CONCAT(DISTINCT re.source_id) as source_ids
                    FROM entities e
                    JOIN event_entities ee ON e.entity_id = ee.entity_id
                    JOIN research_events re ON ee.event_id = re.event_id
                    WHERE re.research_domain = ?
                    GROUP BY e.entity_type, e.entity_name
                    ORDER BY event_count DESC
                """, (domain_id, domain_id)).fetchall()
        else:
            entities_data = cur.execute("""
                SELECT 
                    e.entity_id,
                    e.entity_type,
                    e.entity_name,
                    e.entity_variant,
                    COUNT(DISTINCT ee.event_id) as event_count,
                    GROUP_CONCAT(DISTINCT re.source_id) as source_ids
                FROM entities e
                JOIN event_entities ee ON e.entity_id = ee.entity_id
                JOIN research_events re ON ee.event_id = re.event_id
                GROUP BY e.entity_id
                ORDER BY event_count DESC
            """).fetchall()
        canonical_entities = defaultdict(lambda: {
            "entity_type": None,
            "entity_variant": set(),
            "event_count": 0,
            "paper_ids": set(),
            "original_names": set(),
            "role": None
        })

        for entity_id, etype, ename, evariant, event_count, source_ids in entities_data:
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
            # Domain query uses a custom delimiter to preserve commas in values.
            if evariant:
                if domain_id:
                    raw_fragments = evariant.split(ENTITY_VARIANT_DELIM)
                    trimmed_fragments = [fragment.strip() for fragment in raw_fragments]
                    has_empty_fragment = any(not fragment for fragment in trimmed_fragments)
                    rejoined = ENTITY_VARIANT_DELIM.join(trimmed_fragments)
                    if has_empty_fragment:
                        logger.warning(
                            "Malformed entity_variant split for key=%s: original=%r normalized=%r",
                            key,
                            evariant,
                            rejoined,
                        )
                    variants = [fragment for fragment in trimmed_fragments if fragment]
                else:
                    variants = [evariant.strip()]
                for v in variants:
                    canonical_entities[key]["entity_variant"].add(v)
            # Use event_count directly (it's an integer)
            if event_count:
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
            for (etype, canonical_name), data in canonical_entities.items():
                variant_str = ','.join(sorted(data["entity_variant"])) if data["entity_variant"] else ''
                writer.writerow([
                    canonical_name,
                    etype,
                    variant_str,
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
    print("✅ Export complete!")