from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pdfplumber

from lenses import detect_building_physics, detect_climate, detect_failure, detect_materials
from utils.metadata_utils import extract_metadata
from utils.path_validation import validate_domain_id
from utils.text_utils import chunk_sentences


logger = logging.getLogger(__name__)


CONSTRUCTION_PATTERNS = [
    ("building envelope", ["building envelope", "air barrier", "thermal bridge"], 5),
    ("moisture", ["moisture", "water intrusion", "water leakage", "condensation", "wetting", "moisture risk"], 5),
    ("vapor control", ["vapor barrier", "vapor control", "vapor diffusion", "air sealing"], 5),
    ("insulation", ["insulation", "spray foam", "rigid foam", "batt insulation", "continuous insulation"], 5),
    ("roof assembly", ["roof assembly", "roofing assembly"], 5),
    ("wall assembly", ["wall assembly", "wall system", "building assembly", "enclosure assembly"], 5),
    ("crawlspace", ["crawlspace", "crawl space"], 5),
    ("foundation settlement", ["foundation settlement"], 5),
    ("construction codes", ["ashrae", "astm", "fema", "doe building technologies", "building science corporation", "ibc", "irc"], 5),
    ("roof", ["roof", "roofing"], 1),
    ("attic", ["attic", "vented attic", "unvented attic"], 1),
    ("foundation", ["foundation", "slab", "basement", "footing"], 1),
    ("materials", ["materials", "material", "building materials", "construction materials"], 1),
    ("structural", ["structural", "structure", "structural failure", "load bearing"], 1),
    ("thermal performance", ["thermal performance", "r-value", "u-value", "heat loss", "heat transfer"], 1),
    ("code", ["code", "standard"], 1),
]

BUILDING_CONTEXT_PATTERNS = [
    ("building envelope", ["building envelope", "air barrier", "thermal bridge"], 3),
    ("building science corporation", ["building science corporation"], 2),
    ("roof", ["roof", "roof assembly", "roofing"], 2),
    ("wall", ["wall", "wall assembly", "wall system", "enclosure assembly"], 2),
    ("attic", ["attic", "vented attic", "unvented attic"], 2),
    ("crawlspace", ["crawlspace", "crawl space"], 3),
    ("foundation", ["foundation", "foundation settlement", "slab", "basement", "footing"], 2),
    ("moisture", ["moisture", "water intrusion", "water leakage", "condensation", "wetting", "moisture risk"], 2),
    ("vapor control", ["vapor barrier", "vapor control", "vapor diffusion", "air sealing"], 3),
    ("insulation", ["insulation", "spray foam", "rigid foam", "batt insulation", "continuous insulation"], 3),
    ("construction codes", ["ashrae", "astm", "fema", "doe building technologies", "ibc", "irc"], 3),
]

CONTAMINATION_PATTERNS = [
    ("stem cell", ["stem cell", "stem cells", "stem-cell", "induced pluripotent", "organoid"], 2),
    ("assay", ["assay", "bioassay", "screening assay"], 1),
    ("protein", ["protein", "proteins", "peptide", "peptides", "receptor", "kinase"], 1),
    ("biological sample", ["mouse model", "mouse", "serum", "plasma", "clinical trial", "drug discovery"], 2),
]

CLIMATE_BOILERPLATE_PATTERNS = [
    ("climate normals", ["canadian climate normals", "climate normals", "normales climatiques", "climate publication"], 2),
    ("climate catalog", ["volume 8", "pressure temperature humidity", "environment canada", "atmospheric service"], 1),
]

STRONG_CONSTRUCTION_SIGNALS = {
    "building envelope",
    "moisture",
    "vapor control",
    "insulation",
    "roof assembly",
    "wall assembly",
    "crawlspace",
    "foundation settlement",
    "construction codes",
}

STRONG_BUILDING_CONTEXT_SIGNALS = {
    "building envelope",
    "building science corporation",
    "roof",
    "wall",
    "attic",
    "crawlspace",
    "foundation",
    "moisture",
    "vapor control",
    "insulation",
    "construction codes",
}

PHYSICS_RESEARCH_KEYWORDS = (
    "quantum",
    "photonic",
    "photonics",
    "superconduct",
    "topological",
    "plasmon",
    "spin",
    "magnet",
    "ferroelectric",
    "semiconductor",
    "optical",
    "electronic",
    "transport",
    "band gap",
    "terahertz",
)

