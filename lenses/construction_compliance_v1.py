# lenses/construction_compliance_v1.py
from __future__ import annotations

import re
from typing import List, Tuple, Optional
from .construction_common import (
    LensEvent, build_lens_event, contains_any, has_number, has_unit_signal, make_entity, dedupe_entities
)

# Recognize common standards bodies + some explicit patterns
STD_TOKENS = ["astm", "aci", "asce", "ibc", "iecc", "ashrae", "iso", "eurocode"]
PASS_PHRASES = ["meets", "complies", "complied with", "in accordance with", "conforms", "satisfies"]
FAIL_PHRASES = ["non-compliant", "noncompliant", "does not meet", "did not comply", "fails to meet", "violation"]

def detect(sentence: str, source_type: str = "research_paper") -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    entities: List[dict] = []

    std_match = re.search(r"\b(astm\s*[a-z]?\s*\d+|aci\s*\d+|asce\s*\d+|iso\s*\d+|eurocode\s*\d+|ibc\s*\d+|iecc\s*\d+|ashrae\s*[\d.]+)\b", s_l)
    has_std = any(tok in s_l for tok in STD_TOKENS) or bool(std_match)
    has_comp = contains_any(s_l, PASS_PHRASES) or contains_any(s_l, FAIL_PHRASES) or "requirement" in s_l or "standard" in s_l

    if not has_std and not has_comp:
        return None, []

    # Entity: capture actual standard if present
    if std_match:
        std_name = std_match.group(1).upper()
        entities.append(make_entity("code_standard", std_name, "standard", "standard"))
    elif has_std:
        entities.append(make_entity("code_standard", "STANDARD", "standard", "standard"))

    outcome = "neutral"
    # Pass overrides fail in mixed-signal sentences to treat any affirmative indication as a success.
    # If both pass and fail phrases are present, pass takes precedence.
    if contains_any(s_l, PASS_PHRASES):
        outcome = "successful"
    elif contains_any(s_l, FAIL_PHRASES):
        outcome = "failed"

    score = 0
    if has_std:
        score += 3
    if has_comp:
        score += 2
    if has_number(s_l):
        score += 1
    if has_unit_signal(s_l):
        score += 1

    conf = "high" if score >= 6 else "med" if score >= 3 else "low"

    tags = ["code_compliance"]
    if outcome == "successful":
        tags.append("pass")
    if outcome == "failed":
        tags.append("fail")

    return build_lens_event("compliance", "code_compliance", outcome, conf, tags, sentence, source_type), dedupe_entities(entities)
