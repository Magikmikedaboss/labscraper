"""
Analytics and output utilities for export pipeline
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Any, Optional
from utils.entity_utils import load_overlay_aliases_safe
from process_words import PROCESS_WORDS_TO_DEMOTE

def _ensure_set(value):
    if value is None:
        return set()
    if isinstance(value, set):
        return value
    return set(value)

def write_run_meta(confidence_changes: Dict[str, int], canonical_entities: Dict[Tuple[str, str], Dict[str, Any]], 
                  domain_id: str = None, output_dir: Path = Path("output"), suffix: str = "") -> None:
    """Write run metadata for reproducibility"""
    from axon_domains import get_domain_by_id
    from entity_normalizer import load_normalization_map, normalize_entity
    domain = get_domain_by_id(domain_id) if domain_id else None
    overlay_id = f"{domain_id}_v1" if domain_id else None
    overlay_aliases = load_overlay_aliases_safe(domain_id) if domain_id else {}
    overlay_aliases_count = len(overlay_aliases)
    norm_map = load_normalization_map()
    normalized_entities = {}
    for (etype, ename), data in canonical_entities.items():
        norm_e = normalize_entity({"entity_type": etype, "entity_name": ename}, norm_map, overlay_aliases)
        canonical_name = norm_e["entity_name"]
        key = (etype, canonical_name)
        if key not in normalized_entities:
            normalized_entities[key] = {
                **data,
                "entity_name": canonical_name,
                "paper_ids": _ensure_set(data.get("paper_ids")),
                "original_names": _ensure_set(data.get("original_names")),
            }
        else:
            normalized_entities[key]["event_count"] += data["event_count"]
            normalized_entities[key]["paper_ids"] = _ensure_set(normalized_entities[key].get("paper_ids"))
            data_paper_ids = _ensure_set(data.get("paper_ids"))
            normalized_entities[key]["paper_ids"].update(data_paper_ids)
            normalized_entities[key]["original_names"] = _ensure_set(normalized_entities[key].get("original_names"))
            data_original_names = _ensure_set(data.get("original_names"))
            normalized_entities[key]["original_names"].update(data_original_names)
    for ent in normalized_entities.values():
        if isinstance(ent.get("paper_ids"), set):
            ent["paper_ids"] = list(ent["paper_ids"])
        if isinstance(ent.get("original_names"), set):
            ent["original_names"] = list(ent["original_names"])
    now = datetime.now()
    meta = {
        "run_id": now.strftime("%Y%m%d_%H%M%S"),
        "engine_version": "v5_domain_aware",
        "timestamp": now.isoformat(),
        "seeds_version": "2026-01-22",
        "domain_id": domain_id or None,
        "domain_name": domain.name if domain else "All Domains",
        "overlay_id": overlay_id,
        "overlay_aliases_count": overlay_aliases_count,
        "counts": {
            "total_events": confidence_changes.get("high", 0) + confidence_changes.get("med", 0) + confidence_changes.get("low", 0) + confidence_changes.get("other", 0),
            "total_entities": len(normalized_entities),
            "primary_entities": sum(1 for _, data in normalized_entities.items() if data["role"] == "primary"),
            "context_entities": sum(1 for _, data in normalized_entities.items() if data["role"] == "context")
        },
        "confidence_distribution": {
            "high": confidence_changes.get("high", 0),
            "med": confidence_changes.get("med", 0),
            "low": confidence_changes.get("low", 0),
            "boosted_to_high": confidence_changes.get("boosted_to_high", 0),
            "boosted_to_med": confidence_changes.get("boosted_to_med", 0),
            "other": confidence_changes.get("other", 0)
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
    meta_path = output_dir / f"run_meta{suffix}.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    print(f"✅ Wrote run metadata: {meta_path}")

def get_domain_info(domain_id: str = None) -> Tuple[str, Optional[str]]:
    from axon_domains import get_domain_by_id
    domain = get_domain_by_id(domain_id) if domain_id else None
    domain_name = domain.name if domain else "All Domains"
    overlay_id = f"{domain_id}_v1" if domain_id else None
    return domain_name, overlay_id
