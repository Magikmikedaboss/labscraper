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
from dataclasses import dataclass
from typing import Dict, List, Optional


def load_normalization_map(path: str = "seeds/normalization.json") -> dict:
    """Load the normalization map from JSON file"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


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
    if not domain_id:
        return {}
    
    # Map domain IDs to overlay files
    mapping = {
        "stem_cells_regen": "stem_cells_overlay_v1.json",
        "neuroscience_cognition": "neuroscience_overlay_v1.json",
        "biohacking_longevity": "longevity_overlay_v1.json",
    }
    
    fname = mapping.get(domain_id)
    if not fname:
        return {}
    
    overlay_path = Path(overlays_dir) / fname
    if not overlay_path.exists():
        return {}
    
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    
    # Extract aliases from overlay
    aliases = {}
    if "entities" in overlay and "aliases" in overlay["entities"]:
        for canonical, alias_list in overlay["entities"]["aliases"].items():
            for alias in alias_list:
                aliases[alias.lower()] = canonical
    
    return aliases


def normalize_entity_name(entity_type: str, entity_name: str, norm_map: dict, overlay_aliases: Optional[Dict[str, str]] = None) -> str:
    """
    Normalize an entity name to its canonical form.
    
    Checks overlay aliases first (MSC→mesenchymal stem cell), then core normalization map.
    
    Args:
        entity_type: Type of entity (assay, compound, model, etc.)
        entity_name: Original entity name
        norm_map: Normalization map loaded from JSON
        overlay_aliases: Optional overlay alias map (from load_overlay_aliases)
        
    Returns:
        Canonical entity name, or original if no mapping found
    """
    name_lower = entity_name.lower()
    
    # Check overlay aliases first (higher priority)
    if overlay_aliases and name_lower in overlay_aliases:
        return overlay_aliases[name_lower]
    
    # Check core normalization map
    if entity_type not in norm_map:
        return entity_name
    
    # Check each canonical form and its variants
    for canonical, variants in norm_map[entity_type].items():
        for variant in variants:
            if name_lower == variant.lower():
                return canonical
    
    # No mapping found, return original
    return entity_name


def normalize_entity(entity: dict, norm_map: dict, overlay_aliases: Optional[Dict[str, str]] = None) -> dict:
    """
    Normalize an entity dict to use canonical name.
    
    Args:
        entity: Entity dict with keys: entity_type, entity_name, entity_variant, etc.
        norm_map: Normalization map loaded from JSON
        overlay_aliases: Optional overlay alias map (from load_overlay_aliases)
        
    Returns:
        New entity dict with normalized name
    """
    normalized_name = normalize_entity_name(
        entity["entity_type"],
        entity["entity_name"],
        norm_map,
        overlay_aliases
    )
    
    return {
        **entity,
        "entity_name": normalized_name,
        "original_name": entity.get("original_name", entity["entity_name"])
    }


def is_context_entity(entity: dict, norm_map: dict) -> bool:
    """
    Check if an entity is context-only (should be demoted from rankings).
    
    Args:
        entity: Entity dict with entity_name
        norm_map: Normalization map loaded from JSON
        
    Returns:
        True if entity is context-only, False otherwise
    """
    context_list = norm_map.get("context_only_entities", [])
    return entity["entity_name"].upper() in [c.upper() for c in context_list]


def get_entity_role(entity: dict, norm_map: dict) -> str:
    """
    Determine entity role: 'primary' or 'context'.
    
    Args:
        entity: Entity dict
        norm_map: Normalization map
        
    Returns:
        'context' if context-only entity, 'primary' otherwise
    """
    return "context" if is_context_entity(entity, norm_map) else "primary"


def normalize_entity_list(entities: List[dict], norm_map: dict) -> List[dict]:
    """
    Normalize a list of entities and add role information.
    
    Args:
        entities: List of entity dicts
        norm_map: Normalization map
        
    Returns:
        List of normalized entities with role field added
    """
    normalized = []
    for entity in entities:
        norm_entity = normalize_entity(entity, norm_map)
        norm_entity["role"] = get_entity_role(norm_entity, norm_map)
        normalized.append(norm_entity)
    
    return normalized


def get_primary_entities(entities: List[dict], norm_map: dict) -> List[dict]:
    """
    Filter to only primary (non-context) entities.
    
    Args:
        entities: List of entity dicts
        norm_map: Normalization map
        
    Returns:
        List of primary entities only
    """
    normalized = normalize_entity_list(entities, norm_map)
    return [e for e in normalized if e["role"] == "primary"]


def get_context_entities(entities: List[dict], norm_map: dict) -> List[dict]:
    """
    Filter to only context entities.
    
    Args:
        entities: List of entity dicts
        norm_map: Normalization map
        
    Returns:
        List of context entities only
    """
    normalized = normalize_entity_list(entities, norm_map)
    return [e for e in normalized if e["role"] == "context"]


# Example usage
if __name__ == "__main__":
    # Load normalization map
    norm_map = load_normalization_map()
    
    # Test entities
    test_entities = [
        {"entity_type": "assay", "entity_name": "mass spectrometry", "entity_variant": "assay"},
        {"entity_type": "assay", "entity_name": "LC-MS/MS", "entity_variant": "assay"},
        {"entity_type": "assay", "entity_name": "liquid chromatography", "entity_variant": "assay"},
        {"entity_type": "model", "entity_name": "in vivo", "entity_variant": "experimental"},
        {"entity_type": "model", "entity_name": "HUMAN", "entity_variant": "organism"},
        {"entity_type": "compound", "entity_name": "SEMAGLUTIDE", "entity_variant": "peptide"},
    ]
    
    print("=" * 70)
    print("ENTITY NORMALIZATION TEST")
    print("=" * 70)
    
    print("\n1. Core normalization (no overlay):")
    for e in test_entities:
        print(f"  {e['entity_name']} ({e['entity_type']})")
    
    print("\n2. Normalized entities:")
    normalized = normalize_entity_list(test_entities, norm_map)
    for e in normalized:
        role_marker = "🔧" if e["role"] == "context" else "⭐"
        print(f"  {role_marker} {e['entity_name']} ({e['entity_type']}) - {e['role']}")
    
    # Test overlay aliases
    print("\n3. Testing overlay aliases (stem cells domain):")
    overlay_aliases = load_overlay_aliases("stem_cells_regen")
    print(f"   Loaded {len(overlay_aliases)} aliases from stem cells overlay")
    
    # Test stem cell abbreviations
    stem_cell_tests = [
        {"entity_type": "cell_type", "entity_name": "MSC", "entity_variant": "cell"},
        {"entity_type": "cell_type", "entity_name": "iPSC", "entity_variant": "cell"},
        {"entity_type": "cell_type", "entity_name": "ESC", "entity_variant": "cell"},
        {"entity_type": "cell_type", "entity_name": "mesenchymal stem cell", "entity_variant": "cell"},
    ]
    
    print("\n   Abbreviation → Canonical:")
    for e in stem_cell_tests:
        normalized = normalize_entity(e, norm_map, overlay_aliases)
        arrow = "→" if e["entity_name"] != normalized["entity_name"] else "="
        print(f"   {e['entity_name']:30} {arrow} {normalized['entity_name']}")
    
    print("\n4. Primary entities only (for rankings):")
    primary = get_primary_entities(test_entities, norm_map)
    for e in primary:
        print(f"  ⭐ {e['entity_name']} ({e['entity_type']})")
    
    print("\n5. Context entities only (for filters):")
    context = get_context_entities(test_entities, norm_map)
    for e in context:
        print(f"  🔧 {e['entity_name']} ({e['entity_type']})")
    
    print("\n" + "=" * 70)
    print("✅ Overlay alias normalization working!")
    print("=" * 70)
