import sqlite3
from unittest.mock import Mock, patch

from utils.scrape_pdfs_phase1_full import main


def test_phase1_domain_override_respects_explicit_construction_science(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    pdf_path = input_dir / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 sample")
    db_path = tmp_path / "output.sqlite"

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = "Concrete beam load test failed."
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

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

    with patch("utils.scrape_pdfs_phase1_full.pdfplumber.open") as mock_pdf_open, \
         patch("utils.scrape_pdfs_phase1_full.extract_metadata", return_value={}), \
            patch("utils.scrape_pdfs_phase1_full.chunk_sentences", return_value=["Concrete wall moisture failure and vapor control issues."]), \
         patch("utils.scrape_pdfs_phase1_full.extract_entities", side_effect=extract_entities_side_effect), \
         patch("utils.scrape_pdfs_phase1_full.detect_method_tags", return_value=["load_test"]), \
         patch("utils.scrape_pdfs_phase1_full.detect_failure_reason", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_decision", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_outcome", return_value="neutral"), \
         patch("utils.scrape_pdfs_phase1_full.evidence_strength", return_value="low"), \
         patch("utils.scrape_pdfs_phase1_full.confidence_score", return_value="low"):
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        research_domains = {
            row[0]
            for row in con.execute("SELECT DISTINCT research_domain FROM research_events")
        }

    assert research_domains == {"construction_science"}


def test_phase1_suppresses_climate_table_boilerplate(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    pdf_path = input_dir / "climate.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 climate")
    db_path = tmp_path / "output.sqlite"

    boilerplate = "Canadian climate normals 1951-1980 volume pressure temperature humidity climate zone"

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = boilerplate
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

    with patch("utils.scrape_pdfs_phase1_full.pdfplumber.open") as mock_pdf_open, \
         patch("utils.scrape_pdfs_phase1_full.extract_metadata", return_value={}), \
         patch("utils.scrape_pdfs_phase1_full.chunk_sentences", return_value=[boilerplate] * 50), \
         patch("utils.scrape_pdfs_phase1_full.extract_entities", return_value=[{"entity_type": "environment", "entity_name": "CLIMATE", "entity_variant": "", "role": "environment"}]), \
         patch("utils.scrape_pdfs_phase1_full.detect_method_tags", return_value=[]), \
         patch("utils.scrape_pdfs_phase1_full.detect_failure_reason", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_decision", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_outcome", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.evidence_strength", return_value="low"), \
         patch("utils.scrape_pdfs_phase1_full.confidence_score", return_value="low"):
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        event_count = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]

    assert event_count == 0


def test_phase1_suppresses_construction_front_matter(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    pdf_path = input_dir / "front_matter.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 front matter")
    db_path = tmp_path / "output.sqlite"

    front_matter = "Disclaimer This work was prepared as an account of work sponsored by an agency of the United States Government."

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = front_matter
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

    with patch("utils.scrape_pdfs_phase1_full.pdfplumber.open") as mock_pdf_open, \
         patch("utils.scrape_pdfs_phase1_full.extract_metadata", return_value={}), \
         patch("utils.scrape_pdfs_phase1_full.chunk_sentences", return_value=[front_matter]), \
         patch("utils.scrape_pdfs_phase1_full.extract_entities", return_value=[{"entity_type": "environment", "entity_name": "GOVERNMENT", "entity_variant": "", "role": "environment"}]), \
         patch("utils.scrape_pdfs_phase1_full.detect_method_tags", return_value=[]), \
         patch("utils.scrape_pdfs_phase1_full.detect_failure_reason", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_decision", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_outcome", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.evidence_strength", return_value="low"), \
         patch("utils.scrape_pdfs_phase1_full.confidence_score", return_value="low"):
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        event_count = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]

    assert event_count == 0


def test_phase1_suppresses_raw_climate_normal_table_rows(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    pdf_path = input_dir / "canadian_climate_normals.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 climate normals")
    db_path = tmp_path / "output.sqlite"

    row = "Toronto January February March April May June July August September October November December 12.3 14.1 15.2 16.4"

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = row
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

    with patch("utils.scrape_pdfs_phase1_full.pdfplumber.open") as mock_pdf_open, \
         patch("utils.scrape_pdfs_phase1_full.extract_metadata", return_value={"title": "Canadian Climate Normals"}), \
         patch("utils.scrape_pdfs_phase1_full.chunk_sentences", return_value=[row] * 25), \
         patch("utils.scrape_pdfs_phase1_full.extract_entities", return_value=[{"entity_type": "environment", "entity_name": "TORONTO", "entity_variant": "", "role": "environment"}]), \
         patch("utils.scrape_pdfs_phase1_full.detect_method_tags", return_value=[]), \
         patch("utils.scrape_pdfs_phase1_full.detect_failure_reason", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_decision", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_outcome", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.evidence_strength", return_value="low"), \
         patch("utils.scrape_pdfs_phase1_full.confidence_score", return_value="low"):
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        event_count = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]

    assert event_count == 0


def test_phase1_keeps_climate_load_when_tied_to_building_context(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    pdf_path = input_dir / "climate_load.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 climate load")
    db_path = tmp_path / "output.sqlite"

    sentence = "Canadian climate normals suggest higher heating degree days and moisture risk for wall assembly insulation performance."

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = sentence
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

    with patch("utils.scrape_pdfs_phase1_full.pdfplumber.open") as mock_pdf_open, \
         patch("utils.scrape_pdfs_phase1_full.extract_metadata", return_value={"title": "Canadian Climate Normals"}), \
         patch("utils.scrape_pdfs_phase1_full.chunk_sentences", return_value=[sentence]), \
         patch("utils.scrape_pdfs_phase1_full.extract_entities", return_value=[{"entity_type": "environment", "entity_name": "CLIMATE", "entity_variant": "", "role": "environment"}]), \
         patch("utils.scrape_pdfs_phase1_full.detect_method_tags", return_value=[]), \
         patch("utils.scrape_pdfs_phase1_full.detect_failure_reason", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_decision", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_outcome", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.evidence_strength", return_value="low"), \
         patch("utils.scrape_pdfs_phase1_full.confidence_score", return_value="med"):
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        rows = con.execute("SELECT event_type FROM research_events").fetchall()

    assert rows == [("climate_load",)]


def test_phase1_meaningful_construction_sentence_is_kept(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    pdf_path = input_dir / "meaningful.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 meaningful")
    db_path = tmp_path / "output.sqlite"

    sentence = "Concrete wall assembly showed moisture failure and vapor control issues."

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = sentence
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

    with patch("utils.scrape_pdfs_phase1_full.pdfplumber.open") as mock_pdf_open, \
         patch("utils.scrape_pdfs_phase1_full.extract_metadata", return_value={}), \
         patch("utils.scrape_pdfs_phase1_full.chunk_sentences", return_value=[sentence]), \
         patch("utils.scrape_pdfs_phase1_full.extract_entities", return_value=[{"entity_type": "material", "entity_name": "CONCRETE", "entity_variant": "", "role": "material"}]), \
         patch("utils.scrape_pdfs_phase1_full.detect_method_tags", return_value=[]), \
         patch("utils.scrape_pdfs_phase1_full.detect_failure_reason", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_decision", return_value="unknown"), \
         patch("utils.scrape_pdfs_phase1_full.detect_outcome", return_value="negative"), \
         patch("utils.scrape_pdfs_phase1_full.evidence_strength", return_value="moderate"), \
         patch("utils.scrape_pdfs_phase1_full.confidence_score", return_value="med"):
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        main(input_dir=str(input_dir), db_path=str(db_path), domain="construction_science")

    with sqlite3.connect(db_path) as con:
        rows = con.execute("SELECT research_domain, event_type FROM research_events").fetchall()

    assert rows == [("construction_science", "moisture_failure")]