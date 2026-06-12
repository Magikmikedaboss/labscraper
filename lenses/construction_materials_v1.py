# lenses/construction_materials_v1.py
from __future__ import annotations

from typing import List, Tuple, Optional
from .construction_common import (
    LensEvent, RouteDecision, build_lens_event, contains_any, has_unit_signal, has_number, make_entity, dedupe_entities, list_hits
)

MATERIALS = [
    "concrete", "reinforced concrete", "cement", "fly ash", "slag", "silica fume",
    "steel", "structural steel", "stainless steel", "rebar", "reinforcement", "aggregate",
    "timber", "wood", "glulam", "cross laminated timber",
    "masonry", "brick", "cmu", "mortar", "cementitious",
    "asphalt", "bitumen", "gypsum", "drywall", "osb", "plywood", "stucco",
    "fiber cement", "fiber-cement", "adhesive", "sealant", "coating",
    "insulation", "mineral wool", "fiberglass", "cellulose", "eps", "xps", "polyurethane",
    "epoxy", "polymer", "frp", "fiber reinforced polymer", "fiber-reinforced polymer"
]

PROPERTIES = [
    "compressive strength", "tensile strength", "flexural strength", "shear strength",
    "yield strength", "elastic modulus", "modulus",
    "durability", "service life", "life cycle", "permeability", "porosity", "diffusivity", "chloride penetration",
    "thermal conductivity", "thermal expansion", "vapor permeability", "water absorption",
    "fire resistance", "shrinkage", "creep", "fatigue resistance", "workability"
]

DEGRADATION_TERMS = [
    "corrosion",
    "corrosion resistance",
    "corrosion-resistant",
    "carbonation",
    "freeze-thaw",
    "freeze thaw",
    "chloride ingress",
    "chloride penetration",
    "alkali-silica reaction",
    "alkali silica reaction",
    "asr",
    "sulfate attack",
    "fracture mechanics",
    "microcracking",
    "abrasion",
    "erosion",
    "oxidation",
    "delamination",
    "coating",
    "spalling",
]

STRUCTURAL_MATERIAL_TERMS = {
    "concrete",
    "reinforced concrete",
    "cement",
    "steel",
    "structural steel",
    "stainless steel",
    "rebar",
    "reinforcement",
    "aggregate",
    "timber",
    "wood",
    "glulam",
    "cross laminated timber",
    "masonry",
    "brick",
    "cmu",
    "mortar",
    "cementitious",
    "asphalt",
    "bitumen",
}

MATERIAL_PROPERTY_TERMS = {
    "compressive strength",
    "tensile strength",
    "flexural strength",
    "shear strength",
    "yield strength",
    "elastic modulus",
    "modulus",
    "durability",
    "service life",
    "life cycle",
    "permeability",
    "porosity",
    "diffusivity",
    "chloride penetration",
    "thermal conductivity",
    "thermal expansion",
    "vapor permeability",
    "water absorption",
    "fire resistance",
    "shrinkage",
    "creep",
    "fatigue resistance",
    "workability",
}

MATERIAL_DEGRADATION_TERMS = set(DEGRADATION_TERMS)

METHODS_NOISE_TERMS = ["test", "tested", "results", "sample", "samples", "specimen", "specimens", "measured", "analysis", "experimental", "method", "methods", "assay"]

POSITIVE_COMPARATORS = ["increased", "improved", "higher", "enhanced"]
NEGATIVE_COMPARATORS = ["decreased", "reduced", "lower", "degraded"]
COMPARATORS = POSITIVE_COMPARATORS + NEGATIVE_COMPARATORS


def route_materials_sentence(sentence: str) -> RouteDecision:
    """Registered router callback used by DEFAULT_CONSTRUCTION_LENS_ROUTERS and _detect_multi_lens_internal.

    Return RouteDecision("keep", reason) for materials signals or RouteDecision("skip", reason) otherwise.
    """
    s_l = sentence.lower()
    mats = list_hits(s_l, MATERIALS)
    props = list_hits(s_l, PROPERTIES)
    if not mats and contains_any(s_l, METHODS_NOISE_TERMS):
        return RouteDecision("skip", "methods noise only")
    if mats or props:
        return RouteDecision("keep", "materials signal present")
    return RouteDecision("skip", "no materials signal present")

def detect(sentence: str, source_type: str = "research_paper") -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    entities: List[dict] = []

    mats = list_hits(s_l, MATERIALS)
    props = list_hits(s_l, PROPERTIES)
    degradation_terms = list_hits(s_l, DEGRADATION_TERMS)
    if not mats and contains_any(s_l, METHODS_NOISE_TERMS):
        return None, []


    # Materials is a signal-led lens: material/property markers are enough, and it does not require construction-context gating.
    # Signal is true when: (1) material and property co-occur, or (2) a property is quantified via
    # has_unit_signal(s_l) or has_number(s_l), or (3) explicit materials degradation terms appear with material context.
    signal = (
        (bool(mats) and bool(props))
        or (bool(mats) and bool(degradation_terms))
        or (bool(props) and (has_unit_signal(s_l) or has_number(s_l)))
        or (bool(degradation_terms) and bool(props))
    )
    # Return early if no signal
    if not signal:
        return None, []

    # Note: matches are lowercased because list_hits is run on s_l (lowercased input)
    for m in mats[:5]:
        entities.append(make_entity("material", m, "material", "tested"))

    for p in props[:6]:
        entities.append(make_entity("property", p, "property", "measurement"))

    for d in degradation_terms[:5]:
        entities.append(make_entity("mechanism", d, "degradation", "material"))

    # Materials outputs follow the shared neutral fallback used by other construction lenses.
    if contains_any(s_l, POSITIVE_COMPARATORS):
        outcome = "improved"
    elif contains_any(s_l, NEGATIVE_COMPARATORS):
        outcome = "degraded"
    else:
        outcome = "neutral"

    score = 0
    if mats:
        score += 2
    if props:
        score += 2
    if degradation_terms:
        score += 2
    if has_number(s_l):
        score += 1
    if has_unit_signal(s_l):
        score += 2
    if contains_any(s_l, COMPARATORS):
        score += 1

    conf = "high" if score >= 7 else "med" if score >= 4 else "low"

    tags = ["material_performance"]
    if mats:
        tags.append("has_material")
    if any(term in STRUCTURAL_MATERIAL_TERMS for term in mats):
        tags.append("structural_material")
    if props:
        tags.append("has_property")
    if any(term in MATERIAL_PROPERTY_TERMS for term in props):
        tags.append("material_property")
    if degradation_terms:
        tags.append("has_degradation_term")
    if any(term in MATERIAL_DEGRADATION_TERMS for term in degradation_terms):
        tags.append("material_degradation")
    if has_unit_signal(s_l):
        tags.append("has_units")

    return build_lens_event("materials", "material_performance", outcome, conf, tags, sentence, source_type), dedupe_entities(entities)
