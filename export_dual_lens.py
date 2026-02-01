"""
Dual-Lens Export - Phase 2
Applies overlay scoring to existing extraction results and exports with dual perspectives
"""

import sqlite3
import csv
import json
from pathlib import Path
from collections import defaultdict
from utils.overlay_scorer import OverlayScorer, load_domain_config


def export_dual_lens(db_path: str, domain_id: str, output_dir: str = "output"):
    """
    Export entities and events with dual-lens overlay scoring

    Args:
        db_path: Path to SQLite database
        domain_id: Domain ID (e.g., 'biohacking_longevity')
        output_dir: Output directory for CSV files
    """

    def normalize_entity_name(name: str) -> str:
        name = name.lower()
        # Simple plural/singular merge for common cases
        if name.endswith('s') and name[:-1] in {"human", "neuron", "mouse", "rat", "astrocyte", "microglia", "organoid"}:
            return name[:-1]
        if name == "humans":
            return "human"
        return name

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
    
    # Connect to database
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found: {db_file}")
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # Step 1: Score all events (filter by domain)
        print("\n📊 Step 1: Scoring events...")
        if domain_id:
            events = cur.execute("SELECT * FROM research_events WHERE research_domain = ?", (domain_id,)).fetchall()
            print(f"   ✅ Filtered to domain '{domain_id}': {len(events)} events")
        else:
            events = cur.execute("SELECT * FROM research_events").fetchall()
            print(f"   ✅ No domain filter applied: {len(events)} events")
        event_overlay_scores = {}  # event_id -> {overlay_id: score}
        for event in events:
            event_dict = dict(event)
            scores = scorer.apply_event_scores(event_dict)
            event_overlay_scores[event['event_id']] = scores
        print(f"   ✅ Scored {len(events)} events")

        # Step 2: Aggregate entity scores per overlay
        print("\n🎯 Step 2: Calculating entity scores per overlay...")
        # Get all entities (filter by domain)
        if domain_id:
            entities = cur.execute("""
                SELECT DISTINCT e.* FROM entities e
                JOIN event_entities ee ON e.entity_id = ee.entity_id
                JOIN research_events re ON ee.event_id = re.event_id
                WHERE re.research_domain = ?
            """, (domain_id,)).fetchall()
            print(f"   ✅ Filtered entities to domain '{domain_id}': {len(entities)} entities")
        else:
            entities = cur.execute("SELECT * FROM entities").fetchall()
            print(f"   ✅ No domain filter applied: {len(entities)} entities")

        # Apply entity type precedence and normalization
        def normalize_entity_type(name: str, entity_type: str) -> str:
            """Apply type precedence rules"""
            name_lower = name.lower()
            # Neural cells
            if name_lower in {
                "microglia", "astrocyte", "neuron", "neurons", "astrocytes",
                "microglial", "neuronal", "astrocytic"
            }:
                return "neural_cell"
            # Stem cells
            if name_lower in {"ipsc", "msc", "esc"}:
                return "stem_cell"
            # Organoids -> model
            if name_lower in {"organoid", "organoids"}:
                return "model"
            return entity_type

        # Normalize entities: merge duplicates by canonical name + type
        entity_canonical = {}  # (canonical_name, canonical_type) -> merged_entity
        entity_id_mapping = {}  # old_entity_id -> canonical_entity_id


        for entity in entities:
            name = entity['entity_name']
            entity_type = entity['entity_type']

            # Apply type precedence
            canonical_type = normalize_entity_type(name, entity_type)

            # Canonicalize name (lowercase, singular/plural merge)
            canonical_name = normalize_entity_name(name)

            key = (canonical_name, canonical_type)

            if key not in entity_canonical:
                # Create new canonical entity
                canonical_entity = dict(entity)
                canonical_entity['entity_name'] = canonical_name  # Use canonical name
                canonical_entity['entity_type'] = canonical_type
                canonical_entity['original_names'] = [name]  # Track original names
                entity_canonical[key] = canonical_entity
            else:
                # Merge into existing canonical entity
                canonical_entity = entity_canonical[key]
                if name not in canonical_entity['original_names']:
                    canonical_entity['original_names'].append(name)

            # Map old entity_id to canonical entity_id
            entity_id_mapping[entity['entity_id']] = entity_canonical[key]['entity_id']

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
    all_final_scores = {overlay_id: [] for overlay_id in overlay_ids}

    # First pass: calculate all scores and collect them for distribution analysis
    for entity in entities:
        entity_id = entity['entity_id']
        event_ids = entity_events.get(entity_id, [])
        models_list = list(entity_models_map.get(entity_id, set()))
        entity_scores[entity_id] = {}
        for overlay_id in overlay_ids:
            event_scores_list = [
                event_overlay_scores.get(eid, {}).get(overlay_id, 0)
                for eid in event_ids
            ]
            entity_dict = dict(entity)
            entity_dict['event_count'] = len(event_ids)
            final_score = scorer.calculate_entity_score(
                entity_dict,
                event_scores_list,
                overlay_id,
                entity_models=models_list
            )
            all_final_scores[overlay_id].append(final_score)
            entity_scores[entity_id][overlay_id] = {'score': final_score}

    # Compute max_score for each overlay from the actual score distribution
    # Use the maximum score observed (could use a percentile for robustness)
    max_scores = {overlay_id: max(scores) if scores else 1 for overlay_id, scores in all_final_scores.items()}

    # Second pass: assign buckets using the computed max_score
    for entity in entities:
        entity_id = entity['entity_id']
        for overlay_id in overlay_ids:
            final_score = entity_scores[entity_id][overlay_id]['score']
            max_score = max_scores[overlay_id]
            # Bucket using distribution-derived max_score (not heuristic)
            bucket = scorer.bucket_score(final_score, max_score)
            entity_scores[entity_id][overlay_id]['bucket'] = bucket

    print(f"   ✅ Calculated scores for {len(entities)} entities")
    
    # Step 3: Export entities with dual-lens columns
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
            
            row = {
                'entity_name': entity['entity_name'],
                'entity_type': entity['entity_type'],
                'entity_variant': entity.get('entity_variant') or '',
                'event_count': event_count
            }            
            # Add overlay scores
            for overlay_id in overlay_ids:
                scores = entity_scores[entity_id][overlay_id]
                row[f'{overlay_id}_score'] = f"{scores['score']:.2f}"
                row[f'{overlay_id}_bucket'] = scores['bucket']
            
            writer.writerow(row)
    
    print(f"   ✅ Exported: {entities_file}")
    
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
    import re

    if len(sys.argv) < 2:
        print("Usage: python export_dual_lens.py <database_path> [domain_id]")
        print("\nExample:")
        print("  python export_dual_lens.py output/biohacking_dual_lens.sqlite biohacking_longevity")
        sys.exit(1)

    db_path = sys.argv[1]
    domain_id = sys.argv[2] if len(sys.argv) > 2 else "biohacking_longevity"

    # Validate domain_id to prevent path traversal
    valid_domain_ids = ['biohacking_longevity', 'drug_discovery', 'methods_tooling', 'neuroscience_cognition', 'stem_cells_regen', 'construction_science']
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
