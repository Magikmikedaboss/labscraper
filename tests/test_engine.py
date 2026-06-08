import sqlite3
from unittest.mock import patch, Mock

from utils.run_engine import main


def test_main_function_database_creation(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()

    output_db = tmp_path / "test_output.sqlite"

    test_pdf = input_dir / "test.pdf"
    test_pdf.write_bytes(b"Mock PDF content")

    with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
         patch('utils.run_engine.extract_metadata') as mock_metadata, \
         patch('utils.run_engine.chunk_sentences') as mock_sentences:

        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test content"
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}

        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        mock_pdf_open.return_value.__exit__.return_value = False
        mock_metadata.return_value = {
            'title': 'Test',
            'authors': 'Test Author',
            'year': 2023
        }
        mock_sentences.return_value = ['Test sentence.']

        main(
            domain='methods_tooling',
            input_dir=str(input_dir),
            db_path=str(output_db)
        )

    assert output_db.exists()

    with sqlite3.connect(str(output_db)) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        assert 'sources' in tables
        assert 'documents' in tables

        source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        document_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        assert source_count > 0
        assert document_count > 0

        source_row = conn.execute(
            "SELECT title, authors, pdf_file, domain FROM sources LIMIT 1"
        ).fetchone()
        assert source_row[0] == "Test"
        assert source_row[1] == "Test Author"
        assert source_row[2] == "test.pdf"
        assert source_row[3] == "methods_tooling"

        document_row = conn.execute(
            "SELECT file_path, file_type FROM documents LIMIT 1"
        ).fetchone()
        assert document_row[0].endswith("test.pdf")
        assert document_row[1] == "pdf"


def test_main_keeps_construction_sentence_with_measurement_but_no_context(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()

    output_db = tmp_path / "construction_output.sqlite"

    test_pdf = input_dir / "test.pdf"
    test_pdf.write_bytes(b"Mock PDF content")

    with patch("utils.run_engine.pdfplumber.open") as mock_pdf_open, \
         patch("utils.run_engine.extract_metadata") as mock_metadata, \
         patch("utils.run_engine.chunk_sentences") as mock_sentences, \
         patch("utils.run_engine.extract_quantitative_data") as mock_measurements:

        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "The specimen reached 12 MPa after curing."
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}

        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        mock_pdf_open.return_value.__exit__.return_value = False
        mock_metadata.return_value = {
            "title": "Test",
            "authors": "Test Author",
            "year": 2023,
        }
        mock_sentences.return_value = ["The specimen reached 12 MPa after curing."]
        mock_measurements.return_value = [
            {
                "measurement_type": "compressive_strength",
                "value": "12",
                "unit": "MPa",
                "context": "",
            }
        ]

        main(
            domain="construction_science",
            input_dir=str(input_dir),
            db_path=str(output_db),
        )

    with sqlite3.connect(str(output_db)) as conn:
        event_count = conn.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]
        assert event_count == 1


