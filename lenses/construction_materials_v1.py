# lenses/construction_materials_v1.py
from __future__ import annotations

import re
from typing import List, Tuple, Optional
from .construction_common import (
    LensEvent, contains_any, has_unit_signal, has_number, make_entity, dedupe_entities, list_hits
)

MATERIALS = [
    "concrete", "reinforced concrete", "cement", "fly ash", "slag", "silica fume",
    "steel", "structural steel", "stainless steel",
    "timber", "wood", "glulam", "cross laminated timber",
    "masonry", "brick", "cmu",
    "asphalt", "bitumen",
    "insulation", "mineral wool", "fiberglass", "cellulose", "eps", "xps", "polyurethane"
]

PROPERTIES = [
    "compressive strength", "tensile strength", "flexural strength", "modulus",
    "durability", "permeability", "porosity", "diffusivity", "chloride penetration",
    "thermal conductivity", "fire resistance", "shrinkage", "creep", "workability"
]

POSITIVE_COMPARATORS = ["increased", "improved", "higher", "enhanced"]
NEGATIVE_COMPARATORS = ["decreased", "reduced", "lower", "degraded"]
COMPARATORS = POSITIVE_COMPARATORS + NEGATIVE_COMPARATORS
TEST_MARKERS = ["test", "tested", "measured", "results", "specimen", "samples"]

def detect(sentence: str) -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    entities: List[dict] = []

    mats = list_hits(s_l, MATERIALS)
    props = list_hits(s_l, PROPERTIES)

    # Signal: materials + property, or strong unit/numeric measurement + property, or test marker alone
    signal = (bool(mats) and bool(props)) or (bool(props) and (has_unit_signal(s_l) or has_number(s_l))) or contains_any(s_l, TEST_MARKERS)

    # Allow test markers alone to trigger detection, even if props is empty
    if not signal or (not props and not contains_any(s_l, TEST_MARKERS)):
        return None, []

    # Note: matches are lowercased because list_hits is run on s_l (lowercased input)
    for m in mats[:5]:
        entities.append(make_entity("material", m, "material", "tested"))

    for p in props[:6]:
        entities.append(make_entity("property", p, "property", "measurement"))

    if contains_any(s_l, POSITIVE_COMPARATORS):
        outcome = "improved"
    elif contains_any(s_l, NEGATIVE_COMPARATORS):
        outcome = "degraded"
    else:
        outcome = "unknown"

    score = 0
    if mats:
        score += 2
    if props:
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
    if props:
        tags.append("has_property")
    if has_unit_signal(s_l):
        tags.append("has_units")

    return LensEvent("material_performance", outcome, conf, tags), dedupe_entities(entities)
