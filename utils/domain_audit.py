from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from typing import Iterable

from lenses import LENS_REGISTRY
from utils.axon_domains import load_domain_profile
from utils.domain_enforcement import ALLOWED_ENTITY_TYPES_BY_DOMAIN
from utils.seed_overlay_loader import OVERLAY_MAPPING

LOGGER = logging.getLogger(__name__)

CONSTRUCTION_BANNED_ENTITY_TYPES = {
    "peptide",
    "compound",
    "target",
    "stem_cell",
    "neural_cell",
    "assay",
    "pathway",
    "indication",
    "model",
}

BANNED_ENTITY_TYPES_BY_DOMAIN: dict[str, set[str]] = {
    "construction_science": CONSTRUCTION_BANNED_ENTITY_TYPES,
}

OVERLAY_MAPPING_REQUIRED_BY_DOMAIN: dict[str, bool] = {
    "construction_science": True,
}


@dataclass(frozen=True)
class DomainAuditEntry:
    domain_id: str
    config_path: str
    config_exists: bool
    profile_name: str
    overlays: list[str] = field(default_factory=list)
    overlay_files: list[str] = field(default_factory=list)
    overlay_files_missing: list[str] = field(default_factory=list)
    seed_files: list[str] = field(default_factory=list)
    seed_files_missing: list[str] = field(default_factory=list)
    preferred_entity_types: list[str] = field(default_factory=list)
    allowed_entity_types: list[str] = field(default_factory=list)
    preferred_types_not_allowed: list[str] = field(default_factory=list)
    allowed_types_not_preferred: list[str] = field(default_factory=list)
    construction_lenses: list[str] = field(default_factory=list)
    overlay_mapping_file: str | None = None
    overlay_mapping_exists: bool = False
    biomedical_leakage: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FeedAuditEntry:
    name: str
    url: str
    domain: str | None
    domain_config_exists: bool
    missing_reason: str | None = None


@dataclass(frozen=True)
class DomainAuditReport:
    domains: list[DomainAuditEntry]
    feeds: list[FeedAuditEntry]
    issues: list[str] = field(default_factory=list)

    def has_issues(self) -> bool:
        return bool(self.issues)


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _domain_config_path(domain_id: str, domains_dir: Path) -> Path:
    return domains_dir / f"{domain_id}.json"


def _overlay_file_path(overlay_id: str, overlays_dir: Path) -> Path:
    return overlays_dir / f"{overlay_id}.json"


def _find_missing(values: Iterable[str], base_dir: Path) -> list[str]:
    missing: list[str] = []
    for value in values:
        if not (base_dir / value).exists():
            missing.append(value)
    return missing


def _resolve_seed_file(seed_file: str, seeds_dir: Path, domain_id: str) -> Path | None:
    candidate = seeds_dir / seed_file
    if candidate.exists():
        return candidate

    seed_path = Path(seed_file)
    stem = seed_path.stem
    suffix = seed_path.suffix

    search_paths = []
    if "base/" not in seed_file and "base\\" not in seed_file:
        search_paths.extend([
            seeds_dir / "base" / domain_id / seed_file,
            seeds_dir / "base" / "life_sciences" / seed_file,
        ])

    if suffix:
        alternate_suffix = ".txt" if suffix.lower() != ".txt" else ".json"
        search_paths.extend([
            seeds_dir / "base" / domain_id / f"{stem}{alternate_suffix}",
            seeds_dir / "base" / "life_sciences" / f"{stem}{alternate_suffix}",
            seeds_dir / f"{stem}{alternate_suffix}",
        ])

    attempted_paths = [str(candidate), *(str(path) for path in search_paths)]
    for path in search_paths:
        if path.exists():
            return path

    LOGGER.warning(
        "Unable to resolve seed file %s for domain %s under %s; attempted candidates: %s",
        seed_file,
        domain_id,
        seeds_dir,
        attempted_paths,
    )
    return None


