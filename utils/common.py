# Provide _get_compound_seeds as a wrapper for get_compound_seeds for legacy compatibility
def _get_compound_seeds(SEEDS_DIR=None):
    return get_compound_seeds(SEEDS_DIR)
from pathlib import Path
import tempfile
import hashlib
from datetime import datetime, timezone
from functools import lru_cache


def get_seeds(SEEDS_DIR=None):
    """Return (compounds, targets, models, stopwords) as sets."""
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)

    # If running in a temp directory (test), never fall back to project seeds
    if SEEDS_DIR is None and _is_temp_dir(Path.cwd()):
        return set(), set(), set(), set()

    # If the directory does not exist, do not fall back to bundled seeds
    if not resolved_dir.exists():
        return set(), set(), set(), set()

    compounds = _get_compound_seeds(SEEDS_DIR)
    targets = _get_target_seeds(SEEDS_DIR)
    models = _get_model_seeds(SEEDS_DIR)
    stopwords = _get_stopword_seeds(SEEDS_DIR)
    return compounds, targets, models, stopwords


def _resolve_seeds_dir(SEEDS_DIR=None):
    """Resolve the seeds directory, preferring input/seeds if it exists."""
    if SEEDS_DIR is not None:
        p = Path(SEEDS_DIR)
        return p if p.is_absolute() else (Path.cwd() / p)

    project_root = Path(__file__).resolve().parent.parent
    input_seeds = project_root / "input" / "seeds"
    if input_seeds.exists():
        return input_seeds
    return project_root / "seeds"


def _is_temp_dir(path):
    try:
        temp_root = str(Path(tempfile.gettempdir()).resolve())
        return str(Path(path).resolve()).startswith(temp_root)
    except Exception:
        return False



def get_compound_seeds(SEEDS_DIR=None):
    """Uncached resolver that ensures caching is based on resolved directory string."""
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return _get_compound_seeds_resolved(str(resolved_dir))

@lru_cache(maxsize=32)
def _get_compound_seeds_resolved(resolved_dir_str):
    resolved_dir = Path(resolved_dir_str)
    f = resolved_dir / "base" / "life_sciences" / "compounds.txt"
    if not f.exists():
        return set()
    return load_seed_file(f)


@lru_cache(maxsize=32)
def _get_target_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "base" / "life_sciences" / "targets.txt"
    if not f.exists():
        return set()
    return load_seed_file(f)


@lru_cache(maxsize=32)
def _get_model_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "base" / "life_sciences" / "models.txt"
    if not f.exists():
        return set()
    return load_seed_file(f)


@lru_cache(maxsize=32)
def _get_stopword_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "stopwords.txt"
    if not f.exists():
        return set()
    return load_seed_file(f)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def sha64(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_seed_file(filepath: Path) -> set[str]:
    """Load seed list from file, ignoring comments and empty lines."""
    seeds = set()
    if not filepath.exists():
        print(f"  ⚠️  Seed file not found: {filepath}")
        return seeds

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                seeds.add(line.lower())

    return seeds