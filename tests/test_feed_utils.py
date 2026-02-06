"""Tests for feed utilities using pytest"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from utils.feed_utils import extract_pdf_links, parse_feed, test_feed


class TestExtractPDFLinks:
    """Test PDF link extraction from feed entries"""
    
    def test_extract_pdf_links_from_summary(self):
        """Test PDF extraction from entry summary"""
        entry = {
            'summary': 'Download paper: https://example.com/paper.pdf',
            'links': []
        }
        result = extract_pdf_links(entry)
        
        assert len(result) == 1
        assert result[0] == 'https://example.com/paper.pdf'

    def test_extract_pdf_links_from_links(self):
        """Test PDF extraction from entry links"""
        entry = {
            'summary': 'No PDFs in summary',
            'links': [
                {'href': 'https://example.com/other.html'},
                {'href': 'https://example.com/paper.pdf'}
            ]
        }
        result = extract_pdf_links(entry)
        
        assert len(result) == 1
        assert result[0] == 'https://example.com/paper.pdf'

    def test_extract_pdf_links_handles_empty_entry(self):
        """Test graceful handling of entries with no PDFs"""
        entry = {'summary': 'No PDFs here', 'links': []}
        result = extract_pdf_links(entry)
        
        assert result == []

    def test_extract_pdf_links_mixed_content(self):
        """Test PDF extraction with mixed content"""
        entry = {
            'summary': 'Paper: https://example.com/paper.pdf and code: https://github.com/example',
            'links': [
                {'href': 'https://example.com/other.pdf'},
                {'href': 'https://example.com/image.png'}
            ]
        }
        result = extract_pdf_links(entry)
        
        assert len(result) == 2
        assert 'https://example.com/paper.pdf' in result
        assert 'https://example.com/other.pdf' in result

    def test_extract_pdf_links_case_insensitive(self):
        """Test PDF extraction is case insensitive"""
        entry = {
            'summary': 'Download: https://example.com/PAPER.PDF',
            'links': []
        }
        result = extract_pdf_links(entry)
        
        assert len(result) == 1
        assert result[0] == 'https://example.com/PAPER.PDF'


class TestParseFeed:
    """Test feed parsing functionality"""
    
    @patch('utils.feed_utils.feedparser.parse')
    def test_parse_feed_valid_url(self, mock_parse):
        """Test parsing a valid feed URL"""
        mock_feed = Mock()
        mock_feed.entries = [
            {'title': 'Test Entry', 'summary': 'Test summary', 'links': []}
        ]
        mock_parse.return_value = mock_feed
        
        result = parse_feed('https://example.com/feed.rss')
        
        assert result == mock_feed
        mock_parse.assert_called_once_with('https://example.com/feed.rss')

    @patch('utils.feed_utils.feedparser.parse')
    def test_parse_feed_invalid_url(self, mock_parse):
        """Test error handling for invalid feed URLs"""
        # feedparser returns empty dict for bad URLs
        mock_parse.return_value = {'entries': []}
        
        result = parse_feed('not-a-valid-url')
        
        assert isinstance(result, dict)
        assert result['entries'] == []

    @patch('utils.feed_utils.feedparser.parse')
    def test_parse_feed_network_error(self, mock_parse):
        """Test handling of network errors during feed parsing"""
        mock_parse.side_effect = Exception("Network error")
        
        result = parse_feed('https://example.com/feed.rss')
        
        assert isinstance(result, dict)
        assert result == {}


class TestTestFeed:
    """Test feed testing functionality"""
    
    @patch('utils.feed_utils.parse_feed')
    @patch('utils.feed_utils.extract_pdf_links')
    def test_test_feed_successful(self, mock_extract, mock_parse):
        """Test successful feed testing"""
        mock_entry = {
            'title': 'Test Entry',
            'summary': 'Test summary with https://example.com/paper.pdf',
            'links': []
        }
        mock_parse.return_value = {'entries': [mock_entry]}
        mock_extract.return_value = ['https://example.com/paper.pdf']
        
        result = test_feed('https://example.com/feed.rss', 'Test Feed')
        
        assert result['success'] is True
        assert result['entries'] == 1
        assert result['pdfs'] == 1
        assert result['title'] == 'Test Entry'

    @patch('utils.feed_utils.parse_feed')
    def test_test_feed_no_entries(self, mock_parse):
        """Test feed testing with no entries"""
        mock_parse.return_value = {'entries': []}
        
        result = test_feed('https://example.com/feed.rss', 'Test Feed')
        
        assert result['success'] is True
        assert result['entries'] == 0
        assert result['pdfs'] == 0

    @patch('utils.feed_utils.parse_feed')
    def test_test_feed_with_keywords(self, mock_parse):
        """Test feed testing with keyword filtering"""
        mock_entry = {
            'title': 'Construction materials research',
            'summary': 'Study on construction materials',
            'links': []
        }
        mock_parse.return_value = {'entries': [mock_entry]}
        
        result = test_feed(
            'https://example.com/feed.rss', 
            'Test Feed', 
            check_keywords=['construction', 'materials']
        )
        
        assert result['success'] is True
        assert result['entries'] == 1
        assert result['pdfs'] == 0  # No PDFs, but keywords matched

    @patch('utils.feed_utils.parse_feed')
    def test_test_feed_no_keywords_match(self, mock_parse):
        """Test feed testing with no keyword matches"""
        mock_entry = {
            'title': 'Unrelated topic',
            'summary': 'This is not about construction',
            'links': []
        }
        mock_parse.return_value = {'entries': [mock_entry]}
        
        result = test_feed(
            'https://example.com/feed.rss', 
            'Test Feed', 
            check_keywords=['construction', 'materials']
        )
        
        assert result['success'] is True
        assert result['entries'] == 0  # No entries matched keywords
        assert result['pdfs'] == 0