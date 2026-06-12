from __future__ import annotations

from typing import List, Tuple, Optional

from .construction_common import (
    LensEvent,
    RouteDecision,
    build_lens_event,
    contains_any,
    dedupe_entities,
    list_hits,
    make_entity,
)

TEST_MARKERS = ["test", "tested", "measured", "results", "specimen", "samples"]


def route_methods_tooling_sentence(sentence: str) -> RouteDecision:
    s_l = sentence.lower()
    if list_hits(s_l, TEST_MARKERS):
        return RouteDecision("keep", "methods signal present")
    return RouteDecision("skip", "no methods signal present")


def detect(sentence: str, source_type: str = "research_paper") -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    terms = list_hits(s_l, TEST_MARKERS)
    if not terms:
        return None, []

    entities: List[dict] = []
    for term in terms[:6]:
        entities.append(make_entity("method_term", term, "method_term", "experimental"))

    score = 1
    if len(terms) >= 2:
        score += 1
    if contains_any(s_l, ["analysis", "experiment", "experimental", "method", "methods", "assay"]):
        score += 1
    if contains_any(s_l, ["measured", "tested", "results"]):
        score += 1

    conf = "high" if score >= 3 else "med" if score >= 2 else "low"
    tags = ["experimental_methods"]
    tags.append("has_method_term")

    return build_lens_event("methods_tooling", "experimental_methods", "neutral", conf, tags, sentence, source_type), dedupe_entities(entities)