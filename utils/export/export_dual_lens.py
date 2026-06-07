#!/usr/bin/env python3
"""
Dual-Lens Export - Phase 2
Applies overlay scoring to existing extraction results and exports
with dual perspectives.
"""

import logging
import os
import sys
from functools import lru_cache
from pathlib import Path

from utils.export.filters import should_skip_entity, should_suppress_entity_for_csv
from utils.export.normalization import build_canonical_entities
from utils.export.aggregation import (
    load_events_and_entities,
    build_event_overlay_scores,
    build_entity_event_map,
    build_event_models,
    build_entity_models_map,
    build_entity_scores,
)
from utils.export.reporting import (
    export_entities_csv,
    publish_latest_entities,
    export_events_csv,
    publish_latest_events,
    write_dual_lens_report,
)
from utils.overlay_scorer import OverlayScorer, load_domain_config
from utils.path_validation import validate_domain_id
from utils.entity_normalizer import (
    load_normalization_map,
    load_overlay_aliases,
    normalize_entity,
    get_entity_role,
)
from utils.axon_domains import load_all_domains


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_valid_domain_ids() -> frozenset[str]:
    domains_dir = Path(__file__).resolve().parents[2] / "config" / "domains"
    if not domains_dir.exists() or not domains_dir.is_dir():
        logger.warning("Domain profiles directory missing: %s", domains_dir)
        return frozenset()
    try:
        domains = load_all_domains(str(domains_dir))
    except Exception as exc:
        logger.error("Failed to load domain profiles from %s: %s", domains_dir, exc)
        raise RuntimeError(f"Failed to load domain profiles from {domains_dir}") from exc
    return frozenset(domains.keys())

def _is_special_db_identifier(db_path) -> bool:
    db_path_str = os.fspath(db_path)
    return db_path_str == ":memory:" or db_path_str.startswith(("file:", "sqlite://"))


def _validate_known_domain_id(domain_id: str) -> str:
    safe_domain_id = validate_domain_id(domain_id)
    valid_domain_ids = _get_valid_domain_ids()
    if safe_domain_id not in valid_domain_ids:
        raise ValueError(
            f"Invalid domain_id: {safe_domain_id}. Valid domains: {', '.join(sorted(valid_domain_ids))}"
        )
    return safe_domain_id

def export_dual_lens(db_path, domain_id="construction_science", output_dir="exports"):
    print("\n" + "=" * 70)
    print("DUAL-LENS EXPORT - PHASE 2")
    print("=" * 70)

    domain_id = _validate_known_domain_id(domain_id)
    db_path = os.fspath(db_path)

    if _is_special_db_identifier(db_path):
        db_path_obj = None
    else:
        db_path_obj = Path(db_path)
        if not db_path_obj.exists() or not db_path_obj.is_file():
            raise FileNotFoundError(f"Database file not found on disk: {db_path_obj}")
        db_path = str(db_path_obj)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    domain_config = load_domain_config(domain_id)
    scorer = OverlayScorer(domain_config)

    if not scorer.is_dual_lens():
        print("⚠️  Dual-lens mode not enabled in domain config")
        return

    overlay_ids = scorer.get_overlay_ids()
    print(f"\n📋 Overlays: {', '.join(overlay_ids)}")

    norm_map = load_normalization_map()
    overlay_aliases = load_overlay_aliases(domain_id)

    print("\n📊 Step 1: Loading and scoring events...")
    try:
        events, entities, event_entities, model_rows = load_events_and_entities(db_path)
    except Exception as e:
        raise RuntimeError(f"Failed loading export input data from {db_path}: {e}") from e
    event_overlay_scores = build_event_overlay_scores(events, scorer)
    print(f"   ✅ Scored {len(events)} events")

    print("\n🎯 Step 2: Normalizing entities...")
    canonical_entities, entity_id_mapping = build_canonical_entities(
        entities=entities,
        domain_id=domain_id,
        norm_map=norm_map,
        overlay_aliases=overlay_aliases,
        normalize_entity=normalize_entity,
        get_entity_role=get_entity_role,
        should_skip_entity=should_skip_entity,
    )
    print(f"   ✅ Canonical entities: {len(canonical_entities)}")

    print("\n🧩 Step 3: Building relationships...")
    entity_events = build_entity_event_map(event_entities, entity_id_mapping)
    event_models = build_event_models(model_rows)
    entity_models_map = build_entity_models_map(entity_events, event_models)

    print("\n🧠 Step 4: Scoring entities...")
    entity_scores = build_entity_scores(
        entities=canonical_entities,
        overlay_ids=overlay_ids,
        entity_events=entity_events,
        entity_models_map=entity_models_map,
        event_overlay_scores=event_overlay_scores,
        scorer=scorer,
    )
    print(f"   ✅ Calculated scores for {len(canonical_entities)} entities")

    print("\n📝 Step 5: Exporting entities CSV...")
    entities_file, filtered_entities = export_entities_csv(
        entities=canonical_entities,
        entity_events=entity_events,
        entity_scores=entity_scores,
        overlay_ids=overlay_ids,
        domain_id=domain_id,
        output_path=output_path,
        should_suppress_entity_for_csv=should_suppress_entity_for_csv,
    )
    print(f"   ✅ Exported: {entities_file}")

    latest_entities_file, publish_error = publish_latest_entities(entities_file, domain_id)
    if publish_error:
        print(f"   ❌ Failed to atomically publish latest dual-lens entities: {publish_error}")
    else:
        print(f"   ↳ Published latest dual-lens entities: {latest_entities_file}")

    print("\n📝 Step 6: Exporting events CSV...")

    events_file = export_events_csv(
        events=events,
        event_overlay_scores=event_overlay_scores,
        overlay_ids=overlay_ids,
        domain_id=domain_id,
        output_path=output_path,
    )
    print(f"   ✅ Exported: {events_file}")

    latest_events_file, publish_error = publish_latest_events(events_file, domain_id)
    if publish_error:
        print(f"   ❌ Failed to atomically publish latest dual-lens events: {publish_error}")
    else:
        print(f"   ↳ Published latest dual-lens events: {latest_events_file}")

    print("\n📊 Step 7: Generating comparison report...")
    report_file = output_path / f"dual_lens_report_{domain_id}.txt"
    write_dual_lens_report(
        report_file=report_file,
        domain_config=domain_config,
        overlay_ids=overlay_ids,
        events=events,
        entities=canonical_entities,
        filtered_entities=filtered_entities,
        entity_scores=entity_scores,
        entity_events=entity_events,
    )
    print(f"   ✅ Report: {report_file}")

    print("\n" + "=" * 70)
    print("✅ DUAL-LENS EXPORT COMPLETE")
    print("=" * 70)
    print("\nOutput files:")
    print(f"  📊 {entities_file}")
    print(f"  📋 {events_file}")
    print(f"  📄 {report_file}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python export_dual_lens.py <database_path> [domain_id]")
        print("\nExample:")
        print("  python export_dual_lens.py db/runs.sqlite construction_science")
        sys.exit(1)

    db_path = sys.argv[1]
    domain_id = sys.argv[2] if len(sys.argv) > 2 else "construction_science"

    try:
        domain_id = _validate_known_domain_id(domain_id)
    except ValueError:
        print(f"❌ Invalid domain_id: {domain_id}")
        print(f"Valid domains: {', '.join(sorted(_get_valid_domain_ids()))}")
        sys.exit(1)


    export_dual_lens(db_path, domain_id)
