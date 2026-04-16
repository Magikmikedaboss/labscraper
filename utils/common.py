import hashlib
from datetime import datetime, timezone
from pathlib import Path
import tempfile

# Lazy-loaded seed file caches
def _resolve_seeds_dir(SEEDS_DIR=None):
    """Resolve the seeds directory, preferring input/seeds if it exists. If SEEDS_DIR is absolute, use as is."""
    if SEEDS_DIR is not None:
        p = Path(SEEDS_DIR)
        return p if p.is_absolute() else (Path.cwd() / p)
    project_root = Path(__file__).resolve().parent.parent
    input_seeds = project_root / 'input' / 'seeds'
    if input_seeds.exists():
        return input_seeds
    return project_root / 'seeds'

def _is_temp_dir(path):
    try:
        temp_root = str(Path(tempfile.gettempdir()).resolve())
        return str(Path(path).resolve()).startswith(temp_root)
    except Exception:
        return False

def _get_compound_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "base/life_sciences/compounds.txt"
    # If SEEDS_DIR is provided, never fall back to bundled seeds
    # If running in a temp dir and no seeds dir exists, do not fall back to bundled seeds
    if not f.exists():
        if SEEDS_DIR is None:
            if _is_temp_dir(Path.cwd()) and not (Path.cwd() / 'seeds').exists() and not (Path.cwd() / 'input' / 'seeds').exists():
                return set()
            project_root = Path(__file__).resolve().parent.parent
            bundled = project_root / 'seeds' / "base/life_sciences/compounds.txt"
            if bundled.exists():
                return load_seed_file(bundled)
        return set()
    return load_seed_file(f)

def _get_target_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "base/life_sciences/targets.txt"
    if not f.exists():
        if SEEDS_DIR is None:
            if _is_temp_dir(Path.cwd()) and not (Path.cwd() / 'seeds').exists() and not (Path.cwd() / 'input' / 'seeds').exists():
                return set()
            project_root = Path(__file__).resolve().parent.parent
            bundled = project_root / 'seeds' / "base/life_sciences/targets.txt"
            if bundled.exists():
                return load_seed_file(bundled)
        return set()
    return load_seed_file(f)

def _get_model_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "base/life_sciences/models.txt"
    if not f.exists():
        if SEEDS_DIR is None:
            if _is_temp_dir(Path.cwd()) and not (Path.cwd() / 'seeds').exists() and not (Path.cwd() / 'input' / 'seeds').exists():
                return set()
            project_root = Path(__file__).resolve().parent.parent
            bundled = project_root / 'seeds' / "base/life_sciences/models.txt"
            if bundled.exists():
                return load_seed_file(bundled)
        return set()
    return load_seed_file(f)

def _get_stopword_seeds(SEEDS_DIR=None):
    resolved_dir = _resolve_seeds_dir(SEEDS_DIR)
    f = resolved_dir / "stopwords.txt"
    if not f.exists():
        if SEEDS_DIR is None:
            if _is_temp_dir(Path.cwd()) and not (Path.cwd() / 'seeds').exists() and not (Path.cwd() / 'input' / 'seeds').exists():
                return set()
            project_root = Path(__file__).resolve().parent.parent
            bundled = project_root / 'seeds' / "stopwords.txt"
            if bundled.exists():
                return load_seed_file(bundled)
        return set()
    return load_seed_file(f)

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
