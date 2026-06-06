import copy
from typing import Any, Callable, Optional


GLOBAL_TYPE_MAPPINGS = {
    "neural_cell": {
        "microglia", "astrocyte", "neuron", "neurons",
        "astrocytes", "microglial", "neuronal", "astrocytic",
    },
    "stem_cell": {"ipsc", "msc", "esc"},
    "model": {"organoid", "organoids"},
}

DOMAIN_TYPE_MAPPINGS = {
    "construction_science": {
        "environment": {
            "ice", "water", "air", "moisture", "humidity", "temperature",
            "heat", "cold", "frost", "snow", "vapor", "climate",
            "weather", "acoustic", "sound", "thaw", "freeze",
        },
        "hazard": {
            "corrosion", "fire", "wind", "seismic", "earthquake", "flood",
            "storm", "lightning", "tornado", "impact",
        },
        "material": {
            "steel", "concrete", "wood", "glass", "brick", "masonry",
            "plastic", "polymer", "composite", "aluminum", "copper",
            "board", "insulation", "panel", "coating", "timber",
        },
        "system": {
            "structure", "building", "foundation", "roof", "wall", "floor",
            "frame", "assembly", "component", "door", "ventilation",
            "building envelope", "column", "heating", "cooling",
            "mechanical", "electrical",
        },
        "failure_mode": {
            "failure", "collapse", "crack", "fracture", "buckling",
            "deflection", "deformation", "leakage", "damage", "rot",
            "deterioration", "weathering", "decay", "expansion",
            "creep", "shrinkage",
        },
        "test_method": {
            "test", "method", "guideline", "standard", "procedure",
            "protocol", "assay", "approach", "practice", "technique",
            "specification", "requirement", "code", "strategy",
        },
    }
}

def normalize_entity_type(name: str, entity_type: str, domain_id: str) -> str:
    """Apply type precedence rules before canonical normalization."""
    name_lower = (name or "").lower().strip()

    for mapped_type, values in GLOBAL_TYPE_MAPPINGS.items():
        if name_lower in values:
            return mapped_type

    for mapped_type, values in DOMAIN_TYPE_MAPPINGS.get(domain_id, {}).items():
        if name_lower in values:
            return mapped_type

    return entity_type

def build_canonical_entities(
    entities: list,
    domain_id: str,
    norm_map: dict,
    overlay_aliases: dict,
    normalize_entity: Callable[[dict[str, Any], dict, dict], dict[str, Any]],
    get_entity_role: Callable[[dict[str, Any], dict], Optional[str]],
    should_skip_entity: Callable[[str, str, Optional[str]], bool],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """
    Merge duplicate entities by canonical name + canonical type.

    Returns:
        canonical_entities, entity_id_mapping
    """
    entity_canonical: dict[tuple[str, str], dict[str, Any]] = {}
    entity_id_mapping: dict[str, str] = {}

    for entity in entities:
        if not isinstance(entity, dict):
            continue

        name = entity.get("entity_name")
        entity_type = entity.get("entity_type")
        if not name or not entity_type:
            continue

        canonical_type = normalize_entity_type(name, entity_type, domain_id)

        normalized = normalize_entity(
            {"entity_type": canonical_type, "entity_name": name},
            norm_map,
            overlay_aliases,
        )
        if not isinstance(normalized, dict):
            continue

        normalized_name = normalized.get("entity_name")
        if not normalized_name:
            continue

        canonical_name = str(normalized_name).strip()
        if not canonical_name:
            continue
        canonical_key = canonical_name.lower()

        role = get_entity_role(
            {"entity_type": canonical_type, "entity_name": canonical_name},
            norm_map,
        )

        if should_skip_entity(canonical_type, canonical_name, role):
            continue

        key = (canonical_key, canonical_type)
        entity_id_str = f"{canonical_type}:{canonical_key}"

        if key not in entity_canonical:
            canonical_entity = copy.deepcopy(entity)
            canonical_entity["entity_id"] = entity_id_str
            canonical_entity["entity_name"] = canonical_name
            canonical_entity["entity_type"] = canonical_type
            canonical_entity["original_names"] = [name]
            entity_canonical[key] = canonical_entity
        else:
            canonical_entity = entity_canonical[key]
            if name not in canonical_entity["original_names"]:
                canonical_entity["original_names"].append(name)

        orig_id = entity.get("entity_id")
        if orig_id is not None:
            entity_id_mapping[orig_id] = entity_id_str

    return list(entity_canonical.values()), entity_id_mapping
