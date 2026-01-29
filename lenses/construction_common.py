from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

# ---------- Basic unit / numeric signals ----------
UNIT_PATTERNS = [
    r"\bmpa\b", r"\bkpa\b", r"\bgpa\b",
    r"\bkn\b", r"\bmn\b",
    r"\bmm\b", r"\bcm\b", r"\bm\b",
    # Removed overly broad 'in' and 'n' patterns to avoid false positives
    r"\bft\b",
    r"\bw/m2k\b", r"\bw/m·k\b", r"\bw/mk\b",
    r"\bwh\b", r"\bkwh\b", r"\bkw\b",
    r"\bpa\b", r"\bppm\b",
    # Improved percent sign detection: match '%' after a digit and followed by whitespace or end-of-string
    r"(?<=\d)%(?=\s|$)", r"\bpercent\b",
    r"\b°c\b", r"\bdegc\b", r"\b°f\b"
]

def has_unit_signal(s_l: str) -> bool:
    return any(re.search(p, s_l) for p in UNIT_PATTERNS)

def has_number(s_l: str) -> bool:
    return bool(re.search(r"\b\d+(\.\d+)?\b", s_l))

def contains_any(s_l: str, phrases: List[str]) -> bool:
    return any(p in s_l for p in phrases)

def wordhit(s_l: str, phrase: str) -> bool:
    return bool(re.search(r"\b" + re.escape(phrase) + r"\b", s_l))

def list_hits(s_l: str, vocab: List[str]) -> List[str]:
    hits = []
    for v in vocab:
        if re.search(r"\b" + re.escape(v) + r"\b", s_l):
            hits.append(v)
    return hits

# ---------- Basic entity builder ----------
def make_entity(entity_type: str, name: str, variant: Optional[str], role: str) -> Dict:
    return {
        "entity_type": entity_type,
        "entity_name": name,
        "entity_variant": variant,
        "role": role,
    }

def dedupe_entities(entities: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for e in entities:
        k = (e["entity_type"], str(e["entity_name"]).lower(), e.get("entity_variant") or "", e.get("role") or "")
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out

@dataclass
class LensEvent:
    event_type: str
    outcome: str
    confidence: str
    tags: List[str]
