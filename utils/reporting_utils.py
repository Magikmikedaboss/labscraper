"""Analytics and output utilities for export pipeline"""
import json
import logging
import os
import subprocess  # nosec B404 - controlled git metadata lookup for run metadata
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from utils.process_words import PROCESS_WORDS_TO_DEMOTE
from utils.entity_normalizer import load_normalization_map, normalize_entity
from utils.entity_utils import load_overlay_aliases_safe

def get_overlay_version(domain) -> str:
    """Resolve overlay version from domain object, checking multiple sources in order."""
    if not domain:
        return "v1"
    # Try direct attribute
    version = getattr(domain, 'overlay_version', None)
    if version:
        return version
    # Try metadata dict if present
    if hasattr(domain, 'metadata') and isinstance(domain.metadata, dict):
        version = domain.metadata.get('overlay_version')
        if version:
            return version
    # Try domain_profile_version
    version = getattr(domain, 'domain_profile_version', None)
    if version:
        return version
    return "v1"

def _ensure_set(value):
    if value is None:
        return set()
    if isinstance(value, set):
        return value
    return set(value)

def write_run_meta(confidence_changes: Dict[str, int], canonical_entities: Dict[Tuple[str, str], Dict[str, Any]], 
                  domain_id: Optional[str] = None, output_dir: Path = Path("output"), suffix: str = "") -> None:
    """Write run metadata for reproducibility"""
    overlay_aliases = load_overlay_aliases_safe(domain_id) if domain_id else {}
    overlay_aliases_count = len(overlay_aliases)
    try:
        norm_map = load_normalization_map()
    except Exception as e:
        norm_map = {}
        logging.warning("Failed to load normalization map; proceeding with empty map: %s", e, exc_info=True)
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
        "seeds_version": resolve_seeds_version(),
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
        "normalization_map": norm_map,
        "process_words_demoted": list(PROCESS_WORDS_TO_DEMOTE),
        "confidence_boost_rule": "Domain-specific: construction_science uses (material|system|failure_mode|environment|hazard) + assay + model_context; biomedical domains use (compound|target|stem_cell) + assay + model_context"
    }
    target_dir = output_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    meta_path = target_dir / f"run_meta{suffix}.json"

    def convert_sets(obj):
        if isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        if isinstance(obj, set):
            return sorted(obj)
        if isinstance(obj, list):
            return [convert_sets(v) for v in obj]
        return obj

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(convert_sets(meta), f, indent=2)
    print(f"✅ Wrote run metadata: {meta_path}")

# Module-level, testable seeds version resolver
def resolve_seeds_version(run_cmd=None):
    """
    Resolve the SEEDS version string from environment, config, or git.
    run_cmd: Optional callable for running the git command (for test injection).
    """
    env_version = os.environ.get("SEEDS_VERSION")
    if env_version:
        return env_version
    # 2. Config fallback (add here if you have a config module)
    # try:
    #     import config
    #     if hasattr(config, "SEEDS_VERSION"):
    #         return config.SEEDS_VERSION
    # except ImportError:
    #     pass
    # 3. Git tag/commit fallback
    if run_cmd is None:
        run_cmd = subprocess.check_output
    try:
        version = run_cmd([
            "git", "describe", "--tags", "--always"
        ], stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
        if version:
            return version
    except subprocess.TimeoutExpired:
        # Optionally log timeout here
        pass
    except Exception:
        pass  # nosec B110 - best-effort git metadata lookup falls back to "unknown"
    return "unknown"

def get_domain_info(domain_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
    from utils.axon_domains import get_domain_by_id
    domain = get_domain_by_id(domain_id) if domain_id else None
    domain_name = domain.name if domain else "All Domains"
    return domain_name, getattr(domain, 'overlay_id', None)
