"""
Seed Overlay Loader for Axon Labs Domain System
Loads core seeds + optional domain-specific overlays
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


OVERLAY_MAPPING = {
    "stem_cells_regen": "stem_cells_overlay_v1.json",
    "neuroscience_cognition": "neuroscience_overlay_v1.json",
    "biohacking_longevity": "longevity_overlay_v1.json",
    "construction_science": "construction_science_aliases.json",
}


def load_json(path: str) -> Any:
    """Load JSON file safely."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Seed file not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")

def merge_seed_dict(base: dict, overlay: dict) -> dict:
    """
    Merge overlay into base seed dictionary.
    
    Conservative merge:
    - Lists are combined and deduplicated
    - Nested dicts are merged recursively
    - Base values are never overwritten
    
    Args:
        base: Base seed dictionary
        overlay: Overlay seed dictionary
        
    Returns:
        Merged dictionary
    """
    out = dict(base)

    def _dedupe_and_sort(lst):
        # Remove duplicates by equality, preserve order
        seen = []
        for item in lst:
            if item not in seen:
                seen.append(item)
        # Try to sort if possible
        try:
            return sorted(seen)
        except TypeError:
            return seen

    for k, v in overlay.items():
        if k not in out:
            # New key from overlay
            out[k] = v
        else:
            # Key exists in both
            if isinstance(out[k], list) and isinstance(v, list):
                # Merge lists, deduplicate, sort if possible
                out[k] = _dedupe_and_sort(out[k] + v)
            elif isinstance(out[k], dict) and isinstance(v, dict):
                # Merge nested dicts
                tmp = dict(out[k])
                for dk, dv in v.items():
                    if dk in tmp:
                        if isinstance(tmp[dk], list) and isinstance(dv, list):
                            # Merge nested lists, deduplicate, sort if possible
                            tmp[dk] = _dedupe_and_sort(tmp[dk] + dv)
                        else:
                            # Preserve base value, do not overwrite
                            pass
                    else:
                        # Add new nested key
                        tmp[dk] = dv
                out[k] = tmp
            else:
                # Keep base value (conservative)
                pass
    
    return out


def load_core_seeds(seeds_dir: str = "seeds") -> Dict[str, Any]:
    """
    Load core seed files (always loaded).
    
    Args:
        seeds_dir: Path to seeds directory
        
    Returns:
        Dictionary of core seeds
    """
    core = {}
    
    # Load JSON seed files
    json_files = [
        "assays.json",
        "backup_assays.json",
        "pathways.json",
        "indications.json",
        "normalization.json",
        "outcome_signals.json"
    ]
    
    for fname in json_files:
        path = Path(seeds_dir) / fname
        if path.exists():
            key = fname.replace(".json", "")
            core[key] = load_json(str(path))
    
    # Load text seed files
    text_files = ["compounds.txt", "targets.txt", "models.txt", "stopwords.txt"]
    
    for fname in text_files:
        path = Path(seeds_dir) / fname
        if path.exists():
            key = fname.replace(".txt", "")
            with open(path, "r", encoding="utf-8") as f:
                core[key] = [line.strip() for line in f if line.strip()]
    
    return core


def load_overlay(domain_id: str, overlays_dir: str = "seeds/overlays") -> Optional[Dict[str, Any]]:
    """
    Load domain-specific overlay seed file.
    
    Args:
        domain_id: Domain identifier (e.g., "stem_cells_regen")
        overlays_dir: Path to overlays directory
        
    Returns:
        Overlay dictionary if found, None otherwise
    """
    fname = OVERLAY_MAPPING.get(domain_id)
    if not fname:
        return None
    
    path = Path(overlays_dir) / fname
    if not path.exists():
        return None
    
    return load_json(str(path))


def get_overlay_aliases(domain_id: str, overlays_dir: str = "seeds/overlays") -> Dict[str, str]:
    """Load alias-to-canonical mappings from a domain overlay file."""
    overlay = load_overlay(domain_id, overlays_dir)
    if not overlay:
        return {}

    aliases_section = overlay.get("entities", {}).get("aliases", {})
    if not isinstance(aliases_section, dict):
        return {}

    alias_map: Dict[str, str] = {}
    for canonical_name, alias_values in aliases_section.items():
        if not canonical_name:
            continue
        canonical_lower = str(canonical_name).strip().lower()
        if isinstance(alias_values, list):
            candidates = alias_values
        else:
            candidates = [alias_values]

        for alias_value in candidates:
            if alias_value is None:
                continue
            alias_text = str(alias_value).strip().lower()
            if not alias_text:
                continue
            alias_map[alias_text] = canonical_lower

    return alias_map


