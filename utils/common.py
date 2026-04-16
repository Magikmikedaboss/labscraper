# ---------------------------------------------------------
# UTILS
# ---------------------------------------------------------
def _is_temp_dir(path):
    try:
        temp_root = Path(tempfile.gettempdir()).resolve()
        path_obj = Path(path).resolve()
        # Python 3.9+: use is_relative_to; fallback for older
        try:
            return path_obj == temp_root or temp_root in path_obj.parents
        except Exception:
            # Fallback for Python <3.9
            return str(temp_root) == str(path_obj) or str(temp_root) in [str(p) for p in path_obj.parents]
    except Exception:
        return False

# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------
from pathlib import Path
import tempfile
import hashlib
from datetime import datetime, timezone
from functools import lru_cache
from typing import Set

# ---------------------------------------------------------
# LEGACY WRAPPERS (for backward compatibility)
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
    """Return (compounds, targets, models, stopwords) as sets."""
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)

    # Prevent accidental fallback during tests
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
# PATH RESOLUTION
# ---------------------------------------------------------
def _resolve_seeds_dir(SEEDS_DIR=None):
    """Resolve the seeds directory, preferring input/seeds if it exists."""
    if SEEDS_DIR is not None:
        p = Path(SEEDS_DIR)
        return p if p.is_absolute() else (Path.cwd() / p)
    # Always resolve relative to the labscraper project root
    for parent in Path.cwd().parents:
        if (parent / "seeds" / "base" / "life_sciences").exists():
            return parent / "seeds" / "base" / "life_sciences"
    # Fallback: assume cwd is project root
    return Path.cwd() / "seeds" / "base" / "life_sciences"


# ---------------------------------------------------------
# SEED LOADERS (CONSISTENT CACHING)
# ---------------------------------------------------------
def get_compound_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "compounds.txt"
    seeds = _get_compound_seeds_resolved(str(resolved_dir))
    print(f"[DEBUG] get_compound_seeds: loading {f}, exists={f.exists()}, count={len(seeds)}")
    return seeds


@lru_cache(maxsize=32)
def _get_compound_seeds_resolved(resolved_dir_str):
    resolved_dir = Path(resolved_dir_str)
    f = resolved_dir / "compounds.txt"
    if not f.exists():
        return set()
    return load_seed_file(f, case="upper")


def get_target_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "targets.txt"
    seeds = _get_target_seeds_resolved(str(resolved_dir))
    print(f"[DEBUG] get_target_seeds: loading {f}, exists={f.exists()}, count={len(seeds)}")
    return seeds


@lru_cache(maxsize=32)
def _get_target_seeds_resolved(resolved_dir_str):
    resolved_dir = Path(resolved_dir_str)
    f = resolved_dir / "targets.txt"
    if not f.exists():
        return set()
    return load_seed_file(f, case="upper")


def get_model_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "models.txt"
    seeds = _get_model_seeds_resolved(str(resolved_dir))
    print(f"[DEBUG] get_model_seeds: loading {f}, exists={f.exists()}, count={len(seeds)}")
    return seeds


@lru_cache(maxsize=32)
def _get_model_seeds_resolved(resolved_dir_str):
    resolved_dir = Path(resolved_dir_str)
    f = resolved_dir / "models.txt"
    if not f.exists():
        return set()
    return load_seed_file(f, case="upper")


def get_stopword_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return _get_stopword_seeds_resolved(str(resolved_dir))


@lru_cache(maxsize=32)
def _get_stopword_seeds_resolved(resolved_dir_str):
    resolved_dir = Path(resolved_dir_str)
    f = resolved_dir / "stopwords.txt"
    if not f.exists():
        return set()
    return load_seed_file(f)


# ---------------------------------------------------------
# UTILS
# ---------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def sha64(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_seed_file(filepath: Path, case: str) -> Set[str]:
    """Load seed list from file, ignoring comments and empty lines.
    case: 'upper', 'lower', or None (no change)
    """
    seeds = set()

    if not filepath.exists():
        print(f"  ⚠️  Seed file not found: {filepath}")
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