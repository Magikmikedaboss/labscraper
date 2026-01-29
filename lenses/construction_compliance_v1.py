# lenses/construction_compliance_v1.py
from __future__ import annotations

import re
from typing import List, Tuple, Optional
from .construction_common import (
    LensEvent, contains_any, has_number, has_unit_signal, make_entity, dedupe_entities
)

# Recognize common standards bodies + some explicit patterns
STD_TOKENS = ["astm", "aci", "asce", "ibc", "iecc", "ashrae", "iso", "en", "eurocode"]
PASS_PHRASES = ["meets", "complies", "in accordance with", "conforms", "satisfies"]
FAIL_PHRASES = ["non-compliant", "does not meet", "fails to meet", "violation"]

def detect(sentence: str) -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    entities: List[dict] = []

    has_std = any(tok in s_l for tok in STD_TOKENS) or bool(re.search(r"\b(astm\s*[a-z]?\s*\d+)\b", s_l))
    has_comp = contains_any(s_l, PASS_PHRASES) or contains_any(s_l, FAIL_PHRASES) or "requirement" in s_l or "standard" in s_l

    if not has_std and not has_comp:
        return None, []

    # Entity: capture standard mention
    # Simple: just tag that a standard exists; you can enrich later to parse exact codes.
    if has_std:
        entities.append(make_entity("code_standard", "STANDARD", "standard", "standard"))

    outcome = "unknown"
    if contains_any(s_l, PASS_PHRASES):
        outcome = "successful"
    if contains_any(s_l, FAIL_PHRASES):
        outcome = "failed"

    score = 0
    if has_std: score += 3
    if has_comp: score += 2
    if has_number(s_l): score += 1
    if has_unit_signal(s_l): score += 1

    conf = "high" if score >= 6 else "med" if score >= 3 else "low"

    tags = ["code_compliance"]
    if outcome == "successful": tags.append("pass")
    if outcome == "failed": tags.append("fail")

    return LensEvent("code_compliance", outcome, conf, tags), dedupe_entities(entities)
