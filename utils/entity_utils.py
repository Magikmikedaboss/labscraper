"""
Entity normalization, role assignment, and counting utilities
"""

from __future__ import annotations

import logging
from typing import Tuple, Dict
from utils.entity_normalizer import normalize_entity, get_entity_role
from utils.process_words import is_process_word
import re


logger = logging.getLogger(__name__)

def count_entities_by_role(entities_str: str, norm_map: dict, overlay_aliases: dict | None = None) -> Tuple[int, int, str, str, str]:
    """
    Count primary and context entities in a semicolon-separated string.
    Uses overlay aliases for normalization (MSC→mesenchymal stem cell).
    Also demotes process words to tags.
    Returns: (primary_count, context_count, primary_str, context_str, all_str)
    """
    if not entities_str:
        return (0, 0, "", "", "")
    tokens = [t.strip() for t in re.split(r'\s*;\s*', entities_str) if t.strip()]
    entity_pairs = [e.split(':', 1) for e in tokens if ':' in e]
    # Store both original and normalized forms
    entity_dicts = [
        {"entity_type": etype, "entity_name": ename, "orig_entity_type": etype, "orig_entity_name": ename}
        for etype, ename in entity_pairs
    ]
    normalized = []
    for e in entity_dicts:
        norm_e = normalize_entity(e, norm_map, overlay_aliases)
        norm_e["role"] = get_entity_role(norm_e, norm_map)
        normalized.append(norm_e)
    primary = []
    context = []
    for e in normalized:
        if e['entity_type'] == 'assay' and is_process_word(e['orig_entity_name']):
            e['role'] = 'context'
        # Use original casing for output
        entity_str = f"{e['orig_entity_type']}:{e['orig_entity_name']}"
        if e['role'] == 'primary':
            primary.append(entity_str)
        else:
            context.append(entity_str)
    primary_str = "; ".join(primary) if primary else ""
    context_str = "; ".join(context) if context else ""
    all_str = "; ".join([f"{e['orig_entity_type']}:{e['orig_entity_name']}" for e in normalized])
    return (len(primary), len(context), primary_str, context_str, all_str)

def load_overlay_aliases_safe(domain_id: str | None = None) -> Dict[str, str]:
    """
    Safely load overlay aliases for a given domain_id.
    If domain_id is None, returns an empty dict (no load attempted).
    If importing entity_normalizer or its dependencies fails, returns an empty dict as a safe fallback.
    Callers should not expect aliases when domain_id is None or the dependency is missing.
    Example:
        aliases = load_overlay_aliases_safe("stem_cells_regen")
        # aliases will be {} if domain_id is None or import fails
    """
    if not domain_id:
        return {}
    try:
        from utils.entity_normalizer import load_overlay_aliases
        return load_overlay_aliases(domain_id)
    except Exception as e:
        logger.debug("Failed to load overlay aliases for domain_id '%s': %s", domain_id, e, exc_info=True)
        return {}