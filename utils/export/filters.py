from __future__ import annotations

from typing import Optional, Iterable, Mapping
from pathlib import Path
import csv
import json
import os
import re

DEFAULT_KNOWN_PEPTIDES = {
    "ETELCALCETIDE",
    "PLECANATIDE",
    "TERIPARATIDE",
    "OCTREOTIDE",
    "LANREOTIDE",
    "PASIREOTIDE",
    "SOMATOSTATIN",
}

KNOWN_PEPTIDES_ENV_VAR = "LABSCRAPER_KNOWN_PEPTIDES"
KNOWN_PEPTIDES_FILE_ENV_VAR = "LABSCRAPER_KNOWN_PEPTIDES_FILE"
DEFAULT_KNOWN_PEPTIDES_FILE = Path(__file__).resolve().parents[2] / "seeds" / "domain" / "peptides.txt"


def _normalize_peptide_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().upper()
    return token or None


def _iter_peptide_candidates(payload: object) -> Iterable[object]:
    if payload is None:
        return []
    if isinstance(payload, dict):
        for key in ("peptides", "known_peptides", "values"):
            if key in payload:
                return _iter_peptide_candidates(payload[key])
        return payload.values()
    if isinstance(payload, str):
        return [part for part in re.split(r"[\n,;]+", payload) if part.strip()]
    if isinstance(payload, (list, tuple, set)):
        return payload
    return []


def _load_peptides_from_file(path: Path) -> set[str] | None:
    if not path.exists() or not path.is_file():
        return None

    try:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            candidates = _iter_peptide_candidates(payload)
        elif path.suffix.lower() == ".csv":
            candidates = []
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    if row:
                        candidates.append(row[0])
        elif path.suffix.lower() in {".yml", ".yaml"}:
            try:
                import yaml  # type: ignore
            except Exception:
                return None
            try:
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                return None
            candidates = _iter_peptide_candidates(payload)
        else:
            candidates = path.read_text(encoding="utf-8").splitlines()
    except (OSError, TypeError, ValueError, json.JSONDecodeError, csv.Error):
        return None

    normalized = {
        token
        for token in (_normalize_peptide_value(candidate) for candidate in candidates)
        if token
    }
    return normalized or None


def load_known_peptides(
    config_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> set[str]:
    """Load export peptide allowlist from config or env, with safe defaults."""
    env_map = env or os.environ

    raw_env_peptides = env_map.get(KNOWN_PEPTIDES_ENV_VAR, "").strip()
    if raw_env_peptides:
        normalized = {
            token
            for token in (_normalize_peptide_value(candidate) for candidate in re.split(r"[\n,;]+", raw_env_peptides))
            if token
        }
        if normalized:
            return normalized

    source_path = (
        Path(config_path)
        if config_path is not None
        else Path(env_map.get(KNOWN_PEPTIDES_FILE_ENV_VAR, DEFAULT_KNOWN_PEPTIDES_FILE))
    )
    loaded = _load_peptides_from_file(source_path)
    if loaded:
        return loaded

    return set(DEFAULT_KNOWN_PEPTIDES)


KNOWN_PEPTIDES = load_known_peptides()

# Minimum number of linked events required to keep peptide rows in CSV exports.
PEPTIDE_EVENT_THRESHOLD = 2

def is_valid_export_peptide(name: str) -> bool:
    """Filter obvious OCR/noise artifacts from peptide exports."""
    token = (name or "").strip()
    if not token:
        return False

    token_upper = token.upper()

    if re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]{8,100}", token_upper):
        return True

    return token_upper in KNOWN_PEPTIDES

def should_skip_entity(
    entity_type: str,
    canonical_name: str,
    role: str,
) -> bool:
    """Drop context-only entities and noisy peptides from ranking exports."""
    if role == "context":
        return True

    if entity_type == "peptide" and not is_valid_export_peptide(canonical_name):
        return True

    return False

def should_suppress_entity_for_csv(entity: dict, entity_events: Optional[dict] = None) -> bool:
    """Suppress very weak peptide rows in final CSV exports."""
    entity_type = entity.get("entity_type")
    entity_id = entity.get("entity_id")
    if entity_type != "peptide" or not entity_id:
        return False
    if entity_events is None:
        entity_events = {}
    return len(entity_events.get(entity_id, [])) < PEPTIDE_EVENT_THRESHOLD
