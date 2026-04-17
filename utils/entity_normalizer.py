def normalize_entity(entity: dict, norm_map: dict, overlay_aliases: dict = None) -> dict:
    """
    Normalize an entity using the normalization map and overlay aliases.
    Args:
        entity: dict with keys 'entity_type', 'entity_name', 'entity_variant'
        norm_map: normalization mapping
        overlay_aliases: overlay alias mapping (optional)
    Returns:
        dict with normalized 'entity_type', 'entity_name', 'entity_variant'
    """
    name = entity.get('entity_name', '').strip().lower()
    etype = entity.get('entity_type', '').strip().lower()
    variant = entity.get('entity_variant', '').strip().lower() if entity.get('entity_variant') else ''
    # Overlay alias normalization
    if overlay_aliases and name in overlay_aliases:
        name = overlay_aliases[name].lower()
    # Normalization map
    if etype in norm_map and name in norm_map[etype]:
        name = norm_map[etype][name].lower()
    return {
        'entity_type': etype,
        'entity_name': name,
        'entity_variant': variant
    }

def get_entity_role(entity: dict, norm_map: dict) -> str:
    """
    Assign a role to the entity based on type and normalization map.
    Returns 'primary' for main entities, 'context' for context-only, or 'unknown'.
    """
    etype = entity.get('entity_type', '').strip().lower()
    name = entity.get('entity_name', '').strip().lower()
    # Example logic: context entities are marked in norm_map under a 'context' key
    if 'context' in norm_map and etype in norm_map['context'] and name in norm_map['context'][etype]:
        return 'context'
    # Default: primary for known types
    if etype in {'gene', 'protein', 'compound', 'cell_type', 'assay', 'test_method'}:
        return 'primary'
    return 'unknown'
"""
Entity Normalization Module

Collapses entity variants into canonical forms and identifies context-only entities.
Now supports domain overlay aliases for MSC→mesenchymal stem cell, etc.

Usage:
    from entity_normalizer import normalize_entity, is_context_entity, load_overlay_aliases
    
    norm_map = load_normalization_map()
    overlay_aliases = load_overlay_aliases("stem_cells_regen")  # Optional
    
    normalized = normalize_entity(entity, norm_map, overlay_aliases)
    if not is_context_entity(normalized):
        # Include in top entities ranking
"""

import json
from pathlib import Path
from typing import Dict, Optional


def load_normalization_map(path: str = "seeds/normalization.json") -> dict:
    """Load the normalization map from JSON file"""
    import logging
    try:
        text = Path(path).read_text(encoding="utf-8")
        return json.loads(text)
    except FileNotFoundError:
        logging.getLogger(__name__).error(f"Normalization map file not found: {path}")
        raise ValueError(f"Normalization map file not found: {path}")
    except json.JSONDecodeError as e:
        logging.getLogger(__name__).error(f"Error decoding normalization map JSON: {e}")
        raise ValueError(f"Error decoding normalization map JSON: {e}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Unexpected error loading normalization map: {e}")
        raise


def load_overlay_aliases(domain_id: Optional[str] = None, overlays_dir: str = "seeds/overlays") -> Dict[str, str]:
    """
    Load alias→canonical mappings from domain overlay.
    
    Args:
        domain_id: Domain identifier (e.g., "stem_cells_regen")
        overlays_dir: Path to overlays directory
        
    Returns:
        Dictionary mapping alias (lowercase) to canonical name
        
    Example:
        {"msc": "mesenchymal stem cell", "ipsc": "induced pluripotent stem cell"}
    """
    # Dynamically import seed_overlay_loader if present and get alias map
    import importlib.util
    import importlib
    import logging
    loader_name = 'seed_overlay_loader'
    overlay_map = {}
    try:
        spec = importlib.util.find_spec(loader_name)
        if spec is not None:
            module = importlib.import_module(loader_name)
            if hasattr(module, 'get_overlay_aliases'):
                overlay_map = module.get_overlay_aliases(domain_id, overlays_dir)
            elif hasattr(module, 'OVERLAY_ALIASES'):
                overlay_map = module.OVERLAY_ALIASES.get(domain_id, {})
            else:
                logging.getLogger(__name__).warning(f"seed_overlay_loader found but no loader function or alias map present for {domain_id}")
        else:
            logging.getLogger(__name__).warning(f"seed_overlay_loader not found, overlay aliases unavailable for {domain_id}")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Error loading overlay aliases for {domain_id}: {e}")
    return overlay_map
