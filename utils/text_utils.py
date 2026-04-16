import re
from typing import List

def chunk_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[\.?\!])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]

def guess_stage(sentence_l: str) -> str:
    stage_keywords = {
        "in_vivo": ["in vivo", "mouse", "rat", "animal model"],
        "in_vitro": ["in vitro", "cell line", "cells", "culture"],
        "clinical": ["clinical", "patients", "phase i", "phase ii", "randomized"],
    }
    for stage, keywords in stage_keywords.items():
        for k in keywords:
            if re.search(r'\b' + re.escape(k) + r'\b', sentence_l):
                return stage
    return "unknown"

def guess_section(page_text_l: str) -> str:
    if "methods" in page_text_l and "results" in page_text_l:
        return "mixed"
    if "methods" in page_text_l:
        return "methods"
    if "results" in page_text_l:
        return "results"
    if "discussion" in page_text_l:
        return "discussion"
    return "unknown"