def audit_domain(
    domain_id: str,
    *,
    domains_dir: str | Path = "config/domains",
    overlays_dir: str | Path = "seeds/overlays",
    seeds_dir: str | Path = "seeds",
    domain_banned_entity_map: dict[str, Iterable[str]] | None = None,
    overlay_mapping_required_by_domain: dict[str, bool] | None = None,
) -> DomainAuditEntry:
    domains_dir = Path(domains_dir)
    overlays_dir = Path(overlays_dir)
    seeds_dir = Path(seeds_dir)
    config_path = _domain_config_path(domain_id, domains_dir)
    if not config_path.exists():
        raise FileNotFoundError(f"Missing domain config: {config_path}")

    profile = load_domain_profile(str(config_path))
    allowed_entity_types = sorted(ALLOWED_ENTITY_TYPES_BY_DOMAIN.get(domain_id, []))
    preferred_entity_types = sorted(profile.get_preferred_entity_types())
    preferred_not_allowed = sorted(set(preferred_entity_types) - set(allowed_entity_types))
    allowed_not_preferred = sorted(set(allowed_entity_types) - set(preferred_entity_types))
    overlay_files = [f"{overlay_id}.json" for overlay_id in profile.overlays]
    overlay_files_missing = _find_missing(overlay_files, overlays_dir)
    overlay_mapping_file = OVERLAY_MAPPING.get(domain_id)
    overlay_mapping_exists = bool(overlay_mapping_file and (overlays_dir / overlay_mapping_file).exists())
    construction_lenses = list(LENS_REGISTRY.keys()) if domain_id == "construction_science" else []
    active_banned_entity_map = domain_banned_entity_map or BANNED_ENTITY_TYPES_BY_DOMAIN
    banned_entity_types = set(active_banned_entity_map.get(domain_id, []))
    biomedical_leakage = sorted(set(preferred_entity_types).intersection(banned_entity_types))
    seed_files_missing: list[str] = []
    for seed_file in profile.get_seed_files():
        resolved_seed = _resolve_seed_file(seed_file, seeds_dir, domain_id)
        if resolved_seed is None:
            raise FileNotFoundError(
                f"Unable to resolve seed file {seed_file!r} for domain {domain_id!r} under {seeds_dir}. "
                "See the audit log for attempted candidate paths."
            )
        seed_files_missing.append(seed_file)

    return DomainAuditEntry(
        domain_id=domain_id,
        config_path=str(config_path),
        config_exists=True,
        profile_name=profile.name,
        overlays=list(profile.overlays),
        overlay_files=overlay_files,
        overlay_files_missing=overlay_files_missing,
        seed_files=list(profile.get_seed_files()),
        seed_files_missing=seed_files_missing,
        preferred_entity_types=preferred_entity_types,
        allowed_entity_types=allowed_entity_types,
        preferred_types_not_allowed=preferred_not_allowed,
        allowed_types_not_preferred=allowed_not_preferred,
        construction_lenses=construction_lenses,
        overlay_mapping_file=overlay_mapping_file,
        overlay_mapping_exists=overlay_mapping_exists,
        biomedical_leakage=biomedical_leakage,
    )


def audit_feeds(
    *,
    feeds_path: str | Path = "config/feeds.json",
    domains_dir: str | Path = "config/domains",
) -> list[FeedAuditEntry]:
    feeds_path = Path(feeds_path)
    domains_dir = Path(domains_dir)
    if not feeds_path.exists():
        raise FileNotFoundError(f"Missing feeds config: {feeds_path}")

    data = _read_json(feeds_path)
    feeds = data.get("feeds", [])
    entries: list[FeedAuditEntry] = []
    for feed in feeds:
        domain = feed.get("domain")
        domain_exists = bool(domain) and _domain_config_path(str(domain), domains_dir).exists()
        missing_reason = None
        if not domain:
            missing_reason = "missing domain"
        elif not domain_exists:
            missing_reason = f"missing config/domains/{domain}.json"
        entries.append(
            FeedAuditEntry(
                name=feed.get("name", "<unnamed>"),
                url=feed.get("url", ""),
                domain=domain,
                domain_config_exists=domain_exists,
                missing_reason=missing_reason,
            )
        )
    return entries


