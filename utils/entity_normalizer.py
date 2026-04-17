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
    try:
        import importlib.util
        if importlib.util.find_spec('.seed_overlay_loader', __package__):
            pass  # Module exists, but import failed for another reason
    except ImportError as e:
        # Only fallback if the import failed because the module is missing
        if getattr(e, 'name', None) == 'seed_overlay_loader' or isinstance(e, ModuleNotFoundError):
            try:
                import importlib.util
                if importlib.util.find_spec('seed_overlay_loader') is not None:
                    pass  # Module exists, but import failed for another reason
            except ImportError as e2:
                if getattr(e2, 'name', None) == 'seed_overlay_loader' or isinstance(e2, ModuleNotFoundError):
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Could not import seed_overlay_loader, overlay aliases unavailable for {domain_id}"
                    )
                else:
                    raise
        else:
            raise