MATERIALS_RESEARCH_KEYWORDS = (
    "alloy",
    "composite",
    "ceramic",
    "polymer",
    "membrane",
    "hafnia",
    "tio2",
    "battery",
    "batteries",
    "memristor",
    "nanopattern",
    "thin film",
    "crystal",
    "silicon",
)


@dataclass(frozen=True)
class TriagedSource:
    file_path: str
    title: str
    detected_domain: str
    keep_skip_review: str
    confidence: str
    construction_signals: str
    contamination_signals: str
    reason: str
    building_physics_score: int = 0
    materials_score: int = 0
    failure_score: int = 0
    climate_score: int = 0
    triage_decision: str = ""
    lens_promoted: bool = False
    promotion_reason: str = ""
    lens_hit_counts: str = ""
    final_decision: str = ""


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _collect_matches(text: str, patterns: list[tuple[str, list[str], int]]) -> tuple[list[str], int]:
    normalized = _normalize_text(text)
    matches: list[str] = []
    score = 0
    for label, phrases, weight in patterns:
        for phrase in phrases:
            normalized_phrase = _normalize_text(phrase)
            if normalized_phrase and re.search(rf"\b{re.escape(normalized_phrase)}\b", normalized):
                matches.append(label)
                score += weight
                break
    return sorted(set(matches)), score


LENS_CONFIDENCE_SCORES = {"low": 1, "med": 3, "medium": 3, "high": 5}
LENS_CONTEXT_BONUS = {"weak": 0, "moderate": 1, "strong": 2}
FAILURE_KEYWORDS = [
    "failure",
    "failed",
    "collapse",
    "fracture",
    "cracking",
    "crack",
    "spalling",
    "buckling",
    "leakage",
    "water intrusion",
    "mold",
    "corrosion",
    "settlement",
]


def _score_lens_event(event: object, entities: list[dict]) -> int:
    if event is None:
        return 0

    confidence = getattr(event, "confidence", "")
    context_strength = getattr(event, "context_strength", "weak")
    outcome = getattr(event, "outcome", "")
    tags = getattr(event, "tags", [])

    score = LENS_CONFIDENCE_SCORES.get(str(confidence).lower(), 1)
    score += LENS_CONTEXT_BONUS.get(str(context_strength).lower(), 0)
    if outcome in {"positive", "negative", "degraded"}:
        score += 1
    if tags:
        score += 1
    if entities:
        score += 1
    return min(score, 10)


def _score_lens_text(text: str, detector) -> int:
    score = 0
    for sentence in chunk_sentences(text):
        event, entities = detector(sentence)
        score += _score_lens_event(event, entities)
    return min(score, 10)


def _keyword_support_score(text: str, keywords: list[str], per_hit: int = 2) -> int:
    normalized = _normalize_text(text)
    hits = 0
    for keyword in keywords:
        normalized_keyword = _normalize_text(keyword)
        if normalized_keyword and re.search(rf"\b{re.escape(normalized_keyword)}\b", normalized):
            hits += 1
    return min(hits * per_hit, 10)
def _classify_review_domain(
    *,
    combined_text: str,
    construction_signals: list[str],
    building_context_signals: list[str],
) -> str:
    if building_context_signals:
        return "construction_science"

    lowered_text = combined_text.lower()
    if any(keyword in lowered_text for keyword in PHYSICS_RESEARCH_KEYWORDS):
        return "physics"

    if any(keyword in lowered_text for keyword in MATERIALS_RESEARCH_KEYWORDS):
        return "materials_science"

    return "unknown"