def audit_domains(
    *,
    domains_dir: str | Path = "config/domains",
    feeds_path: str | Path = "config/feeds.json",
    overlays_dir: str | Path = "seeds/overlays",
    seeds_dir: str | Path = "seeds",
    domain_banned_entity_map: dict[str, Iterable[str]] | None = None,
    overlay_mapping_required_by_domain: dict[str, bool] | None = None,
) -> DomainAuditReport:
    domains_dir = Path(domains_dir)
    overlays_dir = Path(overlays_dir)
    seeds_dir = Path(seeds_dir)
    active_overlay_mapping_required_by_domain = overlay_mapping_required_by_domain or OVERLAY_MAPPING_REQUIRED_BY_DOMAIN
    config_files = sorted(domains_dir.glob("*.json"))
    if not config_files:
        raise FileNotFoundError(f"No domain configs found in {domains_dir}")

    domain_entries: list[DomainAuditEntry] = []
    issues: list[str] = []
    for config_path in config_files:
        domain_id = config_path.stem
        entry = audit_domain(
            domain_id,
            domains_dir=domains_dir,
            overlays_dir=overlays_dir,
            seeds_dir=seeds_dir,
            domain_banned_entity_map=domain_banned_entity_map,
            overlay_mapping_required_by_domain=active_overlay_mapping_required_by_domain,
        )
        domain_entries.append(entry)
        if entry.overlay_files_missing:
            issues.append(f"{domain_id}: missing overlay files {entry.overlay_files_missing}")
        if entry.preferred_types_not_allowed:
            issues.append(f"{domain_id}: preferred entity types not allowed {entry.preferred_types_not_allowed}")
        if entry.biomedical_leakage:
            issues.append(f"{domain_id}: biomedical leakage {entry.biomedical_leakage}")
        if active_overlay_mapping_required_by_domain.get(domain_id, False) and not entry.overlay_mapping_exists:
            issues.append(f"{domain_id}: missing overlay mapping file")

    feed_entries = audit_feeds(feeds_path=feeds_path, domains_dir=domains_dir)
    for feed in feed_entries:
        if feed.missing_reason:
            issues.append(f"feed '{feed.name}': {feed.missing_reason}")

    return DomainAuditReport(domains=domain_entries, feeds=feed_entries, issues=issues)


def format_audit_report(report: DomainAuditReport) -> str:
    lines: list[str] = []
    lines.append("DOMAINS")
    for entry in report.domains:
        lines.append(f"- {entry.domain_id}: {entry.profile_name}")
        lines.append(f"  config: {entry.config_path} ({'ok' if entry.config_exists else 'missing'})")
        lines.append(f"  seed files: {', '.join(entry.seed_files) if entry.seed_files else 'none'}")
        if entry.seed_files_missing:
            lines.append(f"  missing seed files: {', '.join(entry.seed_files_missing)}")
        lines.append(f"  preferred entity types: {', '.join(entry.preferred_entity_types) if entry.preferred_entity_types else 'none'}")
        lines.append(f"  allowed entity types: {', '.join(entry.allowed_entity_types) if entry.allowed_entity_types else 'none'}")
        if entry.preferred_types_not_allowed:
            lines.append(f"  preferred not allowed: {', '.join(entry.preferred_types_not_allowed)}")
        lines.append(f"  overlays: {', '.join(entry.overlays) if entry.overlays else 'none'}")
        if entry.overlay_files:
            lines.append(f"  overlay files: {', '.join(entry.overlay_files)}")
        if entry.overlay_files_missing:
            lines.append(f"  missing overlay files: {', '.join(entry.overlay_files_missing)}")
        if entry.overlay_mapping_file:
            lines.append(f"  seed overlay mapping: {entry.overlay_mapping_file} ({'ok' if entry.overlay_mapping_exists else 'missing'})")
        if entry.construction_lenses:
            lines.append(f"  construction lenses: {', '.join(entry.construction_lenses)}")
        if entry.biomedical_leakage:
            lines.append(f"  biomedical leakage: {', '.join(entry.biomedical_leakage)}")
    lines.append("FEEDS")
    for feed in report.feeds:
        domain = feed.domain or "<missing>"
        status = "ok" if feed.domain_config_exists else f"ERROR: {feed.missing_reason}"
        lines.append(f"- {feed.name}: {domain} [{status}]")
    if report.issues:
        lines.append("ISSUES")
        for issue in report.issues:
            lines.append(f"- {issue}")
    else:
        lines.append("ISSUES: none")
    return "\n".join(lines)


def main() -> int:
    report = audit_domains()
    print(format_audit_report(report))
    return 0 if not report.issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
