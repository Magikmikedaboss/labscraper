"""Convenience helpers for the construction lens suite."""

from __future__ import annotations

from typing import Iterable, List, Optional

from .construction_building_physics_v1 import detect as detect_building_physics
from .construction_climate_v1 import detect as detect_climate
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
    if isinstance(enabled_lenses, str):
        selected_lenses = [enabled_lenses]
    elif enabled_lenses is not None:
        selected_lenses = list(enabled_lenses)
    else:
        selected_lenses = list(LENS_REGISTRY.keys())

    confidence_rank = {"low": 1, "med": 2, "medium": 2, "high": 3}
    context_rank = {"weak": 1, "moderate": 2, "strong": 3}


    # Validate selected_lenses
    invalid_lenses = [name for name in selected_lenses if name not in LENS_REGISTRY]
    if invalid_lenses:
        raise ValueError(f"Invalid lens name(s): {invalid_lenses}. Valid options: {list(LENS_REGISTRY.keys())}")


    detector_errors = {}
    for lens_name in selected_lenses:
        detector = LENS_REGISTRY.get(lens_name)
        try:
            event, entities = detector(sentence, source_type=source_type)
        except Exception as e:
            detector_errors[lens_name] = str(e)
            continue
        if event is None:
            detector_errors[lens_name] = "No event returned"
            continue
        stacked = event.as_dict()
        stacked["entities"] = entities
        results.append(stacked)

    if not results:
        raise RuntimeError(f"No detector produced results. Errors: {detector_errors}")

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

