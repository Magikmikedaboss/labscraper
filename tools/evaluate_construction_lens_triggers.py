#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lenses import LENS_REGISTRY, detect_multi_lens  # noqa: E402
from lenses.construction_building_physics_v1 import ASSEMBLIES, PHYSICS_TERMS  # noqa: E402
from lenses.construction_climate_v1 import HAZARDS, RESILIENCE_TERMS  # noqa: E402
from lenses.construction_common import list_hits  # noqa: E402
from lenses.construction_compliance_v1 import CODE_PHRASES, FAIL_PHRASES, PASS_PHRASES, STD_TOKENS  # noqa: E402
from lenses.construction_failure_v1 import CAUSAL_MARKERS, FAILURE_DRIVERS, FAILURE_MODES, HIGH_SIGNAL  # noqa: E402
from lenses.construction_failure_v1 import FIRE_FAILURE_MODES, MATERIAL_FAILURE_MODES, MOISTURE_FAILURE_MODES, STRUCTURAL_FAILURE_MODES  # noqa: E402
from lenses.construction_insurance_risk_v1 import BUILDING_SYSTEMS, INSURANCE_TERMS, LOSS_CAUSES, MITIGATION_TERMS, PROPERTY_RISK_TERMS  # noqa: E402
from lenses.construction_materials_v1 import MATERIALS, PROPERTIES  # noqa: E402
from lenses.construction_methods_tooling_v1 import TEST_MARKERS as METHODS_TEST_MARKERS  # noqa: E402
from tools.evaluate_construction_lenses import (  # noqa: E402
    _collect_candidate_pdfs,
    _default_cache_dir,
    _default_gold_corpus_path,
    _default_manifest_path,
    _load_gold_corpus_paths,
    _normalize_manifest_entries,
    _unique_pdf_paths,
    gold_corpus_ids,
)
from utils.text_utils import chunk_sentences  # noqa: E402


DEFAULT_LENS_ORDER = ["building_physics", "materials", "methods_tooling", "failure", "climate", "compliance", "insurance_risk"]
FAILURE_BUCKET_ORDER = ["moisture", "structural", "material", "fire"]
logger = logging.getLogger(__name__)


def _preferred_failure_kind(kind: str) -> int:
    priority = {
        "failure_mode": 0,
        "failure_driver": 1,
        "causal_marker": 2,
        "high_signal": 3,
    }
    return priority.get(kind, 99)


def _dedupe_failure_terms(terms: list[tuple[str, int, str]]) -> list[tuple[str, int, str]]:
    best_by_term: dict[str, dict[str, object]] = {}
    for term, count, trigger_kind in terms:
        current = best_by_term.get(term)
        if current is None:
            best_by_term[term] = {
                "term": term,
                "count": count,
                "trigger_kind": trigger_kind,
            }
            continue
        current["count"] = int(current["count"]) + count
        if _preferred_failure_kind(trigger_kind) < _preferred_failure_kind(str(current["trigger_kind"])):
            current["trigger_kind"] = trigger_kind
    return sorted(
        [(item["term"], int(item["count"]), str(item["trigger_kind"])) for item in best_by_term.values()],
        key=lambda item: (-item[1], item[0], _preferred_failure_kind(item[2])),
    )


def _default_output_dir() -> Path:
    return ROOT / "exports" / "lens_evaluation"


def _select_lens_order() -> list[str]:
    return [lens_name for lens_name in DEFAULT_LENS_ORDER if lens_name in LENS_REGISTRY]


