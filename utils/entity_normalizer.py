
import logging
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Union

# Central set of primary entity types
PRIMARY_TYPES = {
    'gene', 'protein', 'compound', 'cell_type', 'assay', 'test_method',
    'stem_cell', 'neural_cell', 'model', 'peptide', 'failure_mode', 'target',
    'organism', 'disease', 'phenotype', 'mutation', 'variant', 'tissue', 'pathway',
    'biomarker', 'receptor', 'enzyme', 'transcription_factor', 'rna', 'metabolite',
    'drug', 'chemical', 'exposure', 'treatment', 'intervention', 'outcome', 'measurement'
}


def load_normalization_map(path: str = "seeds/normalization.json") -> dict:
    """Load the normalization map from JSON file"""
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



# Module-level import and flag for seed_overlay_loader
try:
    from utils import seed_overlay_loader
    _SEED_OVERLAY_LOADER_AVAILABLE = True
except (ImportError, ModuleNotFoundError, SyntaxError) as e:
    logging.getLogger(__name__).warning(f"seed_overlay_loader could not be imported: {e}")
    seed_overlay_loader = None
    _SEED_OVERLAY_LOADER_AVAILABLE = False

def load_overlay_aliases(domain_id: Optional[str] = None, overlays_dir: str = "seeds/overlays") -> Dict[str, str]:
    """
    Load alias→canonical mappings from domain overlay using seed_overlay_loader if available.

    Args:
        domain_id: Domain identifier (e.g., "stem_cells_regen")
        overlays_dir: Path to overlays directory

    Returns:
        Dictionary mapping alias (lowercase) to canonical name. Empty if unavailable or error.

    Example:
        {"msc": "mesenchymal stem cell", "ipsc": "induced pluripotent stem cell"}

    Notes:
        - If seed_overlay_loader is not present or fails, returns an empty dict and logs a warning.
        - If neither get_overlay_aliases nor OVERLAY_ALIASES is present, logs a warning.
    """
    overlay_map = {}
    logger = logging.getLogger(__name__)
    if not _SEED_OVERLAY_LOADER_AVAILABLE or seed_overlay_loader is None:
        logger.warning(f"seed_overlay_loader not available, overlay aliases unavailable for {domain_id}")
        return overlay_map
    try:
        if hasattr(seed_overlay_loader, 'get_overlay_aliases'):
            overlay_map = seed_overlay_loader.get_overlay_aliases(domain_id, overlays_dir)
        elif hasattr(seed_overlay_loader, 'OVERLAY_ALIASES'):
            overlay_map = seed_overlay_loader.OVERLAY_ALIASES.get(domain_id, {})
        else:
            logger.warning(f"seed_overlay_loader found but no loader function or alias map present for {domain_id}")
    except Exception as e:
        logger.error(f"Error loading overlay aliases for {domain_id}: {e}")
    return overlay_map


def normalize_entity(entity: dict, norm_map: dict, overlay_aliases: Optional[dict] = None) -> dict:
    """
    Normalize an entity using the normalization map and overlay aliases.
    Args:
        entity: dict with keys 'entity_type', 'entity_name', 'entity_variant'
        norm_map: normalization mapping
        overlay_aliases: overlay alias mapping (optional)
    Returns:
        dict with normalized 'entity_type', 'entity_name', 'entity_variant', preserving extra keys
    Notes:
        Input fields (etype, name, variant) are normalized to lowercase before matching. Matching against overlay_aliases and norm_map is case-insensitive because the code compares against v.lower(), and mapped values are lowercased for consistency.
    """
    copy = dict(entity)
    name = (entity.get('entity_name') or '').strip().lower()
    etype = (entity.get('entity_type') or '').strip().lower()
    variant = (entity.get('entity_variant') or '').strip().lower()
    # Overlay alias normalization (mapped values are lowercased)
    if overlay_aliases and name in overlay_aliases:
        mapped_name = overlay_aliases[name]
        name = mapped_name.lower() if isinstance(mapped_name, str) else str(mapped_name).lower()
    if overlay_aliases and variant in overlay_aliases:
        mapped_variant = overlay_aliases[variant]
        variant = mapped_variant.lower() if isinstance(mapped_variant, str) else str(mapped_variant).lower()
    # Normalization map: match input name to any variant in norm_map[etype] and set to canonical_name
    # Supported shapes for variants_entry:
    #   list:  ["a", "b"]
    #   dict:  {"key": ["a", "b"], "other": ["c"]}
    #   tuple: (["a", "b"], metadata)  # only first element (list) is used
    #   else:  falls back to empty list
    # This logic maps any matching variant (case-insensitive) to canonical_name.
    # Role assignment is handled by get_entity_role.
    if etype in norm_map:
        name_resolved = False
        variant_resolved = not bool(variant)
        for canonical_name, variants_entry in norm_map[etype].items():
            if isinstance(variants_entry, list):
                # e.g. ["a", "b"]
                variants = variants_entry
            elif isinstance(variants_entry, dict):
                # e.g. {"variants": ["a", "b"], "role": "primary"}
                variants = variants_entry.get('variants', [])
            elif isinstance(variants_entry, tuple):
                # e.g. (["a", "b"], metadata)
                variants = variants_entry[0]
            else:
                variants = []

            if (not name_resolved) and any(name == v.lower() for v in variants):
                name = canonical_name.lower()
                name_resolved = True

            if (not variant_resolved) and variant and any(variant == v.lower() for v in variants):
                variant = canonical_name.lower()
                variant_resolved = True

            if name_resolved and variant_resolved:
                break
    copy['entity_type'] = etype
    copy['entity_name'] = name
    copy['entity_variant'] = variant
    # Do not return a string; always return a dict
    # Role assignment is handled by get_entity_role
    return copy



