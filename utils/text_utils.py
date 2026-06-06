
import re
from typing import List

# Module-level abbreviation map for sentence chunking
ABBREV_MAP = {
    "Dr.": "Dr<dot>",
    "Mr.": "Mr<dot>",
    "Mrs.": "Mrs<dot>",
    "Ms.": "Ms<dot>",
    "Prof.": "Prof<dot>",
    "et al.": "et al<dot>",
    "i.e.": "i<dot>e<dot>",
    "e.g.": "e<dot>g<dot>",
    "Fig.": "Fig<dot>",
    "vs.": "vs<dot>",
}

def chunk_sentences(text: str) -> List[str]:
    # Protect common abbreviations from being split
    norm = text.replace("\n", " ")
    for abbr, mask in ABBREV_MAP.items():
        norm = norm.replace(abbr, mask)
    parts = re.split(r"(?<=[\.!?])\s+", norm)
    # Unmask abbreviations
    def unmask(s):
        for abbr, mask in ABBREV_MAP.items():
            s = s.replace(mask, abbr)
        return s
    return [unmask(p).strip() for p in parts if p.strip()]

def guess_stage(sentence_l: str) -> str:
    sentence = (sentence_l or "").lower()
    # Priority order: clinical > in_vivo > in_vitro
    stage_keywords = {
        "clinical": ["clinical", "patients", "phase i", "phase ii", "randomized"],
        "in_vivo": ["in vivo", "mouse", "rat", "animal model"],
        "in_vitro": ["in vitro", "cell line", "cell culture", "primary cells", "cell assay"],
    }
    for stage in ["clinical", "in_vivo", "in_vitro"]:
        for k in stage_keywords[stage]:
            if re.search(r'\b' + re.escape(k) + r'\b', sentence):
                return stage
    return "unknown"

def guess_section(page_text: str) -> str:
    page_text = (page_text or "").lower()
    # Use word-boundary regex to avoid false matches (e.g., 'methodology')
    has_methods = re.search(r'\bmethods\b', page_text)
    has_results = re.search(r'\bresults\b', page_text)
    has_discussion = re.search(r'\bdiscussion\b', page_text)
    if has_methods and has_results and has_discussion:
        return "mixed_discussion"
    if has_methods and has_results:
        return "mixed"
    if has_methods:
        return "methods"
    if has_results:
        return "results"
    if has_discussion:
        return "discussion"
    return "unknown"