def classify_triage(
    *,
    file_path: Path,
    title: str,
    metadata_text: str,
    sample_text: str,
) -> TriagedSource:
    combined_text = "\n".join([title, metadata_text, sample_text])
    construction_signals, construction_score = _collect_matches(combined_text, CONSTRUCTION_PATTERNS)
    building_context_signals, building_context_score = _collect_matches(combined_text, BUILDING_CONTEXT_PATTERNS)
    contamination_signals, contamination_score = _collect_matches(combined_text, CONTAMINATION_PATTERNS)
    climate_signals, climate_score = _collect_matches(combined_text, CLIMATE_BOILERPLATE_PATTERNS)
    score_text = "\n".join([text for text in (title, metadata_text, sample_text) if text])
    building_physics_score = max(
        _score_lens_text(score_text, detect_building_physics),
        construction_score,
    )
    materials_score = max(
        _score_lens_text(score_text, detect_materials),
        _keyword_support_score(combined_text, list(MATERIALS_RESEARCH_KEYWORDS)),
    )
    failure_score = max(
        _score_lens_text(score_text, detect_failure),
        _keyword_support_score(combined_text, FAILURE_KEYWORDS),
    )
    climate_score_lens = max(
        _score_lens_text(score_text, detect_climate),
        climate_score,
    )
    total_score = building_physics_score + materials_score + failure_score + climate_score_lens
    biomedical_score = contamination_score

    biomedical_dominates = biomedical_score >= 3 and biomedical_score >= total_score
    if biomedical_dominates:
        keep_skip_review = "skip"
    elif building_physics_score >= 8 or materials_score >= 8 or failure_score >= 8:
        keep_skip_review = "keep"
    elif total_score >= 4:
        keep_skip_review = "review"
    else:
        keep_skip_review = "skip"

    if biomedical_dominates:
        detected_domain = "biomedical"
    elif keep_skip_review == "keep":
        detected_domain = "construction_science"
    elif climate_score_lens > 0 and construction_score > contamination_score:
        detected_domain = "construction_science"
    else:
        detected_domain = _classify_review_domain(
            combined_text=combined_text,
            construction_signals=construction_signals,
            building_context_signals=building_context_signals,
        )

    if (
        keep_skip_review == "skip"
        and not biomedical_dominates
        and detected_domain in {"physics", "materials_science"}
        and construction_signals
        and not building_context_signals
    ):
        keep_skip_review = "review"

    if total_score >= 8:
        confidence = "high"
    elif total_score >= 4:
        confidence = "med"
    else:
        confidence = "low"

    if keep_skip_review == "keep":
        reason = (
            f"lens scores strong enough for keep; building_physics={building_physics_score}, "
            f"materials={materials_score}, failure={failure_score}, climate={climate_score_lens}"
        )
    elif keep_skip_review == "review":
        reason = (
            f"lens scores warrant review; building_physics={building_physics_score}, materials={materials_score}, "
            f"failure={failure_score}, climate={climate_score_lens}, total={total_score}"
        )
    else:
        reason = (
            f"skip; building_physics={building_physics_score}, materials={materials_score}, "
            f"failure={failure_score}, climate={climate_score_lens}, total={total_score}, "
            f"biomedical={biomedical_score}"
        )

    return TriagedSource(
        file_path=str(file_path),
        title=title,
        detected_domain=detected_domain,
        keep_skip_review=keep_skip_review,
        confidence=confidence,
        construction_signals="; ".join(construction_signals),
        contamination_signals="; ".join(contamination_signals),
        reason=reason,
        building_physics_score=building_physics_score,
        materials_score=materials_score,
        failure_score=failure_score,
        climate_score=climate_score_lens,
    )


def _read_sample_text(pdf_path: Path, first_pages: int, max_chars: int) -> tuple[str, str, str]:
    with pdfplumber.open(str(pdf_path)) as pdf:
        metadata = extract_metadata(pdf_path, pdf)
        title = metadata.get("title") or pdf_path.stem
        metadata_bits = [
            metadata.get("title") or "",
            metadata.get("authors") or "",
            str(metadata.get("year") or ""),
            metadata.get("doi") or "",
        ]
        sample_parts: list[str] = []
        for page in pdf.pages[:first_pages]:
            text = page.extract_text() or ""
            if text.strip():
                sample_parts.append(text)
        sample_text = "\n".join(sample_parts)[:max_chars]
    return title, " | ".join(bit for bit in metadata_bits if bit), sample_text


def scan_pdf(pdf_path: Path, first_pages: int = 3, max_chars: int = 1600) -> TriagedSource:
    title, metadata_text, sample_text = _read_sample_text(pdf_path, first_pages, max_chars)
    return classify_triage(
        file_path=pdf_path,
        title=title,
        metadata_text=metadata_text,
        sample_text=sample_text,
    )


