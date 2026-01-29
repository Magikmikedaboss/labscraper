import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# ----------------------------
# Seed loading
# ----------------------------

def load_text_seed_file(path: Path) -> list:
    """
    Loads a text file and returns a list of non-empty, stripped lines.
    """
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def load_seed_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def load_seeds(seeds_dir: str = "seeds") -> Dict[str, dict]:
    """
    Loads all *.json seed files in ./seeds and base ontology text files.
    Returns a dict like {"assays": {...}, "pathways": {...}, ...}
    """
    d = {}
    p = Path(seeds_dir)
    if not p.exists():
        return d

    # Store JSON seeds and ontology seeds under separate top-level keys
    d['json_seeds'] = {}
    d['ontology_seeds'] = {}

    # Load JSON seed files (existing behavior)
    for fp in p.glob("*.json"):
        key = fp.stem
        d['json_seeds'][key] = load_seed_file(fp)

    # Load base ontology text files (new for multi-ontology support)
    base_dir = p / "base"
    if base_dir.exists():
        for ontology_dir in base_dir.glob("*"):
            if ontology_dir.is_dir():
                ontology_name = ontology_dir.name
                if ontology_name not in d['ontology_seeds']:
                    d['ontology_seeds'][ontology_name] = {}
                for txt_file in ontology_dir.glob("*.txt"):
                    entity_type = txt_file.stem
                    # Check for collision with JSON seeds
                    if (
                        ontology_name in d['json_seeds']
                        and entity_type in d['json_seeds'][ontology_name]
                    ):
                        import warnings
                        warnings.warn(
                            f"Ontology seed '{ontology_name}/{entity_type}' collides with JSON seed. Both are preserved under separate namespaces."
                        )
                    d['ontology_seeds'][ontology_name][entity_type] = load_text_seed_file(txt_file)

    return d

# ----------------------------
# Helpers
# ----------------------------

def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()

def contains_any(hay: str, needles: List[str]) -> bool:
    h = hay.lower()
    return any(n.lower() in h for n in needles)

@dataclass(frozen=True)
class Entity:
    entity_type: str     # compound | target | model | assay | pathway | indication | stem_cell | peptide_class
    entity_name: str     # canonical label
    entity_variant: str  # optional: organism/biofluid/cell_line/etc
    confidence: float    # 0..1
    source: str          # "dict" | "regex"

# ----------------------------
# Extraction
# ----------------------------

def extract_entities(text: str, seeds: Dict[str, dict]) -> List[Entity]:
    """
    Extract typed entities from a text blob (snippet, title+snippet, etc.)
    """
    if not text:
        return []

    t = norm(text)
    out: List[Entity] = []

    # --- ASSAYS
    assays = seeds.get("assays", {})
    for a in assays.get("assays", []):
        if a.lower() in t:
            out.append(Entity("assay", a, "assay", 0.85, "dict"))
    for m in assays.get("metrics", []):
        if m.lower() in t:
            out.append(Entity("assay", m, "metric", 0.70, "dict"))

    # --- PATHWAYS
    pathways = seeds.get("pathways", {})
    for p in pathways.get("pathways", []):
        if p.lower() in t:
            out.append(Entity("pathway", p, "pathway", 0.80, "dict"))

    # --- INDICATIONS
    indications = seeds.get("indications", {})
    for ind in indications.get("indications", []):
        if ind.lower() in t:
            out.append(Entity("indication", ind, "disease", 0.75, "dict"))

    # --- STEM CELLS (from existing seeds if available)
    # We'll handle this in the main scraper since we already have stem cell extraction

    # --- MODELS (organisms, biofluids, cell lines)
    # We'll handle this in the main scraper since we already have model extraction

    # --- TARGETS
    # We'll handle this in the main scraper since we already have target extraction

    # --- COMPOUNDS
    # We'll handle this in the main scraper since we already have compound extraction

    # --- DEDUPE (by type+name+variant)
    dedup = {}
    for e in out:
        k = (e.entity_type, e.entity_name, e.entity_variant)
        # keep max confidence
        if k not in dedup or e.confidence > dedup[k].confidence:
            dedup[k] = e

    return list(dedup.values())

# ----------------------------
# Confidence scoring for the EVENT
# ----------------------------

def score_event_confidence(entities: List[Entity], text: str, seeds: Dict[str, dict]) -> Tuple[str, float]:
    """
    Returns (label, score) where score is 0..1 and label in {"low","med","high"}.
    """
    if not text:
        return ("low", 0.0)

    t = norm(text)

    # Base score from entity presence
    score = 0.0
    type_weights = {
        "compound": 0.30,
        "target": 0.30,
        "assay": 0.20,
        "model": 0.10,
        "pathway": 0.15,
        "indication": 0.10,
        "stem_cell": 0.20,
        "peptide_class": 0.05,
    }

    seen_types = set()
    for e in entities:
        score += type_weights.get(e.entity_type, 0.05) * min(1.0, e.confidence)
        seen_types.add(e.entity_type)

    # Boost if multiple "high signal" cues appear
    boosts = 0.0
    assays = seeds.get("assays", {})
    if contains_any(t, assays.get("metrics", [])):
        boosts += 0.10
    if contains_any(t, ["lc-ms", "lc-ms/ms", "spr", "bli", "triple quadrupole", "quantitation"]):
        boosts += 0.10
    if contains_any(t, ["in vivo", "clinical", "randomized", "phase i", "phase ii"]):
        boosts += 0.10

    score = min(1.0, score + boosts)

    # Labeling
    if score >= 0.75:
        return ("high", score)
    if score >= 0.45:
        return ("med", score)
    return ("low", score)