def get_entity_role(
    entity: dict,
    norm_map: Dict[str, Dict[str, Union[List[str], Dict[str, object], Tuple[List[str], str]]]]
) -> str:
    """
    Assign a role to the entity based on type and normalization map.

    Args:
        entity (dict): Entity dictionary with at least 'entity_type' and 'entity_name'.
        norm_map (dict): Normalization map of the form:
            norm_map[etype][canonical_name] = variants_entry
            where variants_entry can be one of:
                - list[str]: List of variant names (legacy format)
                  Example: ['rapamycin', 'sirolimus']
                - dict: {'variants': list[str], 'role': str}
                  Example: {'variants': ['rapamycin', 'sirolimus'], 'role': 'primary'}
                - tuple: (list[str], str)
                  Example: (['rapamycin', 'sirolimus'], 'primary')
            The function will check if the entity name matches canonical_name or any variant, and return the associated role.

    Returns:
        str: 'primary' for main entities, 'context' for context-only, or 'unknown'.

    Symbol references:
        - norm_map: normalization mapping as described above
        - etype: entity type (lowercased)
        - canonical_name: canonical entity name (lowercased)
        - variants_entry: one of the accepted formats above
        - role: string role, e.g. 'primary' or 'context'

    Example norm_map usage:
        norm_map = {
            'compound': {
                'rapamycin': ['rapamycin', 'sirolimus'],
                'metformin': {'variants': ['metformin', 'glucophage'], 'role': 'primary'},
                'everolimus': (['everolimus', 'afinitor'], 'context'),
            }
        }
    """
    etype = (entity.get('entity_type') or '').strip().lower()
    name = (entity.get('entity_name') or '').strip().lower()

    # 1. Try new-style norm_map[etype][canonical_name] supporting role metadata
    if etype in norm_map:
        for canonical_name, variants_entry in norm_map[etype].items():
            # Support legacy: variants_entry is a list
            role = 'primary'
            if isinstance(variants_entry, list):
                variants = variants_entry
            # Support dict: {'variants': [...], 'role': ...}
            elif isinstance(variants_entry, dict):
                variants = variants_entry.get('variants', [])
                role = variants_entry.get('role', 'primary')
            # Support tuple: ([...], 'role')
            elif isinstance(variants_entry, tuple) and len(variants_entry) == 2:
                variants, role = variants_entry
            else:
                variants = []
            all_variants = [canonical_name] + list(variants)
            if any(name == v.lower() for v in all_variants):
                return role

    def _matches_legacy_names(values) -> bool:
        if isinstance(values, dict):
            candidates = values.keys()
        else:
            candidates = values
        return any(name == str(value).strip().lower() for value in candidates)

    # 2. Fallback: old top-level norm_map['context'] and norm_map['primary']
    if 'context' in norm_map and etype in norm_map['context'] and _matches_legacy_names(norm_map['context'][etype]):
        return 'context'
    if 'primary' in norm_map:
        if etype in norm_map['primary']:
            if _matches_legacy_names(norm_map['primary'][etype]):
                return 'primary'

    # 3. Expanded set of primary types
    if etype in PRIMARY_TYPES:
        return 'primary'
    return 'unknown'
