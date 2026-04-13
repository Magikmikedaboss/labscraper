"""Convenience helpers for the construction lens suite."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .construction_building_physics_v1 import detect as detect_building_physics
from .construction_climate_v1 import detect as detect_climate
from .construction_common import get_source_weight
from .construction_compliance_v1 import detect as detect_compliance
from .construction_failure_v1 import detect as detect_failure
from .construction_materials_v1 import detect as detect_materials

LENS_REGISTRY = {
    "failure": detect_failure,
    "materials": detect_materials,
    "building_physics": detect_building_physics,
    "climate": detect_climate,
    "compliance": detect_compliance,
}


def detect_multi_lens(
    sentence: str,
    source_type: str = "research_paper",
    enabled_lenses: Optional[Iterable[str]] = None,
) -> List[dict]:
    """Run all enabled construction lenses and return stacked results for one sentence."""
    results: List[dict] = []
    selected_lenses = list(enabled_lenses) if enabled_lenses is not None else list(LENS_REGISTRY.keys())

    confidence_rank = {"low": 1, "med": 2, "high": 3}
    context_rank = {"weak": 1, "moderate": 2, "strong": 3}

    for lens_name in selected_lenses:
        detector = LENS_REGISTRY.get(lens_name)
        if detector is None:
            continue

        event, entities = detector(sentence, source_type=source_type)
        if event is None:
            continue

        if event.lens is None:
            event.lens = lens_name
        if event.source_weight is None:
            event.source_weight = get_source_weight(source_type)

        stacked = event.as_dict()
        stacked["lens"] = event.lens if event.lens is not None else lens_name
        stacked["entities"] = entities
        results.append(stacked)

    results.sort(
        key=lambda item: (
            item.get("source_weight", 0.0),
            confidence_rank.get(item.get("confidence", "low"), 0),
            context_rank.get(item.get("context_strength", "weak"), 0),
        ),
        reverse=True,
    )
    return results


__all__ = [
    "LENS_REGISTRY",
    "detect_building_physics",
    "detect_climate",
    "detect_compliance",
    "detect_failure",
    "detect_materials",
    "detect_multi_lens",
]