def scan_pdfs(input_dir: Path, first_pages: int = 3, max_chars: int = 1600, limit: int | None = None) -> list[TriagedSource]:
    pdf_paths = sorted(input_dir.rglob("*.pdf"))
    if limit is not None:
        pdf_paths = pdf_paths[:limit]

    results: list[TriagedSource] = []
    for pdf_path in pdf_paths:
        try:
            results.append(scan_pdf(pdf_path, first_pages=first_pages, max_chars=max_chars))
        except Exception as exc:
            logger.exception("Failed to scan PDF %s", pdf_path)
            results.append(
                TriagedSource(
                    file_path=str(pdf_path),
                    title=pdf_path.stem,
                    detected_domain="unknown",
                    keep_skip_review="review",
                    confidence="low",
                    construction_signals="",
                    contamination_signals="",
                    reason=f"failed to scan PDF ({exc.__class__.__name__}) — see logs",
                )
            )
    return results


def write_triage_csv(rows: Iterable[TriagedSource], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "title",
        "building_physics_score",
        "materials_score",
        "failure_score",
        "climate_score",
        "triage_decision",
        "lens_promoted",
        "promotion_reason",
        "lens_hit_counts",
        "final_decision",
        "decision",
        "reason",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "title": row.title,
                    "building_physics_score": row.building_physics_score,
                    "materials_score": row.materials_score,
                    "failure_score": row.failure_score,
                    "climate_score": row.climate_score,
                    "triage_decision": row.triage_decision or row.keep_skip_review,
                    "lens_promoted": row.lens_promoted,
                    "promotion_reason": row.promotion_reason,
                    "lens_hit_counts": row.lens_hit_counts,
                    "final_decision": row.final_decision or row.keep_skip_review,
                    "decision": row.keep_skip_review,
                    "reason": row.reason,
                }
            )
    return output_path


def load_keep_manifest(manifest_path: Path) -> set[str]:
    if not manifest_path.exists():
        return set()

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()

    if isinstance(payload, dict):
        keep_files = payload.get("keep_files", [])
    elif isinstance(payload, list):
        keep_files = payload
    else:
        keep_files = []

    return {str(item) for item in keep_files if str(item).strip()}


def write_keep_manifest(rows: Iterable[TriagedSource] | Iterable[str], output_path: Path, domain: str = "construction_science") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    keep_files: set[str] = set()
    for row in rows:
        if isinstance(row, TriagedSource):
            final_decision = row.final_decision or row.keep_skip_review
            if final_decision == "keep":
                keep_files.add(row.file_path)
        else:
            value = str(row).strip()
            if value:
                keep_files.add(value)

    payload = {
        "domain": domain,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "keep_files": sorted(keep_files),
    }

    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan PDFs and triage construction-science sources before extraction")
    parser.add_argument("--input-dir", type=Path, default=Path("input/pdfs"), help="Folder containing PDFs to scan")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("exports/source_triage/construction_science_triage.csv"),
        help="Path to the triage CSV report",
    )
    parser.add_argument("--domain", type=str, default="construction_science", help="Target domain label")
    parser.add_argument("--first-pages", type=int, default=3, help="Number of first pages to sample")
    parser.add_argument("--max-chars", type=int, default=1600, help="Maximum sampled text characters per PDF")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for quick smoke tests")
    args = parser.parse_args()

    try:
        domain_id = validate_domain_id(args.domain)
    except (TypeError, ValueError) as exc:
        print(f"Invalid domain value: {exc}")
        return 1

    rows = scan_pdfs(args.input_dir, first_pages=args.first_pages, max_chars=args.max_chars, limit=args.limit)
    output_path = args.output
    if output_path.is_dir():
        output_path = output_path / f"{domain_id}_triage.csv"
    write_triage_csv(rows, output_path)
    write_keep_manifest(rows, output_path.with_name(f"{domain_id}_keep.json"), domain=domain_id)

    keep_count = sum(1 for row in rows if row.keep_skip_review == "keep")
    skip_count = sum(1 for row in rows if row.keep_skip_review == "skip")
    review_count = sum(1 for row in rows if row.keep_skip_review == "review")
    print(f"Wrote triage report: {output_path}")
    print(f"keep={keep_count} skip={skip_count} review={review_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
