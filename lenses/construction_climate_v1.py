# lenses/construction_climate_v1.py
from __future__ import annotations

from typing import List, Tuple, Optional
from .construction_common import (
    LensEvent, build_lens_event, contains_any, has_unit_signal, has_number, make_entity, dedupe_entities, list_hits
)

HAZARDS = [
    "flood", "storm surge", "sea-level rise", "sea level rise",
    "wind", "hurricane", "tornado",
    "wildfire", "smoke",
    "heat wave", "extreme heat", "high temperature",
    "freeze-thaw", "freeze thaw", "icing",
    "humidity", "moisture", "drought"
]

RESILIENCE_TERMS = ["resilience", "adaptation", "mitigation", "risk", "hazard", "exposure", "vulnerability"]

# Construction materials and systems that should boost climate signals when co-occurring
CONSTRUCTION_MATERIALS = [
    "concrete", "steel", "wood", "timber", "brick", "masonry", "glass", "aluminum", "copper", "plastic",
    "composite", "polymer", "insulation", "foam", "panel", "board", "membrane", "coating", "paint", "sealant"
]

CONSTRUCTION_SYSTEMS = [
    "roof", "wall", "floor", "foundation", "structure", "frame", "beam", "column", "slab", "deck",
    "façade", "cladding", "curtain wall", "window", "door", "ventilation", "HVAC", "heating", "cooling",
    "drainage", "plumbing", "electrical", "mechanical", "structural system", "building envelope"
]

def detect(sentence: str, source_type: str = "research_paper") -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    entities: List[dict] = []

    # Use word-boundary matching for hazards and resilience terms
    haz = list_hits(s_l, HAZARDS)
    resil = list_hits(s_l, RESILIENCE_TERMS)

    if not haz and not resil:
        return None, []

    for h in haz[:6]:
        entities.append(make_entity("hazard", h, "hazard", "exposure"))

    for r in resil[:4]:
        entities.append(make_entity("resilience_term", r, "concept", "context"))

    # Outcome assignment logic:
    #   - outcome == "degraded": Explicit negative language is present (e.g., "increased risk", "worsened").
    #     This means the sentence contains strong signals of climate impact or vulnerability worsening.
    #   - outcome == "negative": A hazard is present, but there is no explicit negative outcome phrase.
    #     This means the sentence mentions a hazard but does not use strong language about impact.
    #   - outcome == "improved": Explicit positive language is present (e.g., "mitigated", "improved").
    #   - outcome == "neutral": No hazard or resilience signal is present.
    #
    # Downstream use: Consumers of the outcome field can distinguish between explicit negative impact ("degraded")
    # and generic hazard mention ("negative"). This allows for more nuanced event classification and reporting.
    outcome = "neutral"
    if contains_any(s_l, ["increased risk", "risk increased", "worsened", "exacerbated", "higher vulnerability"]):
        outcome = "degraded"
    elif contains_any(s_l, ["reduced", "mitigated", "improved", "enhanced"]):
        outcome = "improved"
    elif haz:
        outcome = "negative"

    score = 0
    if haz:
        score += 2
    if resil:
        score += 1
    if has_number(s_l):
        score += 1
    if has_unit_signal(s_l):
        score += 1
    if contains_any(s_l, ["scenario", "projection", "return period", "rcp", "ssp"]):
        score += 2

    # CLIMATE CO-OCCURRENCE BOOST: When climate terms co-occur with materials or systems
    materials_hits = list_hits(s_l, CONSTRUCTION_MATERIALS)
    systems_hits = list_hits(s_l, CONSTRUCTION_SYSTEMS)
    
    if (haz or resil) and (materials_hits or systems_hits):
        score += 2  # Boost climate signals when they relate to construction elements
        # Add the co-occurring materials/systems as entities
        for m in materials_hits[:3]:
            entities.append(make_entity("material", m, "material", "context"))
        for s in systems_hits[:3]:
            entities.append(make_entity("system", s, "system", "context"))

    conf = "high" if score >= 6 else "med" if score >= 3 else "low"

    tags = ["climate_resilience"]
    if haz:
        tags.append("has_hazard")
    if contains_any(s_l, ["rcp", "ssp"]):
        tags.append("climate_scenario")
    if materials_hits or systems_hits:
        tags.append("construction_climate_interaction")

    return build_lens_event("climate", "climate_resilience", outcome, conf, tags, sentence, source_type), dedupe_entities(entities)
