
"""Convenience helpers for the construction lens suite.

Registry entries in LENS_REGISTRY are detector callables with the signature
detect(sentence: str, source_type: str = "research_paper") -> Tuple[Optional[LensEvent], List[dict]]
as used by the detector(sentence, source_type=source_type) call site.
"""

from __future__ import annotations

# ruff: noqa: E402

import traceback
import logging
from typing import Iterable, List, Optional, Protocol, Tuple, Dict, Union
from .construction_common import LensEvent
from .construction_building_physics_v1 import detect as detect_building_physics
from .construction_building_physics_v1 import route_building_physics_sentence
from .construction_climate_v1 import detect as detect_climate
from .construction_climate_v1 import route_climate_sentence
from .construction_compliance_v1 import detect as detect_compliance
from .construction_failure_v1 import detect as detect_failure
from .construction_materials_v1 import detect as detect_materials
from .construction_materials_v1 import route_materials_sentence
from utils.domain_router import route_construction_sentence

logger = logging.getLogger(__name__)


DEFAULT_CONFIDENCE_RANK = {"low": 1, "med": 2, "medium": 2, "high": 3}
DEFAULT_CONTEXT_RANK = {"weak": 1, "moderate": 2, "strong": 3}


class LensDetector(Protocol):
    def __call__(
        self,
        sentence: str,
        source_type: str = "research_paper",
    ) -> Tuple[Optional[LensEvent], List[dict]]:
        ...


LENS_REGISTRY: Dict[str, LensDetector] = {
    "building_physics": detect_building_physics,
    "climate": detect_climate,
    "compliance": detect_compliance,
    "failure": detect_failure,
    "materials": detect_materials,
}

DEFAULT_CONSTRUCTION_LENS_NAMES = frozenset(LENS_REGISTRY.keys())
DEFAULT_CONSTRUCTION_LENS_ROUTERS = {
    "building_physics": route_building_physics_sentence,
    "climate": route_climate_sentence,
    "materials": route_materials_sentence,
    "compliance": route_construction_sentence,
    "failure": route_construction_sentence,
}


