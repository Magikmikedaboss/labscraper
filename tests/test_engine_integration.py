"""Integration tests for the main engine functionality using pytest"""
import pytest
import tempfile
import sqlite3
import gc
from pathlib import Path
from unittest.mock import patch, Mock
from utils.run_engine import main


class TestEngineIntegration:
    """Test engine integration functionality"""
    
    @pytest.mark.skip(reason="Windows file locking issue with SQLite")
    def test_main_function_basic(self):
        """Test basic engine functionality with mock data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input_pdfs"
            input_dir.mkdir()
            output_db = Path(temp_dir) / "test_output.sqlite"
            
            # Create a mock PDF file
            test_pdf = input_dir / "test.pdf"
            test_pdf.write_text("Mock PDF content")
            
            # Mock the PDF processing functions
            with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
                 patch('utils.run_engine.extract_metadata') as mock_metadata, \
                 patch('utils.run_engine.chunk_sentences') as mock_sentences:
                
                # Mock PDF object
                mock_pdf = Mock()
                mock_page = Mock()
                mock_page.extract_text.return_value = "Test content"
                mock_pdf.pages = [mock_page]
                mock_pdf.metadata = {}
                mock_pdf_open.return_value.__enter__.return_value = mock_pdf
                mock_metadata.return_value = {'title': 'Test', 'authors': 'Test Author', 'year': 2023}
                mock_sentences.return_value = ['Test sentence.']
                
                # Run the engine
                main(
                    domain='methods_tooling',
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
            
            # Force garbage collection to release file handles
            gc.collect()
            
            # Verify database was created
            assert output_db.exists()
            
            # Verify database has expected structure
            with sqlite3.connect(str(output_db)) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Should have core tables
                assert 'sources' in tables
                assert 'documents' in tables
                assert 'research_events' in tables
                assert 'entities' in tables
                assert 'event_entities' in tables

    def test_main_function_no_pdfs(self):
        """Test engine behavior with no PDF files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input_pdfs"
            input_dir.mkdir()
            output_db = Path(temp_dir) / "test_output.sqlite"
            
            # Run the engine with empty directory
            with pytest.raises(SystemExit) as exc_info:
                main(
                    domain='methods_tooling',
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
            
            # Should exit with error code
            assert exc_info.type is SystemExit

    def test_main_function_invalid_domain(self):
        """Test engine behavior with invalid domain"""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input_pdfs"
            input_dir.mkdir()
            output_db = Path(temp_dir) / "test_output.sqlite"
            
            # Create a mock PDF file
            test_pdf = input_dir / "test.pdf"
            test_pdf.write_text("Mock PDF content")
            
            # Should handle invalid domain gracefully (uses default)
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
                
                # Run the engine
                main(
                    domain='invalid_domain',
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
            
            gc.collect()
                
            # Should still create database
            assert output_db.exists()

    def test_main_function_database_creation(self):
        """Test that the engine creates a valid database"""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input_pdfs"
            input_dir.mkdir()
            output_db = Path(temp_dir) / "test_output.sqlite"
            
            # Create a mock PDF file
            test_pdf = input_dir / "test.pdf"
            test_pdf.write_text("Mock PDF content")
            
            # Mock the processing to avoid actual PDF parsing
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
                
                # Run the engine
                main(
                    domain='methods_tooling',
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
            
            gc.collect()
                
            # Verify database was created
            assert output_db.exists()
            
            # Verify database has expected structure
            conn = sqlite3.connect(str(output_db))
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Should have core tables
            assert 'sources' in tables
            assert 'documents' in tables
            assert 'research_events' in tables
            assert 'entities' in tables
            assert 'event_entities' in tables
            assert 'quantitative_measurements' in tables
            assert 'entity_relationships' in tables
            
            conn.close()

    @pytest.mark.skip(reason="Windows file locking issue with SQLite")
    def test_main_function_error_handling(self):
        """Test engine error handling"""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input_pdfs"
            input_dir.mkdir()
            output_db = Path(temp_dir) / "test_output.sqlite"
            
            # Create a mock PDF file
            test_pdf = input_dir / "test.pdf"
            test_pdf.write_text("Mock PDF content")
            
            # Test with processing error
            with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open:
                mock_pdf_open.side_effect = Exception("Processing error")
                
                # Should handle the error gracefully and complete without raising
                main(
                    domain='methods_tooling',
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
            
            gc.collect()
                
            # Verify database was still created despite the error
            assert output_db.exists()

    def test_main_function_multiple_pdfs(self):
        """Test engine with multiple PDF files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input_pdfs"
            input_dir.mkdir()
            output_db = Path(temp_dir) / "test_output.sqlite"
            
            # Create multiple mock PDF files
            for i in range(2):
                test_pdf = input_dir / f"test_{i}.pdf"
                test_pdf.write_text(f"Mock PDF content {i}")
            
            # Mock the processing
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
                
                # Run the engine
                main(
                    domain='methods_tooling',
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
            
            gc.collect()
                
            # Should process all PDFs
            assert mock_pdf_open.call_count == 2
            assert output_db.exists()

    def test_main_function_domain_specific_processing(self):
        """Test domain-specific processing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input_pdfs"
            input_dir.mkdir()
            
            # Create a mock PDF file
            test_pdf = input_dir / "test.pdf"
            test_pdf.write_text("Mock PDF content")
            
            # Test different domains with unique database paths
            domains = ['methods_tooling', 'drug_discovery', 'construction_science']
            
            for domain in domains:
                output_db = Path(temp_dir) / f"test_output_{domain}.sqlite"
                
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
                    
                    # Run the engine
                    main(
                        domain=domain,
                        input_dir=str(input_dir),
                        db_path=str(output_db)
                    )
                
                gc.collect()
                    
                # Should handle all domains
                assert output_db.exists()
