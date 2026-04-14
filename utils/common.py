
import functools
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Lazy-loaded seed file caches
def _resolve_seeds_dir(SEEDS_DIR=None):
    """Resolve the seeds directory, preferring input/seeds if it exists."""
    if SEEDS_DIR is not None:
        return SEEDS_DIR
    project_root = Path(__file__).resolve().parent.parent
    input_seeds = project_root / 'input' / 'seeds'
    if input_seeds.exists():
        return input_seeds
    return project_root / 'seeds'

@functools.lru_cache(maxsize=1)
def _get_compound_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return load_seed_file(resolved_dir / "base/life_sciences/compounds.txt")

@functools.lru_cache(maxsize=1)
def _get_target_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return load_seed_file(resolved_dir / "base/life_sciences/targets.txt")

@functools.lru_cache(maxsize=1)
def _get_model_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return load_seed_file(resolved_dir / "base/life_sciences/models.txt")

@functools.lru_cache(maxsize=1)
def _get_stopword_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    return load_seed_file(resolved_dir / "stopwords.txt")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def sha64(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_seed_file(filepath: Path) -> set:
    """Load seed list from file, ignoring comments and empty lines"""
    seeds = set()
    if not filepath.exists():
        print(f"  ⚠️  Seed file not found: {filepath}")
        return seeds
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                seeds.add(line.lower())
    return seeds
