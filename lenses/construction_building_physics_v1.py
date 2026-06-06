# lenses/construction_building_physics_v1.py
from __future__ import annotations

import re
from typing import List, Tuple, Optional
from .construction_common import (
    LensEvent, build_lens_event, contains_any, has_unit_signal, has_number, make_entity, dedupe_entities, list_hits
)

ASSEMBLIES = [
    "envelope", "wall", "roof", "attic", "basement", "slab", "window", "glazing",
    "facade", "cladding", "insulation", "air barrier", "vapor barrier", "duct", "hvac"
]

PHYSICS_TERMS = [
    "u-value", "u value", "r-value", "r value", "thermal conductivity", "heat flux",
    "air leakage", "infiltration", "ventilation rate", "ach", "air changes per hour",
    "relative humidity", "dew point", "condensation", "moisture", "mold",
    "energy use", "energy consumption", "cooling load", "heating load",
    "indoor temperature", "comfort"
]

def detect(sentence: str, source_type: str = "research_paper") -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    entities: List[dict] = []

    asm = list_hits(s_l, ASSEMBLIES)
    terms = list_hits(s_l, PHYSICS_TERMS)

    if not terms:
        return None, []

    for a in asm[:5]:
        entities.append(make_entity("building_component", a, "component", "context"))

    for t in terms[:6]:
        entities.append(make_entity("physics_metric", t, "metric", "measurement"))

    # outcome heuristic: negative signals take priority
    pos = contains_any(s_l, [
        "reduced energy", "reduced consumption", "lower u-value", "lower u value",
        "improved insulation", "improved airtightness", "decreased heat loss",
        "better insulation", "better airtightness", "reduced heat transfer",
        "lower heat loss", "lower energy use", "lower energy consumption",
        "improved r-value", "improved r value", "reduced infiltration"
    ])
    # Flexible positive: 'reduced' within 7 words of 'energy consumption' or 'consumption'
    flexible_positive = False
    # Match 'reduced' and 'energy consumption' (or 'consumption') within 7 words, any order, anywhere
    pattern1 = r"reduc\w*\b(?:\W+\w+){0,7}\W+(energy consumption|consumption)"
    pattern2 = r"(energy consumption|consumption)\b(?:\W+\w+){0,7}\W+reduc\w*"
    if re.search(pattern1, s_l) or re.search(pattern2, s_l):
        flexible_positive = True
    neg = contains_any(s_l, ["higher energy", "increased leakage", "worsened", "condensation risk", "mold growth", "mold detected"])
    if neg:
        outcome = "degraded"
    elif pos or flexible_positive:
        outcome = "positive"
    else:
        outcome = "neutral"
    score = 0
    if terms:
        score += 2
    if asm:
        score += 1
    if has_number(s_l):
        score += 1
    if has_unit_signal(s_l):
        score += 2
    if contains_any(s_l, ["measured", "simulated", "modeled", "validated"]):
        score += 1

    conf = "high" if score >= 6 else "med" if score >= 3 else "low"

    tags = ["building_physics_performance"]
    if asm:
        tags.append("has_component")
    if has_unit_signal(s_l):
        tags.append("has_units")

    return build_lens_event("building_physics", "building_physics_performance", outcome, conf, tags, sentence, source_type), dedupe_entities(entities)
