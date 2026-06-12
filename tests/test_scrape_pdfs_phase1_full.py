import sqlite3
from unittest.mock import Mock, patch

import pytest

from utils.scrape_pdfs_phase1_full import main


@pytest.fixture
def mock_phase1_pipeline():
    with patch("utils.scrape_pdfs_phase1_full.pdfplumber.open") as pdf_open, \
         patch("utils.scrape_pdfs_phase1_full.extract_metadata") as extract_metadata_mock, \
         patch("utils.scrape_pdfs_phase1_full.chunk_sentences") as chunk_sentences_mock, \
         patch("utils.scrape_pdfs_phase1_full.extract_entities") as extract_entities_mock, \
         patch("utils.scrape_pdfs_phase1_full.detect_method_tags") as detect_method_tags_mock, \
         patch("utils.scrape_pdfs_phase1_full.detect_failure_reason") as detect_failure_reason_mock, \
         patch("utils.scrape_pdfs_phase1_full.detect_decision") as detect_decision_mock, \
         patch("utils.scrape_pdfs_phase1_full.detect_outcome") as detect_outcome_mock, \
         patch("utils.scrape_pdfs_phase1_full.extract_quantitative_data") as extract_quantitative_data_mock, \
         patch("utils.scrape_pdfs_phase1_full.evidence_strength") as evidence_strength_mock, \
         patch("utils.scrape_pdfs_phase1_full.confidence_score") as confidence_score_mock:
        pdf_open.return_value.__enter__.return_value = Mock()
        yield {
            "pdf_open": pdf_open,
            "extract_metadata": extract_metadata_mock,
            "chunk_sentences": chunk_sentences_mock,
            "extract_entities": extract_entities_mock,
            "detect_method_tags": detect_method_tags_mock,
            "detect_failure_reason": detect_failure_reason_mock,
            "detect_decision": detect_decision_mock,
            "detect_outcome": detect_outcome_mock,
            "extract_quantitative_data": extract_quantitative_data_mock,
            "evidence_strength": evidence_strength_mock,
            "confidence_score": confidence_score_mock,
        }


def prepare_mock_phase1_case(
    tmp_path,
    mock_phase1_pipeline,
    *,
    pdf_name: str,
    pdf_bytes: bytes,
    page_text: str,
    chunk_sentences_result,
    metadata: dict | None = None,
    entities=None,
    detect_method_tags_result=None,
    detect_failure_reason_result: str = "unknown",
    detect_decision_result: str = "unknown",
    detect_outcome_result: str = "unknown",
    extract_entities_side_effect=None,
    evidence_strength_result: str = "low",
    confidence_score_result: str = "low",
):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    pdf_path = input_dir / pdf_name
    pdf_path.write_bytes(pdf_bytes)
    db_path = tmp_path / "output.sqlite"

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = page_text
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

    mock_phase1_pipeline["pdf_open"].return_value.__enter__.return_value = mock_pdf
    mock_phase1_pipeline["extract_metadata"].return_value = metadata or {}
    mock_phase1_pipeline["chunk_sentences"].return_value = chunk_sentences_result
    if extract_entities_side_effect is not None:
        mock_phase1_pipeline["extract_entities"].side_effect = extract_entities_side_effect
    else:
        mock_phase1_pipeline["extract_entities"].return_value = entities or []
    mock_phase1_pipeline["detect_method_tags"].return_value = detect_method_tags_result or []
    mock_phase1_pipeline["detect_failure_reason"].return_value = detect_failure_reason_result
    mock_phase1_pipeline["detect_decision"].return_value = detect_decision_result
    mock_phase1_pipeline["detect_outcome"].return_value = detect_outcome_result
    mock_phase1_pipeline["extract_quantitative_data"].return_value = []
    mock_phase1_pipeline["evidence_strength"].return_value = evidence_strength_result
    mock_phase1_pipeline["confidence_score"].return_value = confidence_score_result

    return input_dir, db_path, mock_pdf


def test_phase1_domain_override_respects_explicit_construction_science(
    tmp_path, mock_phase1_pipeline
):
    def extract_entities_side_effect(sentence, domain, SEEDS_DIR=None):
        assert domain == "construction_science"
        return [
            {
                "entity_type": "material",
                "entity_name": "CONCRETE",
                "entity_variant": "",
                "role": "material",
            }
        ]

    input_dir, db_path, _ = prepare_mock_phase1_case(
        tmp_path,
        mock_phase1_pipeline,
        pdf_name="sample.pdf",
        pdf_bytes=b"%PDF-1.4 sample",
        page_text="Concrete beam load test failed.",
        chunk_sentences_result=["Concrete wall moisture failure and vapor control issues."],
        detect_method_tags_result=["load_test"],
        detect_outcome_result="neutral",
        extract_entities_side_effect=extract_entities_side_effect,
    )
    main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        research_domains = {
            row[0]
            for row in con.execute("SELECT DISTINCT research_domain FROM research_events")
        }

    assert research_domains == {"construction_science"}


