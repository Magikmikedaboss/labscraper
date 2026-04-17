from pathlib import Path
import tempfile
import hashlib
from datetime import datetime, timezone
from functools import lru_cache
from typing import Set
import warnings

# ---------------------------------------------------------
# HASHING
# ---------------------------------------------------------
def sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def sha64(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------
# UTILS
# ---------------------------------------------------------
def _is_temp_dir(path):
    try:
        temp_root = Path(tempfile.gettempdir()).resolve()
        path_obj = Path(path).resolve()
        return path_obj == temp_root or temp_root in path_obj.parents
    except Exception:
        return False


# ---------------------------------------------------------
# LEGACY WRAPPERS
# ---------------------------------------------------------
def _get_compound_seeds(SEEDS_DIR=None):
    return get_compound_seeds(SEEDS_DIR)

def _get_target_seeds(SEEDS_DIR=None):
    return get_target_seeds(SEEDS_DIR)

def _get_model_seeds(SEEDS_DIR=None):
    return get_model_seeds(SEEDS_DIR)


# ---------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------
def get_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)

    if SEEDS_DIR is None and _is_temp_dir(Path.cwd()):
        return set(), set(), set(), set()

    if not resolved_dir.exists():
        return set(), set(), set(), set()

    return (
        get_compound_seeds(SEEDS_DIR),
        get_target_seeds(SEEDS_DIR),
        get_model_seeds(SEEDS_DIR),
        get_stopword_seeds(SEEDS_DIR),
    )


# ---------------------------------------------------------
# PATH RESOLUTION (FIXED)
# ---------------------------------------------------------
# Helper for seeds root normalization
def _normalize_seeds_root(resolved: Path) -> Path:
    """If path ends with base/life_sciences, return grandparent, else resolved."""
    if len(resolved.parts) >= 2 and resolved.parts[-2:] == ("base", "life_sciences"):
        return resolved.parent.parent.resolve()
    return resolved

def _resolve_seeds_dir(SEEDS_DIR=None):


    if SEEDS_DIR:
        p = Path(SEEDS_DIR)
        if p.exists():
            resolved = p.resolve()
            return _normalize_seeds_root(resolved)

        p2 = Path.cwd() / p
        if p2.exists():
            resolved = p2.resolve()
            return _normalize_seeds_root(resolved)

        warnings.warn(f"Provided SEEDS_DIR '{SEEDS_DIR}' not found as absolute or relative path; falling back to auto-discovery.")

    # Walk up directories to find /seeds
    for parent in [Path.cwd()] + list(Path.cwd().parents):
        candidate = parent / "seeds"
        if candidate.exists():
            return candidate.resolve()

    return (Path.cwd() / "seeds").resolve()


# ---------------------------------------------------------
# SEED LOADERS
# ---------------------------------------------------------
def get_compound_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return _get_compound_seeds_resolved(str(resolved_dir))


@lru_cache(maxsize=32)
def _get_compound_seeds_resolved(resolved_dir_str):
    f = Path(resolved_dir_str) / "base" / "life_sciences" / "compounds.txt"
    if not f.exists():
        return set()
    return load_seed_file(f, case="upper")


def get_target_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return _get_target_seeds_resolved(str(resolved_dir))


@lru_cache(maxsize=32)
def _get_target_seeds_resolved(resolved_dir_str):
    f = Path(resolved_dir_str) / "base" / "life_sciences" / "targets.txt"
    if not f.exists():
        return set()
    return load_seed_file(f, case="upper")


def get_model_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return _get_model_seeds_resolved(str(resolved_dir))


@lru_cache(maxsize=32)
def _get_model_seeds_resolved(resolved_dir_str):
    f = Path(resolved_dir_str) / "base" / "life_sciences" / "models.txt"
    if not f.exists():
        return set()
    return load_seed_file(f, case="upper")


def get_stopword_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return _get_stopword_seeds_resolved(str(resolved_dir))


@lru_cache(maxsize=32)
def _get_stopword_seeds_resolved(resolved_dir_str):
    # Try base/life_sciences/stopwords.txt first
    f = Path(resolved_dir_str) / "base" / "life_sciences" / "stopwords.txt"
    if f.exists():
        return load_seed_file(f)
    # Fallback: seeds/stopwords.txt (for test compatibility)
    f2 = Path(resolved_dir_str) / "stopwords.txt"
    if f2.exists():
        return load_seed_file(f2)
    return set()


# ---------------------------------------------------------
# TIME
# ---------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ---------------------------------------------------------
# FILE LOADER
# ---------------------------------------------------------
def load_seed_file(filepath: Path, case: str = None) -> Set[str]:
    seeds = set()

    if not filepath.exists():
        print(f"⚠️ Seed file not found: {filepath}")
        return seeds

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if case == "upper":
                    seeds.add(line.upper())
                elif case == "lower":
                    seeds.add(line.lower())
                else:
                    seeds.add(line)

    return seeds