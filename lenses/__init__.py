"""Convenience helpers for the construction lens suite."""

from __future__ import annotations
import logging
from typing import Iterable, List, Optional, Tuple, Dict, Union
from .construction_building_physics_v1 import detect as detect_building_physics
from .construction_climate_v1 import detect as detect_climate
from .construction_compliance_v1 import detect as detect_compliance
from .construction_failure_v1 import detect as detect_failure
from .construction_materials_v1 import detect as detect_materials

logger = logging.getLogger(__name__)


LENS_REGISTRY = {
    "building_physics": detect_building_physics,
    "climate": detect_climate,
    "compliance": detect_compliance,
    "failure": detect_failure,
    "materials": detect_materials,
}

def detect_multi_lens(
    sentence: str,
    source_type: str = "research_paper",
    enabled_lenses: Optional[Iterable[str]] = None,
    raise_on_no_match: bool = False,
    return_errors: bool = False,
) -> Union[List[dict], Tuple[List[dict], Dict[str, str]]]:
    """
    Run all enabled construction lenses and return stacked results for one sentence.

    Args:
        sentence: Input sentence to analyze.
        source_type: Type of source (default: research_paper).
        enabled_lenses: List of lens names to use (default: all).
        raise_on_no_match: If True, raise if no results (even if no errors). Default: False.
        return_errors: If True, return (results, detector_errors) tuple instead of just results.

    Returns:
        - If return_errors is False (default): List of stacked event dicts (List[dict]).
        - If return_errors is True: Tuple[List[dict], Dict[str, str]] where the second element is a dict of detector errors.
        If no results and no errors, returns [] (or ([], {}) if return_errors).
        Raises RuntimeError only if detector_errors is non-empty or raise_on_no_match is True.
    """
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
        detector = LENS_REGISTRY[lens_name]
        try:
            event, entities = detector(sentence, source_type=source_type)
        except Exception as e:
            detector_errors[lens_name] = str(e)
            continue
        # Only record as error if event is None and entities is not empty (unexpected),
        # or if there is an explicit error signal. Normal no-match (None, []) is not an error.
        if event is None:
            if entities:
                detector_errors[lens_name] = "No event returned but entities present"
            # else: normal no-match, do not record error
            continue
        stacked = event.as_dict()
        stacked["entities"] = entities
        results.append(stacked)


    if not results:
        if detector_errors:
            raise RuntimeError(f"No detector produced results. Errors: {detector_errors}")
        if raise_on_no_match:
            raise RuntimeError("No detector produced results (no match)")
        # If return_errors, return both (empty) results and errors
        if not return_errors:
            logger.warning("No detectors matched and no errors reported.")
        return ([], detector_errors) if return_errors else []

    # If there are results and also detector_errors, log a warning for partial failures
    if detector_errors and results:
        logger.warning("Some detectors failed: %r", detector_errors)

    results.sort(
        key=lambda item: (
            item.get("source_weight", 0.0),
            confidence_rank.get(item.get("confidence", "low"), 0),
            context_rank.get(item.get("context_strength", "weak"), 0),
        ),
        reverse=True,
    )
    return (results, detector_errors) if return_errors else results


__all__ = [
    "LENS_REGISTRY",
    "detect_building_physics",
    "detect_climate",
    "detect_compliance",
    "detect_failure",
    "detect_materials",
    "detect_multi_lens",
]

