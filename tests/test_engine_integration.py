

import gc
import pytest
import sqlite3
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from utils.run_engine import main
from utils.db_init import _init_db_schema

def test_main_function_falsy_domain_uses_default():
    # NOTE: This test intentionally omits an explicit _init_db_schema() call.
    # main() internally calls _init_db_schema_if_needed(), which initializes the schema for non-canonical/test DBs.
    # This ensures the test exercises main()'s fallback DB initialization logic as intended.
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        output_db = Path(temp_dir) / "test_output.sqlite"

        # Create a mock PDF file
        test_pdf = input_dir / "test.pdf"
        test_pdf.write_text("Mock PDF content")

        # Should handle falsy domain gracefully (uses default/fallback)
        with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
             patch('utils.run_engine.extract_metadata') as mock_metadata, \
             patch('utils.run_engine.chunk_sentences') as mock_sentences:

            mock_pdf = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test content"
            mock_pdf.pages = [mock_page]
            mock_pdf.metadata = {}
            mock_pdf_open.return_value.__enter__.return_value = mock_pdf
            mock_metadata.return_value = {'title': 'Test', 'authors': 'Test Author', 'year': 2023}
            mock_sentences.return_value = ['Test sentence.']

            main(
                domain='',  # Falsy domain triggers fallback
                input_dir=str(input_dir),
                db_path=str(output_db)
            )

        gc.collect()
        assert output_db.exists()

def test_main_function_database_creation():
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        output_db = Path(temp_dir) / "test_output.sqlite"
        _init_db_schema(str(output_db))

        test_pdf = input_dir / "test.pdf"
        test_pdf.write_text("Mock PDF content")

        with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
             patch('utils.run_engine.extract_metadata') as mock_metadata, \
             patch('utils.run_engine.chunk_sentences') as mock_sentences:

            mock_pdf = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test content"
            mock_pdf.pages = [mock_page]
            mock_pdf.metadata = {}
            mock_pdf_open.return_value.__enter__.return_value = mock_pdf
            mock_metadata.return_value = {'title': 'Test', 'authors': 'Test Author', 'year': 2023}
            mock_sentences.return_value = ['Test sentence.']

            main(
                domain='methods_tooling',
                input_dir=str(input_dir),
                db_path=str(output_db)
            )

        gc.collect()
        assert output_db.exists()

        conn = sqlite3.connect(str(output_db))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert 'sources' in tables
        assert 'documents' in tables
        assert 'research_events' in tables
        assert 'entities' in tables
        assert 'event_entities' in tables
        assert 'quantitative_measurements' in tables
        assert 'entity_relationships' in tables
        conn.close()

@pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issue with SQLite")
def test_main_function_error_handling():
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        output_db = Path(temp_dir) / "test_output.sqlite"
        test_pdf = input_dir / "test.pdf"
        test_pdf.write_text("Mock PDF content")

        # Ensure the DB/schema exists before main is called
        _init_db_schema(str(output_db))
        with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open:
            mock_pdf_open.side_effect = Exception("Processing error")
            with pytest.raises(SystemExit) as e:
                main(
                    domain='methods_tooling',
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
            assert e.value.code == 1
        gc.collect()
        assert output_db.exists()

def test_main_function_multiple_pdfs():
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        output_db = Path(temp_dir) / "test_output.sqlite"
        _init_db_schema(str(output_db))

        for i in range(2):
            test_pdf = input_dir / f"test_{i}.pdf"
            test_pdf.write_text(f"Mock PDF content {i}")


        with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
             patch('utils.run_engine.extract_metadata') as mock_metadata, \
             patch('utils.run_engine.chunk_sentences') as mock_sentences:

            mock_pdf = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test content"
            mock_pdf.pages = [mock_page]
            mock_pdf.metadata = {}
            mock_pdf_open.return_value.__enter__.return_value = mock_pdf
            mock_metadata.return_value = {'title': 'Test', 'authors': 'Test Author', 'year': 2023}
            mock_sentences.return_value = ['Test sentence.']

            main(
                domain='methods_tooling',
                input_dir=str(input_dir),
                db_path=str(output_db)
            )

        assert mock_pdf_open.call_count == 2
        gc.collect()
        assert output_db.exists()

def test_main_function_domain_specific_processing():
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        test_pdf = input_dir / "test.pdf"
        test_pdf.write_text("Mock PDF content")
        domains = ['methods_tooling', 'drug_discovery', 'construction_science']
        for domain in domains:
            output_db = Path(temp_dir) / f"test_output_{domain}.sqlite"
            _init_db_schema(str(output_db))
            with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
                 patch('utils.run_engine.extract_metadata') as mock_metadata, \
                 patch('utils.run_engine.chunk_sentences') as mock_sentences:

                mock_pdf = Mock()
                mock_page = Mock()
                mock_page.extract_text.return_value = "Test content"
                mock_pdf.pages = [mock_page]
                mock_pdf.metadata = {}
                mock_pdf_open.return_value.__enter__.return_value = mock_pdf
                mock_metadata.return_value = {'title': 'Test', 'authors': 'Test Author', 'year': 2023}
                mock_sentences.return_value = ['Test sentence.']

                main(
                    domain=domain,
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
            gc.collect()
            assert output_db.exists()
