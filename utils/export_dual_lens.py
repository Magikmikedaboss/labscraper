"""
Dual-Lens Export - Phase 2
Applies overlay scoring to existing extraction results and exports with dual perspectives
"""

import sqlite3
from contextlib import closing
import csv
import re
import shutil
from pathlib import Path
from collections import defaultdict
from .overlay_scorer import OverlayScorer, load_domain_config

try:
    from .entity_normalizer import load_normalization_map, load_overlay_aliases, normalize_entity, get_entity_role
except ImportError:
    from entity_normalizer import load_normalization_map, load_overlay_aliases, normalize_entity, get_entity_role


def export_dual_lens(db_path: str, domain_id: str, output_dir: str = "output"):
    """
    Export entities and events with dual-lens overlay scoring
    
    Args:
        db_path: Path to SQLite database
        domain_id: Domain ID (e.g., 'biohacking_longevity')
        output_dir: Output directory for CSV files
    """
    
    print("\n" + "="*70)
    print("DUAL-LENS EXPORT - PHASE 2")
    print("="*70)
    
    # Load domain config and initialize scorer
    domain_config = load_domain_config(domain_id)
    scorer = OverlayScorer(domain_config)
    
    if not scorer.is_dual_lens():
        print("⚠️  Dual-lens mode not enabled in domain config")
        return
    
    overlay_ids = scorer.get_overlay_ids()
    print(f"\n📋 Overlays: {', '.join(overlay_ids)}")

    norm_map = load_normalization_map()
    overlay_aliases = load_overlay_aliases(domain_id)

    def is_valid_export_peptide(name: str) -> bool:
        """Filter obvious OCR/noise artifacts from peptide exports."""
        token = (name or "").strip()
        if not token:
            return False
        # Keep canonical peptide sequences only when they are explicitly uppercase.
        if re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]{8,100}", token):
            return True
        known = {
            "ETELCALCETIDE", "PLECANATIDE", "TERIPARATIDE", "OCTREOTIDE",
            "LANREOTIDE", "PASIREOTIDE", "SOMATOSTATIN"
        }
        return token.upper() in known
    
    # Connect to database and perform all DB operations; ensure connection is closed explicitly
    events = []
    with closing(sqlite3.connect(db_path)) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        # Step 1: Score all events
        print("\n📊 Step 1: Scoring events...")
        events = cur.execute("SELECT * FROM research_events").fetchall()

        event_overlay_scores = {}  # event_id -> {overlay_id: score}

        for event in events:
            event_dict = dict(event)
            scores = scorer.apply_event_scores(event_dict)
            event_overlay_scores[event['event_id']] = scores

        print(f"   ✅ Scored {len(events)} events")

        # Step 2: Aggregate entity scores per overlay
        print("\n🎯 Step 2: Calculating entity scores per overlay...")

        # Get all entities
        entities = cur.execute("SELECT * FROM entities").fetchall()

        # Apply entity type precedence and normalization
        def normalize_entity_type(name: str, entity_type: str) -> str:
            """Apply type precedence rules"""
            name_lower = name.lower()
            if name_lower in {"microglia", "astrocyte", "neuron", "neurons", "astrocytes", "microglial", "neuronal", "astrocytic"}:
                return "neural_cell"
            if name_lower in {"ipsc", "msc", "esc"}:
                return "stem_cell"
            if name_lower in {"organoid", "organoids"}:
                return "model"
            if domain_id == "construction_science":
                if name_lower in {"ice", "water", "air", "moisture", "humidity", "temperature", "heat", "cold", "frost", "snow", "vapor", "climate", "weather", "acoustic", "sound", "thaw", "freeze"}:
                    return "environment"
                if name_lower in {"corrosion", "fire", "wind", "seismic", "earthquake", "flood", "storm", "lightning", "tornado", "impact", "cold"}:
                    return "hazard"
                if name_lower in {"steel", "concrete", "wood", "glass", "brick", "masonry", "plastic", "polymer", "composite", "aluminum", "copper", "board", "insulation", "panel", "coating", "timber"}:
                    return "material"
                if name_lower in {"structure", "building", "foundation", "roof", "wall", "floor", "frame", "assembly", "component", "door", "ventilation", "building envelope", "column", "heating", "cooling", "mechanical", "electrical"}:
                    return "system"
                if name_lower in {"failure", "collapse", "crack", "fracture", "buckling", "deflection", "deformation", "leakage", "damage", "rot", "deterioration", "weathering", "decay", "expansion", "creep", "shrinkage"}:
                    return "failure_mode"
                if name_lower in {"test", "method", "guideline", "standard", "procedure", "protocol", "assay", "approach", "practice", "technique", "specification", "requirement", "code", "strategy"}:
                    return "test_method"
            return entity_type

        # Normalize entities: merge duplicates by canonical name + type
        entity_canonical = {}  # (canonical_name, canonical_type) -> merged_entity
        entity_id_mapping = {}  # old_entity_id -> canonical_entity_id

        for entity in entities:
            name = entity['entity_name']
            entity_type = entity['entity_type']

            canonical_type = normalize_entity_type(name, entity_type)
            normalized = normalize_entity(
                {"entity_type": canonical_type, "entity_name": name},
                norm_map,
                overlay_aliases,
            )
            canonical_name = normalized["entity_name"].strip()
            canonical_key = canonical_name.lower()

            # Filter noisy peptide artifacts and context-only entities from ranking exports.
            if canonical_type == "peptide" and not is_valid_export_peptide(canonical_name):
                continue
            if get_entity_role({"entity_type": canonical_type, "entity_name": canonical_name}, norm_map) == "context":
                continue

            key = (canonical_key, canonical_type)

            if key not in entity_canonical:
                canonical_entity = dict(entity)
                canonical_entity['entity_id'] = str(key)
                canonical_entity['entity_name'] = canonical_name
                canonical_entity['entity_type'] = canonical_type
                canonical_entity['original_names'] = [name]
                entity_canonical[key] = canonical_entity
            else:
                canonical_entity = entity_canonical[key]
                if name not in canonical_entity['original_names']:
                    canonical_entity['original_names'].append(name)

            entity_id_mapping[entity['entity_id']] = str(key)

        # Update entities list to use canonical entities
        entities = list(entity_canonical.values())

        # Get entity-event relationships
        entity_events = defaultdict(list)  # entity_id -> [event_ids]

        for row in cur.execute("SELECT entity_id, event_id FROM event_entities"):
            # Map to canonical entity_id
            canonical_id = entity_id_mapping.get(row['entity_id'], row['entity_id'])
            entity_events[canonical_id].append(row['event_id'])

        # Extract models from events for model weighting
        # Get all entities of type 'model' linked to each event
        event_models = defaultdict(set)  # event_id -> set of model names

        for row in cur.execute("""
            SELECT ee.event_id, e.entity_name, e.entity_type
            FROM event_entities ee
            JOIN entities e ON ee.entity_id = e.entity_id
            WHERE e.entity_type = 'model'
        """):
            event_models[row['event_id']].add(row['entity_name'])

        # Build entity -> models mapping (models mentioned in entity's events)
        entity_models_map = defaultdict(set)  # entity_id -> set of model names

        for entity_id, event_ids in entity_events.items():
            for event_id in event_ids:
                entity_models_map[entity_id].update(event_models.get(event_id, set()))

        # Calculate scores for each entity in each overlay
        entity_scores = {}  # entity_id -> {overlay_id: {score, bucket}}

        for entity in entities:
            entity_id = entity['entity_id']
            event_ids = entity_events.get(entity_id, [])

            # Get models associated with this entity
            models_list = list(entity_models_map.get(entity_id, set()))

            entity_scores[entity_id] = {}

            for overlay_id in overlay_ids:
                # Get event scores for this entity in this overlay
                event_scores_list = [
                    event_overlay_scores.get(eid, {}).get(overlay_id, 0)
                    for eid in event_ids
                ]

                # Calculate final score WITH model weighting
                entity_dict = dict(entity)
                entity_dict['event_count'] = len(event_ids)

                final_score = scorer.calculate_entity_score(
                    entity_dict,
                    event_scores_list,
                    overlay_id,
                    entity_models=models_list  # Pass models for weighting
                )

                # Determine bucket
                max_score = max(len(event_ids) * 2, 10)  # Rough max estimate
                bucket = scorer.bucket_score(final_score, max_score)

                entity_scores[entity_id][overlay_id] = {
                    'score': final_score,
                    'bucket': bucket
                }

        print(f"   ✅ Calculated scores for {len(entities)} entities")
    
    # No explicit con.close() needed; handled by context manager
    
    print("\n📝 Step 3: Exporting entities CSV...")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    entities_file = output_path / f"entities_dual_lens_{domain_id}.csv"
    
    with open(entities_file, 'w', newline='', encoding='utf-8') as f:
        # Build column headers
        base_cols = ['entity_name', 'entity_type', 'entity_variant', 'event_count']
        
        overlay_cols = []
        for overlay_id in overlay_ids:
            overlay_cols.extend([
                f'{overlay_id}_score',
                f'{overlay_id}_bucket'
            ])
        
        all_cols = base_cols + overlay_cols
        
        writer = csv.DictWriter(f, fieldnames=all_cols)
        writer.writeheader()
        
        for entity in entities:
            entity_id = entity['entity_id']
            event_count = len(entity_events.get(entity_id, []))

            # Suppress single-mention peptide artifacts that are typically OCR/token noise.
            if entity['entity_type'] == 'peptide' and event_count < 2:
                continue

            row = {
                'entity_name': entity['entity_name'],
                'entity_type': entity['entity_type'],
                'entity_variant': entity['entity_variant'] or '',
                'event_count': event_count
            }
            
            # Add overlay scores
            for overlay_id in overlay_ids:
                scores = entity_scores[entity_id][overlay_id]
                row[f'{overlay_id}_score'] = f"{scores['score']:.2f}"
                row[f'{overlay_id}_bucket'] = scores['bucket']
            
            writer.writerow(row)
    
    print(f"   ✅ Exported: {entities_file}")

    latest_dir = Path("exports") / "latest" / domain_id
    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_entities_file = latest_dir / "entities.csv"
    shutil.copyfile(entities_file, latest_entities_file)
    print(f"   ↳ Published latest entities: {latest_entities_file}")
    
    # Step 4: Export events with overlay scores
    print("\n📝 Step 4: Exporting events CSV...")
    
    events_file = output_path / f"events_dual_lens_{domain_id}.csv"
    
    with open(events_file, 'w', newline='', encoding='utf-8') as f:
        base_cols = ['event_id', 'event_type', 'stage', 'confidence_original', 'evidence_snippet']
        
        overlay_cols = []
        for overlay_id in overlay_ids:
            overlay_cols.append(f'{overlay_id}_score')
        
        all_cols = base_cols + overlay_cols
        
        writer = csv.DictWriter(f, fieldnames=all_cols)
        writer.writeheader()
        
        for event in events:
            event_id = event['event_id']
            
            row = {
                'event_id': event_id,
                'event_type': event['event_type'],
                'stage': event['study_stage'] or '',
                'confidence_original': event['confidence'],
                'evidence_snippet': (event['evidence_snippet'] or '')[:200]
            }
            
            # Add overlay scores
            for overlay_id in overlay_ids:
                score = event_overlay_scores[event_id].get(overlay_id, 0)
                row[f'{overlay_id}_score'] = f"{score:+.1f}"
            
            writer.writerow(row)
    
    print(f"   ✅ Exported: {events_file}")

    latest_events_file = latest_dir / "events_dual_lens.csv"
    shutil.copyfile(events_file, latest_events_file)
    print(f"   ↳ Published latest dual-lens events: {latest_events_file}")
    
    # Step 5: Generate comparison report
    print("\n📊 Step 5: Generating comparison report...")
    
    report_file = output_path / f"dual_lens_report_{domain_id}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("DUAL-LENS ANALYSIS REPORT\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Domain: {domain_config['name']}\n")
        f.write(f"Overlays: {', '.join(overlay_ids)}\n")
        f.write(f"Total Events: {len(events)}\n")
        f.write(f"Total Entities: {len(entities)}\n\n")
        
        # Top entities per overlay
        for overlay_id in overlay_ids:
            f.write("="*70 + "\n")
            f.write(f"TOP 20 ENTITIES - {overlay_id.upper()}\n")
            f.write("="*70 + "\n\n")
            
            # Sort entities by this overlay's score
            sorted_entities = sorted(
                entities,
                key=lambda e: entity_scores[e['entity_id']][overlay_id]['score'],
                reverse=True
            )
            
            for i, entity in enumerate(sorted_entities[:20], 1):
                entity_id = entity['entity_id']
                scores = entity_scores[entity_id][overlay_id]
                event_count = len(entity_events.get(entity_id, []))
                
                f.write(f"{i:2d}. {entity['entity_name']:30s} ")
                f.write(f"({entity['entity_type']:12s}) ")
                f.write(f"Score: {scores['score']:6.2f} ")
                f.write(f"[{scores['bucket']:15s}] ")
                f.write(f"Events: {event_count:3d}\n")
            
            f.write("\n")
        
        # Bucket distribution per overlay
        f.write("="*70 + "\n")
        f.write("BUCKET DISTRIBUTION\n")
        f.write("="*70 + "\n\n")
        
        for overlay_id in overlay_ids:
            f.write(f"{overlay_id}:\n")
            
            bucket_counts = defaultdict(int)
            for entity_id in entity_scores:
                bucket = entity_scores[entity_id][overlay_id]['bucket']
                bucket_counts[bucket] += 1
            
            for bucket in ['strong', 'promising', 'exploratory', 'stalled', 'deprioritized']:
                count = bucket_counts.get(bucket, 0)
                pct = (count / len(entities) * 100) if entities else 0
                f.write(f"  {bucket:15s}: {count:4d} ({pct:5.1f}%)\n")
            
            f.write("\n")
    
    print(f"   ✅ Report: {report_file}")
    
    # Database operations complete; connection handled by context manager above    
    print("\n" + "="*70)
    print("✅ DUAL-LENS EXPORT COMPLETE")
    print("="*70)
    print("\nOutput files:")
    print(f"  📊 {entities_file}")
    print(f"  📋 {events_file}")
    print(f"  📄 {report_file}")
    print()



if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python export_dual_lens.py <database_path> [domain_id]")
        print("\nExample:")
        print("  python export_dual_lens.py output/biohacking_dual_lens.sqlite biohacking_longevity")
        sys.exit(1)

    db_path = sys.argv[1]
    domain_id = sys.argv[2] if len(sys.argv) > 2 else "biohacking_longevity"

    # Validate domain_id to prevent path traversal
    valid_domain_ids = [
        'biohacking_longevity',
        'drug_discovery',
        'methods_tooling',
        'neuroscience_cognition',
        'stem_cells_regen',
        'peptide',  # legacy / peptide intelligence pipeline
        'construction_science',
    ]
    if domain_id not in valid_domain_ids:
        print(f"❌ Invalid domain_id: {domain_id}")
        print(f"Valid domains: {', '.join(valid_domain_ids)}")
        sys.exit(1)

    # Additional safety check: ensure domain_id contains only safe characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', domain_id):
        print(f"❌ Invalid domain_id format: {domain_id}")
        print("Domain ID must contain only letters, numbers, underscores, and hyphens")
        sys.exit(1)

    export_dual_lens(db_path, domain_id)