def test_phase1_suppresses_climate_table_boilerplate(tmp_path, mock_phase1_pipeline):
    boilerplate = "Canadian climate normals 1951-1980 volume pressure temperature humidity climate zone"
    input_dir, db_path, _ = prepare_mock_phase1_case(
        tmp_path,
        mock_phase1_pipeline,
        pdf_name="climate.pdf",
        pdf_bytes=b"%PDF-1.4 climate",
        page_text=boilerplate,
        chunk_sentences_result=[boilerplate] * 50,
        entities=[
            {"entity_type": "environment", "entity_name": "CLIMATE", "entity_variant": "", "role": "environment"}
        ],
    )
    main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        event_count = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]

    assert event_count == 0


def test_phase1_suppresses_construction_front_matter(tmp_path, mock_phase1_pipeline):
    front_matter = "Disclaimer This work was prepared as an account of work sponsored by an agency of the United States Government."
    input_dir, db_path, _ = prepare_mock_phase1_case(
        tmp_path,
        mock_phase1_pipeline,
        pdf_name="front_matter.pdf",
        pdf_bytes=b"%PDF-1.4 front matter",
        page_text=front_matter,
        chunk_sentences_result=[front_matter],
        entities=[
            {"entity_type": "environment", "entity_name": "GOVERNMENT", "entity_variant": "", "role": "environment"}
        ],
    )
    main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        event_count = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]

    assert event_count == 0


def test_phase1_suppresses_raw_climate_normal_table_rows(tmp_path, mock_phase1_pipeline):
    row = "Toronto January February March April May June July August September October November December 12.3 14.1 15.2 16.4"
    input_dir, db_path, _ = prepare_mock_phase1_case(
        tmp_path,
        mock_phase1_pipeline,
        pdf_name="canadian_climate_normals.pdf",
        pdf_bytes=b"%PDF-1.4 climate normals",
        page_text=row,
        chunk_sentences_result=[row] * 25,
        metadata={"title": "Canadian Climate Normals"},
        entities=[
            {"entity_type": "environment", "entity_name": "TORONTO", "entity_variant": "", "role": "environment"}
        ],
    )
    main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        event_count = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]

    assert event_count == 0


def test_phase1_requires_construction_context_for_generic_thermal_terms(tmp_path, mock_phase1_pipeline):
    noisy_sentence = "The culture was incubated at 37 C and the temperature increased during analysis."
    input_dir, db_path, _ = prepare_mock_phase1_case(
        tmp_path,
        mock_phase1_pipeline,
        pdf_name="thermal_noise.pdf",
        pdf_bytes=b"%PDF-1.4 thermal noise",
        page_text=noisy_sentence,
        chunk_sentences_result=[noisy_sentence],
        entities=[
            {"entity_type": "environment", "entity_name": "TEMPERATURE", "entity_variant": "", "role": "environment"}
        ],
    )
    main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        event_count = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]

    assert event_count == 0


def test_phase1_keeps_construction_thermal_context(tmp_path, mock_phase1_pipeline):
    sentence = "The concrete wall assembly showed thermal performance loss at elevated temperature."
    input_dir, db_path, _ = prepare_mock_phase1_case(
        tmp_path,
        mock_phase1_pipeline,
        pdf_name="construction_thermal.pdf",
        pdf_bytes=b"%PDF-1.4 construction thermal",
        page_text=sentence,
        chunk_sentences_result=[sentence],
        entities=[
            {"entity_type": "material", "entity_name": "CONCRETE", "entity_variant": "", "role": "material"}
        ],
        detect_outcome_result="negative",
        evidence_strength_result="moderate",
        confidence_score_result="med",
    )
    main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        rows = con.execute("SELECT event_type FROM research_events").fetchall()

    assert rows == [("thermal_performance",)]


def test_phase1_keeps_climate_load_when_tied_to_building_context(tmp_path, mock_phase1_pipeline):
    sentence = "Canadian climate normals suggest higher heating degree days and moisture risk for wall assembly insulation performance."
    input_dir, db_path, _ = prepare_mock_phase1_case(
        tmp_path,
        mock_phase1_pipeline,
        pdf_name="climate_load.pdf",
        pdf_bytes=b"%PDF-1.4 climate load",
        page_text=sentence,
        chunk_sentences_result=[sentence],
        metadata={"title": "Canadian Climate Normals"},
        entities=[
            {"entity_type": "environment", "entity_name": "CLIMATE", "entity_variant": "", "role": "environment"}
        ],
        detect_outcome_result="unknown",
        evidence_strength_result="low",
        confidence_score_result="med",
    )
    main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        rows = con.execute("SELECT event_type FROM research_events").fetchall()

    assert rows == [("climate_load",)]


def test_phase1_meaningful_construction_sentence_is_kept(tmp_path, mock_phase1_pipeline):
    sentence = "Concrete wall assembly showed moisture failure and vapor control issues."
    input_dir, db_path, _ = prepare_mock_phase1_case(
        tmp_path,
        mock_phase1_pipeline,
        pdf_name="meaningful.pdf",
        pdf_bytes=b"%PDF-1.4 meaningful",
        page_text=sentence,
        chunk_sentences_result=[sentence],
        entities=[
            {"entity_type": "material", "entity_name": "CONCRETE", "entity_variant": "", "role": "material"}
        ],
        detect_outcome_result="negative",
        evidence_strength_result="moderate",
        confidence_score_result="med",
    )
    main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        rows = con.execute("SELECT research_domain, event_type FROM research_events").fetchall()

    assert rows == [("construction_science", "moisture_failure")]