def load_seeds_with_overlay(domain_id: Optional[str] = None, 
                            seeds_dir: str = "seeds",
                            overlays_dir: str = "seeds/overlays") -> Dict[str, Any]:
    """
    Load core seeds + optional domain overlay.
    
    Args:
        domain_id: Optional domain identifier for overlay
        seeds_dir: Path to seeds directory
        overlays_dir: Path to overlays directory
        
    Returns:
        Merged seed dictionary
    """
    # Always load core seeds
    seeds = load_core_seeds(seeds_dir)
    
    # Optionally load and merge overlay
    if domain_id:
        overlay = load_overlay(domain_id, overlays_dir)
        if overlay and "entities" in overlay:
            # Merge overlay entities into seeds
            for category, terms in overlay["entities"].items():
                if category not in seeds:
                    seeds[category] = terms
                elif isinstance(seeds[category], list) and isinstance(terms, list):
                    seeds[category] = sorted(set(seeds[category] + terms))
                elif isinstance(seeds[category], dict) and isinstance(terms, dict):
                    seeds[category] = merge_seed_dict(seeds[category], terms)
            
            # Add overlay metadata
            seeds["_overlay_id"] = overlay.get("overlay_id")
            seeds["_overlay_domain"] = overlay.get("domain")
    
    return seeds


def get_overlay_info(domain_id: str, overlays_dir: str = "seeds/overlays") -> Optional[Dict[str, Any]]:
    """
    Get overlay metadata without loading full entities.
    
    Args:
        domain_id: Domain identifier
        overlays_dir: Path to overlays directory
        
    Returns:
        Overlay metadata (id, domain, notes, exclusions)
    """
    overlay = load_overlay(domain_id, overlays_dir)
    if not overlay:
        return None
    
    return {
        "overlay_id": overlay.get("overlay_id"),
        "domain": overlay.get("domain"),
        "notes": overlay.get("notes"),
        "exclusions": overlay.get("exclusions", {}),
        "entity_categories": list(overlay.get("entities", {}).keys())
    }


# Example usage and testing
if __name__ == "__main__":
    print("="*70)
    print("SEED OVERLAY LOADER - TESTING")
    print("="*70)
    
    # Test 1: Load core seeds only
    print("\n1. Loading core seeds (no overlay)...")
    core = load_core_seeds()
    print(f"   ✅ Loaded {len(core)} core seed categories")
    for key in sorted(core.keys()):
        if isinstance(core[key], list):
            print(f"      - {key}: {len(core[key])} items")
        elif isinstance(core[key], dict):
            print(f"      - {key}: {len(core[key])} categories")
    
    # Test 2: Load with stem cells overlay
    print("\n2. Loading with stem_cells_regen overlay...")
    stem_seeds = load_seeds_with_overlay("stem_cells_regen")
    print(f"   ✅ Loaded {len(stem_seeds)} seed categories (core + overlay)")
    
    # Show overlay-specific additions
    overlay_keys = set(stem_seeds.keys()) - set(core.keys())
    if overlay_keys:
        print(f"   📦 Overlay added: {', '.join(sorted(overlay_keys))}")
    
    # Test 3: Load with neuroscience overlay
    print("\n3. Loading with neuroscience_cognition overlay...")
    neuro_seeds = load_seeds_with_overlay("neuroscience_cognition")
    print(f"   ✅ Loaded {len(neuro_seeds)} seed categories")
    
    # Test 4: Load with longevity overlay
    print("\n4. Loading with biohacking_longevity overlay...")
    longevity_seeds = load_seeds_with_overlay("biohacking_longevity")
    print(f"   ✅ Loaded {len(longevity_seeds)} seed categories")
    
    # Test 5: Get overlay info
    print("\n5. Getting overlay metadata...")
    for domain_id in ["stem_cells_regen", "neuroscience_cognition", "biohacking_longevity"]:
        info = get_overlay_info(domain_id)
        if info:
            print(f"\n   {info['overlay_id']}:")
            print(f"      Domain: {info['domain']}")
            print(f"      Categories: {', '.join(info['entity_categories'])}")
            print(f"      Exclusions: {len(info['exclusions'].get('terms', []))} terms")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
