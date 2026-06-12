from pathlib import Path
import tempfile
import hashlib
import logging
from datetime import datetime, timezone
from typing import Set, Union
import warnings

# ---------------------------------------------------------
# HASHING
# ---------------------------------------------------------

def _to_bytes(s: Union[str, bytes]) -> bytes:
    """Convert input to bytes for hashing."""
    if isinstance(s, bytes):
        return s
    return s.encode("utf-8")

def sha256_short_unsafe(s: Union[str, bytes]) -> str:
    """Return the first 16 hex chars of SHA-256.

    Warning: this is a 64-bit truncation and has a materially higher collision
    risk than the full digest. Use only when a short, non-security identifier
    is acceptable.
    """
    data = _to_bytes(s)
    return hashlib.sha256(data).hexdigest()[:16]


def sha256_short(s: Union[str, bytes]) -> str:
    """Deprecated wrapper for sha256_short_unsafe.

    Prefer :func:`sha256_short_unsafe` for new code.
    """
    warnings.warn(
        "sha256_short is deprecated; use sha256_short_unsafe instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return sha256_short_unsafe(s)

def sha256_hex(s: Union[str, bytes]) -> str:
    """Return the full SHA-256 hex digest of input."""
    data = _to_bytes(s)
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------
# UTILS
# ---------------------------------------------------------
def is_temp_dir(path):
    try:
        temp_root = Path(tempfile.gettempdir()).resolve()
        path_obj = Path(path).resolve()
        return path_obj == temp_root or temp_root in path_obj.parents
    except (OSError, ValueError, RuntimeError):
        return False




# ---------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------
def get_seeds(SEEDS_DIR=None):
    empty = {
        "compounds": set(),
        "targets": set(),
        "models": set(),
        "stopwords": set(),
    }

    if SEEDS_DIR is None and is_temp_dir(Path.cwd()):
        logging.warning("Skipping seed loading because SEEDS_DIR is None and Path.cwd() is a temp dir: %s", Path.cwd())
        return empty

    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)

    if not resolved_dir.exists():
        return empty

    return {
        "compounds": get_compound_seeds(resolved_dir),
        "targets": get_target_seeds(resolved_dir),
        "models": get_model_seeds(resolved_dir),
        "stopwords": get_stopword_seeds(resolved_dir),
    }


# ---------------------------------------------------------
# PATH RESOLUTION (FIXED)
# ---------------------------------------------------------
# Helper for seeds root normalization
def _normalize_seeds_root(resolved: Path, suffix: tuple[str, ...] = ("base", "life_sciences")) -> Path:
    """Normalize a seeds directory root when it ends with a known project suffix.

    Example: ``/repo/seeds/base/life_sciences`` -> ``/repo/seeds``
    """
    if not suffix:
        return resolved
    if suffix and len(resolved.parts) >= len(suffix) and resolved.parts[-len(suffix):] == suffix:
        return resolved.parents[len(suffix) - 1].resolve()
    return resolved

def _resolve_seeds_dir(SEEDS_DIR=None):
    if SEEDS_DIR:
        p = Path(SEEDS_DIR)
        if p.exists():
            resolved = p.resolve()
            return _normalize_seeds_root(resolved, suffix=("base", "life_sciences"))

        p2 = Path.cwd() / p
        if p2.exists():
            resolved = p2.resolve()
            return _normalize_seeds_root(resolved, suffix=("base", "life_sciences"))

        logging.warning(f"Provided SEEDS_DIR '{SEEDS_DIR}' not found as absolute or relative path; falling back to auto-discovery.")

    # Walk up directories to find /seeds
    for parent in [Path.cwd()] + list(Path.cwd().parents):
        candidate = parent / "seeds"
        if candidate.exists():
            return candidate.resolve()

    return (Path.cwd() / "seeds").resolve()


# ---------------------------------------------------------
# SEED LOADERS
# ---------------------------------------------------------
def get_compound_seeds(resolved_dir=None):
    resolved = _resolve_seeds_dir(resolved_dir)
    return _get_compound_seeds_resolved(str(resolved))


def _get_compound_seeds_resolved(resolved_dir_str):
    f = Path(resolved_dir_str) / "base" / "life_sciences" / "compounds.txt"
    if not f.exists():
        return set()
    return load_seed_file(f, case="upper")


def get_target_seeds(resolved_dir=None):
    resolved = _resolve_seeds_dir(resolved_dir)
    return _get_target_seeds_resolved(str(resolved))


def _get_target_seeds_resolved(resolved_dir_str):
    f = Path(resolved_dir_str) / "base" / "life_sciences" / "targets.txt"
    if not f.exists():
        return set()
    return load_seed_file(f, case="upper")


def get_model_seeds(resolved_dir=None):
    resolved = _resolve_seeds_dir(resolved_dir)
    return _get_model_seeds_resolved(str(resolved))


def _get_model_seeds_resolved(resolved_dir_str):
    f = Path(resolved_dir_str) / "base" / "life_sciences" / "models.txt"
    if not f.exists():
        return set()
    return load_seed_file(f, case="upper")


def get_stopword_seeds(resolved_dir=None):
    resolved = _resolve_seeds_dir(resolved_dir)
    return _get_stopword_seeds_resolved(str(resolved))


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
        warnings.warn(f"Seed file not found: {filepath}", stacklevel=2)
        return seeds

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            comment_index = None
            for idx, char in enumerate(line):
                if char == "#" and (idx == 0 or line[idx - 1].isspace()):
                    comment_index = idx
                    break
            line = line[:comment_index].strip() if comment_index is not None else line.strip()
            if not line:
                continue
            if case == "upper":
                seeds.add(line.upper())
            elif case == "lower":
                seeds.add(line.lower())
            else:
                seeds.add(line)

    return seeds