def _trigger_hits_for_lens(lens_name: str, sentence: str) -> list[tuple[str, str]]:
    s_l = sentence.lower()
    hits: list[tuple[str, str]] = []

    if lens_name == "building_physics":
        hits.extend((term, "assembly") for term in list_hits(s_l, ASSEMBLIES))
        hits.extend((term, "physics_term") for term in list_hits(s_l, PHYSICS_TERMS))
    elif lens_name == "materials":
        hits.extend((term, "material") for term in list_hits(s_l, MATERIALS))
        hits.extend((term, "property") for term in list_hits(s_l, PROPERTIES))
    elif lens_name == "methods_tooling":
        hits.extend((term, "test_marker") for term in list_hits(s_l, METHODS_TEST_MARKERS))
    elif lens_name == "failure":
        hits.extend((term, "failure_mode") for term in list_hits(s_l, FAILURE_MODES))
        hits.extend((term, "failure_driver") for term in list_hits(s_l, FAILURE_DRIVERS))
        hits.extend((term, "causal_marker") for term in list_hits(s_l, CAUSAL_MARKERS))
        hits.extend((term, "high_signal") for term in list_hits(s_l, HIGH_SIGNAL))
    elif lens_name == "climate":
        hits.extend((term, "hazard") for term in list_hits(s_l, HAZARDS))
        hits.extend((term, "resilience_term") for term in list_hits(s_l, RESILIENCE_TERMS))
    elif lens_name == "compliance":
        hits.extend((term, "std_token") for term in list_hits(s_l, STD_TOKENS))
        hits.extend((term, "code_phrase") for term in list_hits(s_l, CODE_PHRASES))
        hits.extend((term, "pass_phrase") for term in list_hits(s_l, PASS_PHRASES))
        hits.extend((term, "fail_phrase") for term in list_hits(s_l, FAIL_PHRASES))
    elif lens_name == "insurance_risk":
        hits.extend((term, "loss_cause") for term in list_hits(s_l, LOSS_CAUSES))
        hits.extend((term, "risk_term") for term in list_hits(s_l, PROPERTY_RISK_TERMS))
        hits.extend((term, "insurance_term") for term in list_hits(s_l, INSURANCE_TERMS))
        hits.extend((term, "mitigation_term") for term in list_hits(s_l, MITIGATION_TERMS))
        hits.extend((term, "system") for term in list_hits(s_l, BUILDING_SYSTEMS))

    return hits


def _failure_bucket_for_term(term: str) -> str:
    if term in MOISTURE_FAILURE_MODES:
        return "moisture"
    if term in STRUCTURAL_FAILURE_MODES:
        return "structural"
    if term in MATERIAL_FAILURE_MODES:
        return "material"
    if term in FIRE_FAILURE_MODES:
        return "fire"
    return ""


def _scan_pdf_for_trigger_terms(pdf_path: Path, lens_order: list[str]) -> dict[str, list[dict]]:
    rows_by_lens: dict[str, list[dict]] = {lens_name: [] for lens_name in lens_order}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                for sentence_num, sentence in enumerate(chunk_sentences(text), start=1):
                    lens_results = detect_multi_lens(sentence, enabled_lenses=lens_order)
                    if not lens_results:
                        continue
                    for result in lens_results:
                        lens_name = result.get("lens")
                        if lens_name not in rows_by_lens:
                            continue
                        trigger_hits = _trigger_hits_for_lens(lens_name, sentence)
                        if not trigger_hits:
                            continue
                        for trigger_term, trigger_kind in trigger_hits:
                            rows_by_lens[lens_name].append(
                                {
                                    "pdf_name": pdf_path.name,
                                    "page": page_num,
                                    "sentence_num": sentence_num,
                                    "trigger_term": trigger_term,
                                    "trigger_kind": trigger_kind,
                                    "event_type": result.get("event_type", ""),
                                    "outcome": result.get("outcome", ""),
                                    "confidence": result.get("confidence", ""),
                                    "context_strength": result.get("context_strength", ""),
                                    "sentence": sentence,
                                }
                            )
    except (OSError, IOError, PDFSyntaxError):
        logger.exception("Handled PDF scan error for %s", pdf_path)
    except Exception:
        logger.exception("Failed to scan PDF %s", pdf_path)

    return rows_by_lens


