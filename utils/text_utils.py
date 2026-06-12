
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

def _mask_sentence_fragments(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    token_index = 0

    def replace_with_token(match: re.Match[str]) -> str:
        nonlocal token_index
        token = f"<mask{token_index}>"
        token_index += 1
        replacements[token] = match.group(0)
        return token

    def replace_url_with_token(match: re.Match[str]) -> str:
        nonlocal token_index
        matched = match.group(0)
        suffix = ""
        if matched and matched[-1] in ".!?":
            suffix = matched[-1]
            matched = matched[:-1]
        token = f"<mask{token_index}>"
        token_index += 1
        replacements[token] = matched
        return f"{token}{suffix}"

    def replace_ellipsis_with_token(match: re.Match[str]) -> str:
        nonlocal token_index
        token = f"<mask{token_index}>"
        token_index += 1
        replacements[token] = match.group(0)
        return f"{token}."

    text = re.sub(r"\b(?:https?://|www\.)[^\s\)\}\]\.\'\"`]+", replace_url_with_token, text)
    text = re.sub(r"\.\.\.", replace_ellipsis_with_token, text)
    text = re.sub(r"(?<=\d)\.(?=\d)", replace_with_token, text)
    return text, replacements


def _unmask_sentence_fragments(text: str, replacements: dict[str, str]) -> str:
    for token, original in replacements.items():
        if original == "...":
            text = text.replace(f"{token}.", original)
        text = text.replace(token, original)
    return text

def chunk_sentences(text: str) -> List[str]:
    """Split text into sentences while preserving common abbreviations.

    _mask_sentence_fragments() masks URLs, ellipses, and decimal numbers before
    splitting, and ABBREV_MAP temporarily masks common abbreviations as part of
    the same boundary-detection pass. _unmask_sentence_fragments() restores the
    original text afterward. This masking reduces sentence-boundary errors, but
    rare edge cases may still remain.
    """
    norm = text.replace("\n", " ")
    norm, fragment_masks = _mask_sentence_fragments(norm)
    for abbr, mask in ABBREV_MAP.items():
        norm = norm.replace(abbr, mask)
    parts = re.split(r"(?<=[\.!?])\s+", norm)
    # Unmask abbreviations and temporary sentence fragment masks
    def unmask(s):
        s = _unmask_sentence_fragments(s, fragment_masks)
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
    # "mixed_discussion" means all three major sections are present, not just methods+results.
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
