# lenses/construction_climate_v1.py
from __future__ import annotations

from typing import List, Tuple, Optional
from .construction_common import (
    LensEvent, contains_any, has_unit_signal, has_number, make_entity, dedupe_entities, list_hits
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

def detect(sentence: str) -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    entities: List[dict] = []

    haz = [h for h in HAZARDS if h in s_l]
    resil = [t for t in RESILIENCE_TERMS if t in s_l]

    if not haz and not resil:
        return None, []

    for h in haz[:6]:
        entities.append(make_entity("hazard", h, "hazard", "exposure"))

    for r in resil[:4]:
        entities.append(make_entity("resilience_term", r, "concept", "context"))

    outcome = "unknown"
    if contains_any(s_l, ["reduced", "mitigated", "improved", "enhanced"]):
        outcome = "improved"
    if contains_any(s_l, ["increased risk", "worsened", "exacerbated"]):
        outcome = "failed"

    score = 0
    if haz: score += 2
    if resil: score += 1
    if has_number(s_l): score += 1
    if has_unit_signal(s_l): score += 1
    if contains_any(s_l, ["scenario", "projection", "return period", "rcp", "ssp"]):
        score += 2

    conf = "high" if score >= 6 else "med" if score >= 3 else "low"

    tags = ["climate_resilience"]
    if haz: tags.append("has_hazard")
    if contains_any(s_l, ["rcp", "ssp"]): tags.append("climate_scenario")

    return LensEvent("climate_resilience", outcome, conf, tags), dedupe_entities(entities)
