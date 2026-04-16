"""Additional helper coverage for the core scraping engine."""

from pathlib import Path
from unittest.mock import Mock

from utils.run_engine import (
    chunk_sentences,
    classify_event_type,
    confidence_score,
    detect_decision,
    detect_failure_reason,
    detect_method_tags,
    detect_outcome,
    evidence_strength,
    extract_metadata,
    extract_quantitative_data,
    extract_relationships,
    guess_section,
    guess_stage,
    sha16,
    sha64,
)
from utils.common import now_iso
from utils.event_classification import suggested_keep
from utils.deduplication import normalize_event_key


def test_basic_helpers_return_expected_formats():
    chunks = chunk_sentences("First sentence. Second sentence!\nThird question?")

    assert chunks == ["First sentence.", "Second sentence!", "Third question?"]
    assert now_iso().endswith("Z")
    assert len(sha16("hello")) == 16
    assert len(sha64("hello")) == 64


def test_guess_stage_and_section_cover_all_major_branches():
    assert guess_stage("tested in mouse model") == "in_vivo"
    assert guess_stage("cell line culture assay") == "in_vitro"
    assert guess_stage("randomized patients in phase ii study") == "clinical"
    assert guess_stage("background information only") == "unknown"

    assert guess_section("methods and results overview") == "mixed"
    assert guess_section("methods overview") == "methods"
    assert guess_section("results summary") == "results"
    assert guess_section("discussion and limitations") == "discussion"
    assert guess_section("plain introduction") == "unknown"


def test_extract_metadata_uses_pdf_metadata_and_first_page_text():
    first_page = Mock()
    first_page.extract_text.return_value = (
        "A long and descriptive paper title for validation\n"
        "DOI: 10.1234/example.doi\n"
        "Published in 2024"
    )

    pdf = Mock()
    pdf.metadata = {"Author": "Jane Doe", "CreationDate": "D:20240101000000"}
    pdf.pages = [first_page]

    metadata = extract_metadata(Path("paper.pdf"), pdf)

    assert metadata["authors"] == "Jane Doe"
    assert metadata["year"] == 2024
    assert metadata["doi"] == "10.1234/example.doi"
    assert metadata["title"]


def test_detection_classification_and_confidence_helpers_work_together():
    sentence = (
        "We used LC-MS/MS and observed poor stability, so we decided to optimize "
        "the sequence and IC50 improved to 10 nm."
    )
    sentence_l = sentence.lower()

    tags = detect_method_tags(sentence_l)
    failure_reason = detect_failure_reason(sentence_l)
    decision_taken, decision_driver = detect_decision(sentence_l)
    outcome = detect_outcome(sentence_l)
    event_type = classify_event_type(sentence_l, tags, failure_reason, decision_taken)
    confidence = confidence_score(True, tags, failure_reason, decision_taken, True, sentence_l)

    assert "lc-ms/ms" in tags
    assert failure_reason == "stability_failure"
    # The sentence contains both "decided to" (continued) and "optimize" (modified).
    # DECISION_PHRASES is checked in dict order; "continued" is checked before "modified".
    assert decision_taken in ("continued", "modified")
    assert decision_driver is None
    assert outcome == "positive"
    assert event_type == "stability_issue"
    assert evidence_strength("we demonstrate robust and significant activity") == "strong"
    assert evidence_strength("this may suggest a trend") == "weak"
    assert confidence == "high"
    assert suggested_keep(confidence, event_type, failure_reason, decision_taken, tags) == 1


def test_quantitative_and_relationship_extractors_capture_signals():
    sentence = "CompoundA was more stable than CompoundB and had IC50 of 12.5 nm with half-life 3 h."

    measurements = extract_quantitative_data(sentence)
    relationships = extract_relationships(
        sentence,
        [
            {"entity_name": "COMPOUNDA"},
            {"entity_name": "COMPOUNDB"},
        ],
    )
    event_key = normalize_event_key("efficacy_result", [{"entity_name": "COMPOUNDA"}], 1, sentence)

    measurement_types = {item["measurement_type"] for item in measurements}
    assert {"ic50", "half_life"}.issubset(measurement_types)
    assert relationships[0]["relationship_type"] == "more_stable_than"
    assert event_key.startswith("efficacy_result|COMPOUNDA|1|")
