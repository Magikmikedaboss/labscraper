"""
Analytics and output utilities for export pipeline
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Any, Optional
from utils.entity_utils import load_overlay_aliases_safe
from utils.process_words import PROCESS_WORDS_TO_DEMOTE

def _ensure_set(value):
    if value is None:
        return set()
    if isinstance(value, set):
        return value
    return set(value)

def write_run_meta(confidence_changes: Dict[str, int], canonical_entities: Dict[Tuple[str, str], Dict[str, Any]], 
                  domain_id: Optional[str] = None, output_dir: Path = Path("output"), suffix: str = "") -> None:
    """Write run metadata for reproducibility"""
    from utils.entity_normalizer import load_normalization_map, normalize_entity
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
            ent = normalized_entities[key]
            ent.setdefault("event_count", 0)
            ent.setdefault("paper_ids", set())
            ent.setdefault("original_names", set())
            ent["event_count"] += data.get("event_count", 0)
            data_paper_ids = _ensure_set(data.get("paper_ids"))
            ent["paper_ids"].update(data_paper_ids)
            data_original_names = _ensure_set(data.get("original_names"))
            ent["original_names"].update(data_original_names)
    for ent in normalized_entities.values():
        if isinstance(ent.get("paper_ids"), set):
            ent["paper_ids"] = list(ent["paper_ids"])
        if isinstance(ent.get("original_names"), set):
            ent["original_names"] = list(ent["original_names"])
    # Use get_domain_info to get domain_name and overlay_id
    domain_name, overlay_id = get_domain_info(domain_id)
    now = datetime.now()
    meta = {
        "run_id": now.strftime("%Y%m%d_%H%M%S"),
        "engine_version": "v5_domain_aware",
        "timestamp": now.isoformat(),
        "seeds_version": "2026-01-22",
        "domain_id": domain_id,
        "domain_name": domain_name,
        "overlay_id": overlay_id,
        "overlay_aliases_count": overlay_aliases_count,
        "counts": {
            "total_events": confidence_changes.get("high", 0) + confidence_changes.get("med", 0) + confidence_changes.get("low", 0) + confidence_changes.get("other", 0),
            "total_entities": len(normalized_entities),
            "primary_entities": sum(1 for _, data in normalized_entities.items() if data.get("role") == "primary"),
            "context_entities": sum(1 for _, data in normalized_entities.items() if data.get("role") == "context")
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
                "name": data.get("entity_name", ""),
                "type": etype,
                "event_count": data.get("event_count", 0),
                "role": data.get("role", None)
            }
            for (etype, _), data in sorted(
                normalized_entities.items(),
                key=lambda x: x[1].get("event_count", 0),
                reverse=True
            )[:20]
        ],
        "process_words_demoted": list(PROCESS_WORDS_TO_DEMOTE),
        "confidence_boost_rule": "Domain-specific: construction_science uses (material|system|failure_mode|environment|hazard) + assay + model_context; biomedical domains use (compound|target|stem_cell) + assay + model_context"
    }
    # Keep exports under an "output" folder for consistency with tests and tooling.
    target_dir = output_dir / "output" if output_dir.name != "output" else output_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    meta_path = target_dir / f"run_meta{suffix}.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    print(f"✅ Wrote run metadata: {meta_path}")

def get_domain_info(domain_id: str = None) -> Tuple[str, Optional[str]]:
    from utils.axon_domains import get_domain_by_id
    domain = get_domain_by_id(domain_id) if domain_id else None
    domain_name = domain.name if domain else "All Domains"
    overlay_id = f"{domain_id}_v1" if domain_id else None
    return domain_name, overlay_id