
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, Mock
import gc

from utils.run_engine import main
from utils.db_init import _init_db_schema


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

        # Force release of SQLite handles before file cleanup
        gc.collect()

        assert output_db.exists()

        conn = sqlite3.connect(str(output_db))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert 'sources' in tables
        assert 'documents' in tables
        cursor.close()
        conn.close()
        gc.collect()
