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
    extract_metadata,
    extract_quantitative_data,
    guess_section,
    guess_stage,
    sha16,
    sha64,
)
from utils.event_classification import ConfidenceInput, DECISION_PHRASES
from utils.data_extractors import extract_relationships
from utils.common import now_iso
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
        "CompoundA was more stable than CompoundB. "
        "We used LC-MS/MS and observed poor stability, so we decided to optimize "
        "the sequence. IC50 improved to 10 nm and half-life increased to 2 hours."
    )
    sentence_l = sentence.lower()

    tags = detect_method_tags(sentence_l)
    failure_reason = detect_failure_reason(sentence_l)
    decision_taken, decision_driver = detect_decision(sentence_l)
    outcome = detect_outcome(sentence_l)
    event_type = classify_event_type(sentence_l, tags, failure_reason, decision_taken)

    score = confidence_score(
        ConfidenceInput(
            has_entity=True,
            method_tags=tags,
            failure_reason=failure_reason,
            decision_taken=decision_taken,
            has_measurements=True,
            sentence_l=sentence_l
        )
    )
    assert score == "high"

    assert "lc-ms/ms" in tags
    assert failure_reason == "stability_failure"
    # The sentence contains both "decided to" (continued) and "optimize" (modified).
    # Check that the detected decision is one of the allowed decision types.
    allowed = set(DECISION_PHRASES.keys())
    assert decision_taken in allowed
    assert decision_driver is None
    assert outcome == "positive"
    assert event_type == "stability_issue"
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
    assert len(relationships) > 0, "Expected at least one relationship to be extracted"
    assert relationships[0]["relationship_type"] == "more_stable_than"
    # event_key format is 'event_type|ENTITY1|page|snippet_hash'
    assert event_key.startswith("efficacy_result|COMPOUNDA|1|")

def test_init_db_schema_if_needed(monkeypatch, tmp_path):
    """Covers both canonical and non-canonical DB path branches."""

    from utils.run_engine import _init_db_schema_if_needed

    called = {}
    def fake_init_db_schema(path):
        called['path'] = path

    # Patch the imported symbol in utils.run_engine, not the definition site
    import utils.run_engine
    monkeypatch.setattr(utils.run_engine, "init_db_schema", fake_init_db_schema)
    monkeypatch.setattr(utils.run_engine, "_db_has_all_tables", lambda _: True, raising=False)

    # Should NOT call for canonical path
    canonical = str(Path("db/runs.sqlite").resolve())
    _init_db_schema_if_needed(canonical)
    assert 'path' not in called

    # Should call for non-canonical path
    non_canonical = str((tmp_path / "test.sqlite").resolve())
    _init_db_schema_if_needed(non_canonical)
    assert called['path'] == non_canonical
