import re
from typing import List

def chunk_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[\.?\!])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]

def guess_stage(sentence_l: str) -> str:
    if any(k in sentence_l for k in ["in vivo", "mouse", "rat", "animal model"]):
        return "in_vivo"
    if any(k in sentence_l for k in ["in vitro", "cell line", "cells", "culture"]):
        return "in_vitro"
    if any(k in sentence_l for k in ["clinical", "patients", "phase i", "phase ii", "randomized"]):
        return "clinical"
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
