"""
Shared utilities for CSV export modules
- safe_confidence_boost: Safe confidence promotion rule
- count_entities_by_role: Count primary and context entities with process word demotion
- write_run_meta: Write run metadata for reproducibility
"""

import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple, Any, Optional, Set, List

# Import required modules
try:
    from .entity_normalizer import load_normalization_map, normalize_entity, get_entity_role
    from .axon_domains import get_domain_by_id
    from .process_words import PROCESS_WORDS_TO_DEMOTE, is_process_word
except ImportError:
    # Fallback for direct execution
    from entity_normalizer import load_normalization_map, normalize_entity, get_entity_role
    from axon_domains import get_domain_by_id
    from process_words import PROCESS_WORDS_TO_DEMOTE, is_process_word

def safe_confidence_boost(entities_str: str, current_conf: str, domain_id: str = None) -> str:
    """
    Safe confidence promotion rule:
    Promote to HIGH if event has:
    - (domain-relevant entities) AND
    - assay AND
    - model context (in vivo/in vitro/human/rat/plasma/serum)
    
    This is objective, not subjective.
    """
    # Normalize confidence to known values (handle synonyms and unexpected values)
    conf_normalized = current_conf.lower().strip() if current_conf else "low"
    conf_map = {
        "high": "high",
        "med": "med",
        "medium": "med",
        "low": "low",
        "": "low",
        "none": "low"
    }
    conf_normalized = conf_map.get(conf_normalized, "other")

    if conf_normalized == "high":
        return "high"  # Already high

    if not entities_str:
        return conf_normalized

    # Parse entities
    entities = entities_str.split("; ") if entities_str else []
    entity_types = set()
    entity_names_lower = set()

    for e in entities:
        if ":" in e:
            etype, ename = e.split(":", 1)
            entity_types.add(etype.lower())
            entity_names_lower.add(ename.lower())
    
    # Domain-specific high-value entities
    if domain_id == "construction_science":
        # Construction science: materials, systems, failure modes, environments
        has_high_value = bool(entity_types & {"material", "system", "failure_mode", "environment", "hazard"})
    else:
        # Biomedical domains: compounds, targets, stem cells
        has_high_value = bool(entity_types & {"compound", "target", "stem_cell"})
    
    # Check for assay
    has_assay = "assay" in entity_types
    
    # Check for model context
    model_context_terms = {
        "in vivo", "in vitro", "human", "rat", "mouse", "plasma", "serum",
        "blood", "tissue", "cell culture", "fbs"
    }
    has_model_context = bool(entity_names_lower & model_context_terms)
    
    # Promote if all three conditions met
    if has_high_value and has_assay and has_model_context:
        return "high"
    
    # Promote to med if has high-value entity + assay (even without model context)
    if has_high_value and has_assay and conf_normalized == "low":
        return "med"
    
    return conf_normalized

def count_entities_by_role(entities_str: str, norm_map: dict, overlay_aliases: dict = None) -> Tuple[int, int, str, str, str]:
    """
    Count primary and context entities in a semicolon-separated string.
    Uses overlay aliases for normalization (MSC→mesenchymal stem cell).
    Also demotes process words to tags.
    Returns: (primary_count, context_count, primary_str, context_str, all_str)
    """
    if not entities_str:
        return (0, 0, "", "", "")
    
    # Parse entities
    entity_pairs = [e.split(':', 1) for e in entities_str.split('; ') if ':' in e]
    entity_dicts = [
        {"entity_type": etype, "entity_name": ename}
        for etype, ename in entity_pairs
    ]
    
    # Normalize with overlay aliases
    normalized = []
    for e in entity_dicts:
        norm_e = normalize_entity(e, norm_map, overlay_aliases)
        norm_e["role"] = get_entity_role(norm_e, norm_map)
        normalized.append(norm_e)
    
    # Separate by role, demoting process words
    primary = []
    context = []
    
    for idx, e in enumerate(normalized):
        # Demote process words to context
        if e['entity_type'] == 'assay' and is_process_word(e['entity_name']):
            new_e = e.copy()
            new_e['role'] = 'context'  # Override role
            normalized[idx] = new_e
            e = new_e
        
        entity_str = f"{e['entity_type']}:{e['entity_name']}"
        
        if e['role'] == 'primary':
            primary.append(entity_str)
        else:
            context.append(entity_str)
    
    primary_str = "; ".join(primary) if primary else ""
    context_str = "; ".join(context) if context else ""
    all_str = "; ".join([f"{e['entity_type']}:{e['entity_name']}" for e in normalized])
    
    return (len(primary), len(context), primary_str, context_str, all_str)

def write_run_meta(confidence_changes: Dict[str, int], canonical_entities: Dict[Tuple[str, str], Dict[str, Any]], 
                  domain_id: str = None, output_dir: Path = Path("output"), suffix: str = "") -> None:
    """Write run metadata for reproducibility"""
    domain = get_domain_by_id(domain_id) if domain_id else None
    overlay_id = f"{domain_id}_v1" if domain_id else None
    
    # Ensure overlay aliases are loaded and applied for normalization
    try:
        from .entity_normalizer import load_overlay_aliases
    except ImportError:
        from entity_normalizer import load_overlay_aliases
    overlay_aliases = load_overlay_aliases(domain_id) if domain_id else {}
    overlay_aliases_count = len(overlay_aliases)    # Re-normalize canonical_entities with overlay aliases if not already
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
    
    meta_path = output_dir / f"run_meta{suffix}.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    
    print(f"✅ Wrote run metadata: {meta_path}")

def get_domain_info(domain_id: str = None) -> Tuple[str, Optional[str]]:
    """Get domain information for export headers"""
    domain = get_domain_by_id(domain_id) if domain_id else None
    domain_name = domain.name if domain else "All Domains"
    overlay_id = f"{domain_id}_v1" if domain_id else None
    return domain_name, overlay_id
def load_overlay_aliases_safe(domain_id: str = None) -> Dict[str, str]:
    """Safely load overlay aliases with fallback"""
    try:
        from .entity_normalizer import load_overlay_aliases
        return load_overlay_aliases(domain_id) if domain_id else {}
    except ImportError:
        # Fallback for direct execution
        from entity_normalizer import load_overlay_aliases
        return load_overlay_aliases(domain_id) if domain_id else {}