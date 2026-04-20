import re
from typing import List

def chunk_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[\.?\!])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]

def guess_stage(sentence_l: str) -> str:
    sentence = (sentence_l or "").lower()
    stage_keywords = {
        "in_vivo": ["in vivo", "mouse", "rat", "animal model"],
        "in_vitro": ["in vitro", "cell line", "cells", "culture"],
        "clinical": ["clinical", "patients", "phase i", "phase ii", "randomized"],
    }
    for stage, keywords in stage_keywords.items():
        for k in keywords:
            if re.search(r'\b' + re.escape(k) + r'\b', sentence):
                return stage
    return "unknown"

def guess_section(page_text: str) -> str:
    page_text = (page_text or "").lower()
    # Use word-boundary regex to avoid false matches (e.g., 'methodology')
    has_methods = re.search(r'\bmethods\b', page_text)
    has_results = re.search(r'\bresults\b', page_text)
    has_discussion = re.search(r'\bdiscussion\b', page_text)
    if has_methods and has_results:
        return "mixed"
    if has_methods:
        return "methods"
    if has_results:
        return "results"
    if has_discussion:
        return "discussion"
    return "unknown"