def _write_csv(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "lens",
        "failure_bucket",
        "trigger_term",
        "trigger_kind",
        "count",
        "pdf_count",
        "top_pdf",
        "top_pdf_count",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def _write_markdown(summary: dict[str, object], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Construction Lens Trigger Vocabulary", ""]
    lines.append(f"- PDFs evaluated: {summary['pdfs_evaluated']}")
    lines.append(f"- Lens order: {', '.join(summary['lens_order'])}")
    lines.append("")

    for lens_name in summary["lens_order"]:
        lines.append(f"## {lens_name}")
        top_terms = summary["top_terms"].get(lens_name, [])
        if not top_terms:
            lines.append("- No trigger terms found")
            lines.append("")
            continue
        for term, count, trigger_kind in top_terms[:20]:
            lines.append(f"- {term} ({trigger_kind}): {count}")
        lines.append("")

    failure_buckets = summary.get("failure_buckets", {})
    if failure_buckets:
        lines.append("## failure buckets")
        for bucket in FAILURE_BUCKET_ORDER:
            bucket_rows = failure_buckets.get(bucket, [])
            if not bucket_rows:
                continue
            lines.append(f"### {bucket}")
            for term, count in bucket_rows[:10]:
                lines.append(f"- {term}: {count}")
            lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _write_failure_bucket_csv(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["failure_bucket", "trigger_term", "trigger_kind", "count", "pdf_count", "top_pdf", "top_pdf_count"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def _write_risk_summary_csv(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "lens",
        "top_issue",
        "top_term",
        "trigger_kind",
        "count",
        "pdf_count",
        "top_pdf",
        "top_pdf_count",
        "notes",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def _write_risk_summary_markdown(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Construction Risk Summary", ""]
    for row in rows:
        lines.append(f"## {row['lens']}")
        lines.append(f"- Top issue: {row['top_issue']}")
        lines.append(f"- Top term: {row['top_term']} ({row['count']} hits across {row['pdf_count']} PDFs)")
        lines.append(f"- Top PDF: {row['top_pdf']} ({row['top_pdf_count']} hits)")
        if row.get("notes"):
            lines.append(f"- Notes: {row['notes']}")
        lines.append("")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _term_pdf_stats(rows: list[dict], term: str) -> tuple[str, int, int]:
    pdf_counts: Counter[str] = Counter()
    for row in rows:
        if row["trigger_term"] == term:
            pdf_counts[row["pdf_name"]] += 1
    if not pdf_counts:
        return "", 0, 0
    top_pdf_name, top_pdf_count = pdf_counts.most_common(1)[0]
    return top_pdf_name, top_pdf_count, len(pdf_counts)


def _best_term(terms: list[tuple[str, int, str]], preferred_terms: list[str]) -> str:
    term_map = {term: term for term, _, _ in terms}
    for preferred_term in preferred_terms:
        if preferred_term in term_map:
            return preferred_term
    return terms[0][0] if terms else ""


def _best_term_from_rows(rows: list[dict], preferred_terms: list[str]) -> str:
    term_counts: Counter[str] = Counter(row["trigger_term"] for row in rows)
    for preferred_term in preferred_terms:
        if preferred_term in term_counts:
            return preferred_term
    return term_counts.most_common(1)[0][0] if term_counts else ""


def _build_causal_chain_rows(summary_top_terms: dict[str, list[tuple[str, int, str]]], failure_rows: list[dict]) -> list[dict]:
    building_terms = summary_top_terms.get("building_physics", [])
    climate_terms = summary_top_terms.get("climate", [])
    failure_terms = summary_top_terms.get("failure", [])

    def _has_preferred_term(terms: list[tuple[str, int, str]], preferred_terms: list[str]) -> bool:
        return any(term in preferred_terms for term, _, _ in terms)

    def _has_preferred_row_term(rows: list[dict], preferred_terms: list[str]) -> bool:
        return any(str(row.get("trigger_term", "")) in preferred_terms for row in rows)

    def _chain_status(
        *,
        hazard_terms: list[tuple[str, int, str]],
        hazard_preferred: list[str],
        physics_terms: list[tuple[str, int, str]] | None,
        physics_preferred: list[str] | None,
        failure_terms_source: list[tuple[str, int, str]] | None = None,
        failure_rows_source: list[dict] | None = None,
        failure_preferred: list[str] | None = None,
    ) -> bool:
        if not hazard_terms or not _has_preferred_term(hazard_terms, hazard_preferred):
            return False
        if physics_terms is not None and physics_preferred is not None and (
            not physics_terms or not _has_preferred_term(physics_terms, physics_preferred)
        ):
            return False
        if failure_terms_source is not None and failure_preferred is not None and (
            not failure_terms_source or not _has_preferred_term(failure_terms_source, failure_preferred)
        ):
            return False
        if failure_rows_source is not None and failure_preferred is not None and (
            not failure_rows_source or not _has_preferred_row_term(failure_rows_source, failure_preferred)
        ):
            return False
        return True

    chains = [
        {
            "chain_name": "moisture_chain",
            "hazard": _best_term(climate_terms, ["humidity", "moisture", "flood"]),
            "physics_mechanism": _best_term(
                building_terms,
                ["condensation", "moisture", "air leakage", "dew point", "relative humidity"],
            ),
            "failure": _best_term_from_rows(
                failure_rows,
                ["mold", "leakage", "moisture damage", "water damage", "condensation"],
            ),
            "material_effect": "water damage",
            "evidence_terms": "humidity; condensation; mold; water damage",
            "status": "high confidence",
        },
        {
            "chain_name": "fire_chain",
            "hazard": _best_term(climate_terms, ["wildfire", "wind", "high temperature"]),
            "physics_mechanism": _best_term(building_terms, ["heat flux", "thermal conductivity", "ventilation rate"]),
            "failure": _best_term(failure_terms, ["ignition", "fire spread", "collapse"]),
            "material_effect": "material degradation",
            "evidence_terms": "wildfire; heat flux; ignition; material degradation",
            "status": "high confidence",
        },
        {
            "chain_name": "structural_chain",
            "hazard": _best_term(climate_terms, ["wind", "freeze-thaw", "seismic"]),
            "physics_mechanism": "structural loading",
            "failure": _best_term(failure_terms, ["collapse", "spalling", "buckling"]),
            "material_effect": "structural distress",
            "evidence_terms": "wind; structural loading; collapse; structural distress",
            "status": "thin coverage",
        },
    ]

    validated_chains: list[dict] = []
    for chain in chains:
        if chain["chain_name"] == "moisture_chain":
            evidence_ok = _chain_status(
                hazard_terms=climate_terms,
                hazard_preferred=["humidity", "moisture", "flood"],
                physics_terms=building_terms,
                physics_preferred=["condensation", "moisture", "air leakage", "dew point", "relative humidity"],
                failure_rows_source=failure_rows,
                failure_preferred=["mold", "leakage", "moisture damage", "water damage", "condensation"],
            )
        elif chain["chain_name"] == "fire_chain":
            evidence_ok = _chain_status(
                hazard_terms=climate_terms,
                hazard_preferred=["wildfire", "wind", "high temperature"],
                physics_terms=building_terms,
                physics_preferred=["heat flux", "thermal conductivity", "ventilation rate"],
                failure_terms_source=failure_terms,
                failure_preferred=["ignition", "fire spread", "collapse"],
            )
        else:
            evidence_ok = _chain_status(
                hazard_terms=climate_terms,
                hazard_preferred=["wind", "freeze-thaw", "seismic"],
                physics_terms=None,
                physics_preferred=None,
                failure_terms_source=failure_terms,
                failure_preferred=["collapse", "spalling", "buckling"],
            )

        if not evidence_ok:
            chain = {
                **chain,
                "hazard": "missing_evidence",
                "physics_mechanism": "missing_evidence",
                "failure": "missing_evidence",
                "material_effect": "missing_evidence",
                "status": "insufficient_data",
            }
        validated_chains.append(chain)

    return validated_chains


def _write_causal_chain_csv(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "chain_name",
        "hazard",
        "physics_mechanism",
        "failure",
        "material_effect",
        "evidence_terms",
        "status",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def _write_causal_chain_markdown(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Construction Causal Chain Summary", ""]
    for row in rows:
        lines.append(f"## {row['chain_name']}")
        lines.append(f"- Hazard: {row['hazard']}")
        lines.append(f"- Physics mechanism: {row['physics_mechanism']}")
        lines.append(f"- Failure: {row['failure']}")
        lines.append(f"- Material effect: {row['material_effect']}")
        lines.append(f"- Evidence: {row['evidence_terms']}")
        lines.append(f"- Status: {row['status']}")
        lines.append("")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _write_top_failure_pathways_markdown(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Top Failure Pathways", ""]
    for row in rows:
        lines.append(f"## {row['chain_name']}")
        lines.append(
            f"- Pathway: {row['hazard']} -> {row['physics_mechanism']} -> {row['failure']} -> {row['material_effect']}"
        )
        lines.append(f"- Evidence: {row['evidence_terms']}")
        lines.append(f"- Status: {row['status']}")
        lines.append("")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _write_top_failure_pathways_csv(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["chain_name", "pathway", "evidence_terms", "status"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "chain_name": row["chain_name"],
                    "pathway": f"{row['hazard']} -> {row['physics_mechanism']} -> {row['failure']} -> {row['material_effect']}",
                    "evidence_terms": row["evidence_terms"],
                    "status": row["status"],
                }
            )
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit trigger vocabulary for the construction lens suite")
    parser.add_argument("--cache-dir", type=Path, default=_default_cache_dir(), help="RSS cache directory")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_default_manifest_path(),
        help="Construction keep manifest used to seed the evaluation set",
    )
    parser.add_argument(
        "--gold-corpus",
        type=Path,
        default=_default_gold_corpus_path(),
        help="Construction gold corpus used to seed the evaluation set",
    )
    parser.add_argument("--output-dir", type=Path, default=_default_output_dir(), help="Folder for evaluation outputs")
    parser.add_argument("--limit", type=int, default=25, help="Number of PDFs to evaluate")
    parser.add_argument(
        "--triage-limit",
        type=int,
        default=None,
        help="Optional maximum cache PDFs to triage when expanding beyond the keep manifest",
    )
    args = parser.parse_args(argv)

    lens_order = _select_lens_order()
    if not lens_order:
        print("ERROR: No construction lenses are available")
        return 1

    if not args.cache_dir.exists():
        print(f"ERROR: cache directory not found: {args.cache_dir}")
        return 1

    if not args.manifest.exists():
        print(f"ERROR: manifest file not found: {args.manifest}")
        return 1

    manifest_entries = _normalize_manifest_entries(args.manifest)
    gold_corpus_paths = _load_gold_corpus_paths(args.gold_corpus)
    gold_corpus_id_set = gold_corpus_ids(args.gold_corpus)
    pdf_paths = _collect_candidate_pdfs(
        args.cache_dir,
        manifest_entries,
        gold_corpus_paths,
        args.limit,
        args.triage_limit,
    )
    if not pdf_paths:
        print("ERROR: No construction PDFs were selected for evaluation")
        return 1

    pdf_paths, _, _, _skipped_pdfs = _unique_pdf_paths(pdf_paths, manifest_entries, gold_corpus_id_set)

    rows_by_lens: dict[str, list[dict]] = {lens_name: [] for lens_name in lens_order}
    for index, pdf_path in enumerate(pdf_paths, start=1):
        print(f"[{index}/{len(pdf_paths)}] {pdf_path.name}", flush=True)
        per_pdf_rows = _scan_pdf_for_trigger_terms(pdf_path, lens_order)
        for lens_name in lens_order:
            rows_by_lens[lens_name].extend(per_pdf_rows[lens_name])

    output_rows: list[dict] = []
    summary_top_terms: dict[str, list[tuple[str, int, str]]] = {}
    summary_top_pdfs: dict[str, list[tuple[str, int]]] = {}
    failure_bucket_summary: dict[str, list[tuple[str, int]]] = {bucket: [] for bucket in FAILURE_BUCKET_ORDER}

    for lens_name in lens_order:
        term_counts: Counter[tuple[str, str]] = Counter()
        pdf_term_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

        for row in rows_by_lens[lens_name]:
            term_key = (row["trigger_term"], row["trigger_kind"])
            term_counts[term_key] += 1
            pdf_term_counts[term_key][row["pdf_name"]] += 1

        ordered_terms = sorted(term_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
        if lens_name == "failure":
            summary_top_terms[lens_name] = _dedupe_failure_terms(
                [(term, count, trigger_kind) for (term, trigger_kind), count in ordered_terms]
            )[:20]
        else:
            summary_top_terms[lens_name] = [
                (term, count, trigger_kind)
                for (term, trigger_kind), count in ordered_terms[:20]
            ]

        top_pdf_counter: Counter[str] = Counter()
        for counts in pdf_term_counts.values():
            top_pdf_counter.update(counts)
        summary_top_pdfs[lens_name] = top_pdf_counter.most_common(10)

        for term, count, trigger_kind in summary_top_terms[lens_name]:
            top_pdf_name, top_pdf_count = pdf_term_counts[(term, trigger_kind)].most_common(1)[0]
            failure_bucket = _failure_bucket_for_term(term) if lens_name == "failure" else ""
            if lens_name == "failure" and not failure_bucket:
                continue
            output_rows.append(
                {
                    "lens": lens_name,
                    "failure_bucket": failure_bucket,
                    "trigger_term": term,
                    "trigger_kind": trigger_kind,
                    "count": count,
                    "pdf_count": len(pdf_term_counts[(term, trigger_kind)]),
                    "top_pdf": top_pdf_name,
                    "top_pdf_count": top_pdf_count,
                }
            )
            if lens_name == "failure":
                failure_bucket_summary.setdefault(failure_bucket, []).append((term, count))

    csv_path = args.output_dir / "construction_lens_trigger_terms.csv"
    md_path = args.output_dir / "construction_lens_trigger_terms.md"
    json_path = args.output_dir / "construction_lens_trigger_terms.json"
    failure_bucket_csv_path = args.output_dir / "construction_failure_buckets.csv"
    risk_summary_csv_path = args.output_dir / "construction_risk_summary.csv"
    risk_summary_md_path = args.output_dir / "construction_risk_summary.md"
    risk_summary_json_path = args.output_dir / "construction_risk_summary.json"
    causal_chain_csv_path = args.output_dir / "construction_causal_chain_summary.csv"
    causal_chain_md_path = args.output_dir / "construction_causal_chain_summary.md"
    causal_chain_json_path = args.output_dir / "construction_causal_chain_summary.json"
    top_failure_pathways_csv_path = args.output_dir / "construction_top_failure_pathways.csv"
    top_failure_pathways_md_path = args.output_dir / "construction_top_failure_pathways.md"
    top_failure_pathways_json_path = args.output_dir / "construction_top_failure_pathways.json"

    _write_csv(output_rows, csv_path)
    failure_bucket_rows: list[dict] = []
    if failure_bucket_summary:
        bucket_term_counts: dict[str, Counter[str]] = {bucket: Counter() for bucket in FAILURE_BUCKET_ORDER}
        bucket_top_pdf: dict[tuple[str, str], Counter[str]] = {}
        for row in rows_by_lens.get("failure", []):
            bucket = _failure_bucket_for_term(row["trigger_term"])
            if not bucket:
                continue
            bucket_term_counts[bucket][row["trigger_term"]] += 1
            bucket_top_pdf.setdefault((bucket, row["trigger_term"]), Counter())[row["pdf_name"]] += 1
        for bucket in FAILURE_BUCKET_ORDER:
            for term, count in bucket_term_counts[bucket].most_common(20):
                top_pdf_name, top_pdf_count = bucket_top_pdf[(bucket, term)].most_common(1)[0]
                failure_bucket_rows.append(
                    {
                        "failure_bucket": bucket,
                        "trigger_term": term,
                        "trigger_kind": "failure_mode",
                        "count": count,
                        "pdf_count": len(bucket_top_pdf[(bucket, term)]),
                        "top_pdf": top_pdf_name,
                        "top_pdf_count": top_pdf_count,
                    }
                )
    _write_failure_bucket_csv(failure_bucket_rows, failure_bucket_csv_path)

    risk_summary_rows: list[dict] = []

    if summary_top_terms.get("building_physics"):
        top_term, count, trigger_kind = summary_top_terms["building_physics"][0]
        top_pdf_name, top_pdf_count, pdf_count = _term_pdf_stats(rows_by_lens["building_physics"], top_term)
        risk_summary_rows.append(
            {
                "lens": "building_physics",
                "top_issue": "Building physics issue",
                "top_term": top_term,
                "trigger_kind": trigger_kind,
                "count": count,
                "pdf_count": pdf_count,
                "top_pdf": top_pdf_name,
                "top_pdf_count": top_pdf_count,
                "notes": "Envelope and thermal-performance signal",
            }
        )

    if summary_top_terms.get("materials"):
        top_term, count, trigger_kind = summary_top_terms["materials"][0]
        top_pdf_name, top_pdf_count, pdf_count = _term_pdf_stats(rows_by_lens["materials"], top_term)
        risk_summary_rows.append(
            {
                "lens": "materials",
                "top_issue": "Material performance",
                "top_term": top_term,
                "trigger_kind": trigger_kind,
                "count": count,
                "pdf_count": pdf_count,
                "top_pdf": top_pdf_name,
                "top_pdf_count": top_pdf_count,
                    "notes": "Method/process vocabulary is excluded from materials-only scoring",
            }
        )

    if summary_top_terms.get("methods_tooling"):
        top_term, count, trigger_kind = summary_top_terms["methods_tooling"][0]
        top_pdf_name, top_pdf_count, pdf_count = _term_pdf_stats(rows_by_lens["methods_tooling"], top_term)
        risk_summary_rows.append(
            {
                "lens": "methods_tooling",
                "top_issue": "Experimental methods",
                "top_term": top_term,
                "trigger_kind": trigger_kind,
                "count": count,
                "pdf_count": pdf_count,
                "top_pdf": top_pdf_name,
                "top_pdf_count": top_pdf_count,
                "notes": "Research-process vocabulary separated from materials",
            }
        )

    failure_bucket_totals = Counter()
    failure_bucket_top_terms: dict[str, tuple[str, int, int]] = {}
    for row in failure_bucket_rows:
        bucket = row["failure_bucket"]
        failure_bucket_totals[bucket] += row["count"]
        current = failure_bucket_top_terms.get(bucket)
        candidate = (row["trigger_term"], row["count"], row["pdf_count"])
        if current is None or candidate[1] > current[1]:
            failure_bucket_top_terms[bucket] = candidate

    if failure_bucket_totals:
        top_bucket = max(failure_bucket_totals.items(), key=lambda item: (item[1], item[0]))[0]
        top_term_info = failure_bucket_top_terms.get(top_bucket)
        if top_term_info is not None:
            top_term, top_count, top_pdf_count = top_term_info
            top_pdf_name = "N/A"
            top_pdf_hits = 0
            for row in failure_bucket_rows:
                if row["failure_bucket"] == top_bucket and row["trigger_term"] == top_term:
                    top_pdf_name = row["top_pdf"]
                    top_pdf_hits = row["top_pdf_count"]
                    top_pdf_count = row["pdf_count"]
                    break
            risk_summary_rows.append(
                {
                    "lens": "failure",
                    "top_issue": top_bucket.title(),
                    "top_term": top_term,
                    "trigger_kind": "failure_mode",
                    "count": top_count,
                    "pdf_count": top_pdf_count,
                    "top_pdf": top_pdf_name,
                    "top_pdf_count": top_pdf_hits,
                    "notes": "Bucketed failure taxonomy",
                }
            )

    if summary_top_terms.get("climate"):
        top_term, count, trigger_kind = summary_top_terms["climate"][0]
        top_pdf_name, top_pdf_count, pdf_count = _term_pdf_stats(rows_by_lens["climate"], top_term)
        risk_summary_rows.append(
            {
                "lens": "climate",
                "top_issue": "Climate hazard",
                "top_term": top_term,
                "trigger_kind": trigger_kind,
                "count": count,
                "pdf_count": pdf_count,
                "top_pdf": top_pdf_name,
                "top_pdf_count": top_pdf_count,
                "notes": "Hazard/exposure/resilience vocabulary",
            }
        )

    if summary_top_terms.get("compliance"):
        top_term, count, trigger_kind = summary_top_terms["compliance"][0]
        top_pdf_name, top_pdf_count, pdf_count = _term_pdf_stats(rows_by_lens["compliance"], top_term)
        risk_summary_rows.append(
            {
                "lens": "compliance",
                "top_issue": "Compliance",
                "top_term": top_term,
                "trigger_kind": trigger_kind,
                "count": count,
                "pdf_count": pdf_count,
                "top_pdf": top_pdf_name,
                "top_pdf_count": top_pdf_count,
                "notes": "Regulatory and code-related vocabulary",
            }
        )

    if summary_top_terms.get("insurance_risk"):
        top_term, count, trigger_kind = summary_top_terms["insurance_risk"][0]
        top_pdf_name, top_pdf_count, pdf_count = _term_pdf_stats(rows_by_lens["insurance_risk"], top_term)
        risk_summary_rows.append(
            {
                "lens": "insurance_risk",
                "top_issue": "Insurance risk",
                "top_term": top_term,
                "trigger_kind": trigger_kind,
                "count": count,
                "pdf_count": pdf_count,
                "top_pdf": top_pdf_name,
                "top_pdf_count": top_pdf_count,
                "notes": "Claims, loss, mitigation, and property-risk vocabulary",
            }
        )

    _write_risk_summary_csv(risk_summary_rows, risk_summary_csv_path)
    _write_risk_summary_markdown(risk_summary_rows, risk_summary_md_path)
    risk_summary_json_path.write_text(
        json.dumps({"rows": risk_summary_rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    causal_chain_rows = _build_causal_chain_rows(summary_top_terms, rows_by_lens.get("failure", []))
    _write_causal_chain_csv(causal_chain_rows, causal_chain_csv_path)
    _write_causal_chain_markdown(causal_chain_rows, causal_chain_md_path)
    causal_chain_json_path.write_text(
        json.dumps({"rows": causal_chain_rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_top_failure_pathways_csv(causal_chain_rows, top_failure_pathways_csv_path)
    _write_top_failure_pathways_markdown(causal_chain_rows, top_failure_pathways_md_path)
    top_failure_pathways_json_path.write_text(
        json.dumps({"rows": causal_chain_rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(
        {
            "pdfs_evaluated": len(pdf_paths),
            "lens_order": lens_order,
            "top_terms": summary_top_terms,
            "top_pdfs": summary_top_pdfs,
            "failure_buckets": failure_bucket_summary,
        },
        md_path,
    )
    json_path.write_text(
        json.dumps(
            {
                "pdfs_evaluated": len(pdf_paths),
                "lens_order": lens_order,
                "top_terms": summary_top_terms,
                "top_pdfs": summary_top_pdfs,
                "failure_buckets": failure_bucket_summary,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {csv_path}")
    print(f"Wrote {failure_bucket_csv_path}")
    print(f"Wrote {risk_summary_csv_path}")
    print(f"Wrote {risk_summary_md_path}")
    print(f"Wrote {risk_summary_json_path}")
    print(f"Wrote {causal_chain_csv_path}")
    print(f"Wrote {causal_chain_md_path}")
    print(f"Wrote {causal_chain_json_path}")
    print(f"Wrote {top_failure_pathways_csv_path}")
    print(f"Wrote {top_failure_pathways_md_path}")
    print(f"Wrote {top_failure_pathways_json_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    for lens_name in lens_order:
        print(f"{lens_name}: {len(rows_by_lens[lens_name])} trigger rows")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())