def set_rankings(
    confidence_rank: Optional[Dict[str, int]] = None,
    context_rank: Optional[Dict[str, int]] = None,
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Return ranking maps for detect_multi_lens sorting.

    Pass None for either map to get a copy of that default map.
    """
    return (
        dict(DEFAULT_CONFIDENCE_RANK if confidence_rank is None else confidence_rank),
        dict(DEFAULT_CONTEXT_RANK if context_rank is None else context_rank),
    )

def detect_multi_lens(
    sentence: str,
    source_type: str = "research_paper",
    enabled_lenses: Optional[Union[str, Iterable[str]]] = None,
    confidence_rank: Optional[Dict[str, int]] = None,
    context_rank: Optional[Dict[str, int]] = None,
) -> List[dict]:
    """
    Run all enabled construction lenses and return stacked results for one sentence.

    Args:
        sentence: Input sentence to analyze.
        source_type: Type of source (default: research_paper).
        enabled_lenses: List of lens names to use (default: all).
        confidence_rank: Optional ranking map for confidence sort order.
        context_rank: Optional ranking map for context-strength sort order.

    Returns:
        List of stacked event dicts.

    Notes:
        This core API is intentionally minimal and deterministic.
        Use wrappers for alternate handling modes:
        - detect_multi_lens_raise_on_no_match
        - detect_multi_lens_raise_on_detector_errors
        - detect_multi_lens_return_errors
        - detect_multi_lens_warn_on_no_match
    """
    return _detect_multi_lens_internal(
        sentence=sentence,
        source_type=source_type,
        enabled_lenses=enabled_lenses,
        confidence_rank=confidence_rank,
        context_rank=context_rank,
    )


def _detect_multi_lens_internal(
    sentence: str,
    source_type: str = "research_paper",
    enabled_lenses: Optional[Union[str, Iterable[str]]] = None,
    *,
    raise_on_no_match: bool = False,
    return_errors: bool = False,
    raise_on_detector_errors: bool = False,
    warn_on_no_match: bool = False,
    confidence_rank: Optional[Dict[str, int]] = None,
    context_rank: Optional[Dict[str, int]] = None,
) -> Union[List[dict], Tuple[List[dict], Dict[str, str]]]:
    results: List[dict] = []
    detector_errors = {}

    if isinstance(enabled_lenses, str):
        selected_lenses = [enabled_lenses]
    elif enabled_lenses is not None:
        selected_lenses = list(enabled_lenses)
    else:
        selected_lenses = list(LENS_REGISTRY.keys())

    active_confidence_rank = dict(DEFAULT_CONFIDENCE_RANK if confidence_rank is None else confidence_rank)
    active_context_rank = dict(DEFAULT_CONTEXT_RANK if context_rank is None else context_rank)

    # Validate selected_lenses
    invalid_lenses = [name for name in selected_lenses if name not in LENS_REGISTRY]
    if invalid_lenses:
        raise ValueError(f"Invalid lens name(s): {invalid_lenses}. Valid options: {list(LENS_REGISTRY.keys())}")

    selected_default_lenses = [name for name in selected_lenses if name in DEFAULT_CONSTRUCTION_LENS_NAMES]
    sentence_route = None
    route_decisions = {}
    if selected_default_lenses:
        if any(name in {"compliance", "failure"} for name in selected_default_lenses):
            sentence_route = route_construction_sentence(sentence)
        for name in selected_default_lenses:
            if name in {"compliance", "failure"}:
                route_decisions[name] = sentence_route
            else:
                route_decisions[name] = DEFAULT_CONSTRUCTION_LENS_ROUTERS[name](sentence)
        if all(route_decisions[name].decision == "skip" for name in selected_default_lenses):
            if raise_on_no_match:
                raise RuntimeError("No detector produced results (no match)")
            if warn_on_no_match:
                logger.warning("No detectors matched and no errors reported.")
            else:
                logger.debug("No detectors matched and no errors reported.")
            return ([], detector_errors) if return_errors else []

    for lens_name in selected_lenses:
        detector = LENS_REGISTRY[lens_name]
        try:
            if lens_name in {"compliance", "failure"} and selected_default_lenses:
                event, entities = detector(sentence, source_type=source_type, route_decision=route_decisions[lens_name])
            else:
                event, entities = detector(sentence, source_type=source_type)
        except Exception:
            tb = traceback.format_exc()
            logger.error("Exception in detector '%s':\n%s", lens_name, tb)
            detector_errors[lens_name] = tb
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
            if raise_on_detector_errors:
                raise RuntimeError(f"No detector produced results. Errors: {detector_errors}")
            else:
                logger.error("No detector produced results. Errors: %s", detector_errors)
        if raise_on_no_match:
            raise RuntimeError("No detector produced results (no match)")
        # If return_errors, return both (empty) results and errors
        if not return_errors:
            if warn_on_no_match:
                logger.warning("No detectors matched and no errors reported.")
            else:
                logger.debug("No detectors matched and no errors reported.")
        return ([], detector_errors) if return_errors else []

    # If there are results and also detector_errors, log a warning for partial failures
    if detector_errors and results:
        if raise_on_detector_errors:
            raise RuntimeError(f"Some detectors failed: {detector_errors}")
        logger.warning("Some detectors failed: %r", detector_errors)

    def _ranking_key(item: dict) -> tuple[float, int, int]:
        conf = item.get("confidence", "low")
        if conf not in active_confidence_rank:
            logger.warning(
                "Unexpected confidence value %r for item event_id=%r event_type=%r; defaulting confidence rank to 1",
                conf,
                item.get("event_id"),
                item.get("event_type"),
            )
        context_strength = item.get("context_strength", "weak")
        if context_strength not in active_context_rank:
            logger.warning(
                "Unexpected context_strength value %r for item event_id=%r event_type=%r; defaulting context rank to 1",
                context_strength,
                item.get("event_id"),
                item.get("event_type"),
            )
        return (
            item.get("source_weight", 0.0),
            active_confidence_rank.get(conf, 1),
            active_context_rank.get(context_strength, 1),
        )

    results.sort(
        key=_ranking_key,
        reverse=True,
    )
    return (results, detector_errors) if return_errors else results


def detect_multi_lens_raise_on_no_match(
    sentence: str,
    source_type: str = "research_paper",
    enabled_lenses: Optional[Union[str, Iterable[str]]] = None,
    confidence_rank: Optional[Dict[str, int]] = None,
    context_rank: Optional[Dict[str, int]] = None,
) -> List[dict]:
    return _detect_multi_lens_internal(
        sentence=sentence,
        source_type=source_type,
        enabled_lenses=enabled_lenses,
        raise_on_no_match=True,
        confidence_rank=confidence_rank,
        context_rank=context_rank,
    )


def detect_multi_lens_raise_on_detector_errors(
    sentence: str,
    source_type: str = "research_paper",
    enabled_lenses: Optional[Union[str, Iterable[str]]] = None,
    confidence_rank: Optional[Dict[str, int]] = None,
    context_rank: Optional[Dict[str, int]] = None,
) -> List[dict]:
    return _detect_multi_lens_internal(
        sentence=sentence,
        source_type=source_type,
        enabled_lenses=enabled_lenses,
        raise_on_detector_errors=True,
        confidence_rank=confidence_rank,
        context_rank=context_rank,
    )


def detect_multi_lens_return_errors(
    sentence: str,
    source_type: str = "research_paper",
    enabled_lenses: Optional[Union[str, Iterable[str]]] = None,
    confidence_rank: Optional[Dict[str, int]] = None,
    context_rank: Optional[Dict[str, int]] = None,
) -> Tuple[List[dict], Dict[str, str]]:
    results, detector_errors = _detect_multi_lens_internal(
        sentence=sentence,
        source_type=source_type,
        enabled_lenses=enabled_lenses,
        return_errors=True,
        confidence_rank=confidence_rank,
        context_rank=context_rank,
    )
    return results, detector_errors


def detect_multi_lens_warn_on_no_match(
    sentence: str,
    source_type: str = "research_paper",
    enabled_lenses: Optional[Union[str, Iterable[str]]] = None,
    confidence_rank: Optional[Dict[str, int]] = None,
    context_rank: Optional[Dict[str, int]] = None,
) -> List[dict]:
    return _detect_multi_lens_internal(
        sentence=sentence,
        source_type=source_type,
        enabled_lenses=enabled_lenses,
        warn_on_no_match=True,
        confidence_rank=confidence_rank,
        context_rank=context_rank,
    )


__all__ = [
    "LENS_REGISTRY",
    "detect_building_physics",
    "detect_climate",
    "detect_compliance",
    "detect_failure",
    "detect_materials",
    "set_rankings",
    "detect_multi_lens",
    "detect_multi_lens_raise_on_no_match",
    "detect_multi_lens_raise_on_detector_errors",
    "detect_multi_lens_return_errors",
    "detect_multi_lens_warn_on_no_match",
]

