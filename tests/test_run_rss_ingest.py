from pathlib import Path
from types import SimpleNamespace

import pytest
from unittest.mock import patch

from run_rss_ingest import get_pdf_links_from_feed, process_feed_entry
from utils.source_triage import TriagedSource


class TestGetPdfLinksFromFeed:
    @patch("run_rss_ingest.time.sleep")
    @patch("run_rss_ingest.time.monotonic")
    @patch("run_rss_ingest.requests.get")
    @patch("run_rss_ingest.parse_feed")
    def test_html_discovery_is_rate_limited_per_host(
        self,
        mock_parse,
        mock_get,
        mock_monotonic,
        mock_sleep,
    ):
        mock_parse.return_value = SimpleNamespace(
            entries=[
                {"link": "https://example.com/a", "title": "A"},
                {"link": "https://example.com/b", "title": "B"},
            ]
        )
        mock_get.return_value = SimpleNamespace(ok=True, text="<html></html>")
        mock_monotonic.side_effect = [100.0, 100.1, 100.2, 100.3]

        result = get_pdf_links_from_feed("https://example.com/feed.xml")

        assert result == []
        assert mock_get.call_count == 2
        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args.args[0] == pytest.approx(0.9)


class TestHybridFeedEntryProcessing:
    @patch("run_rss_ingest.process_html_document")
    @patch("run_rss_ingest.process_pdf")
    @patch("run_rss_ingest.is_valid_pdf", return_value=True)
    @patch("run_rss_ingest.download_pdf")
    @patch("run_rss_ingest.get_pdf_links_from_entry")
    def test_pdf_path_processes_pdf_and_skips_abstract_fallback(
        self,
        mock_get_pdf_links_from_entry,
        mock_download_pdf,
        mock_is_valid_pdf,
        mock_process_pdf,
        mock_process_html_document,
        tmp_path,
    ):
        entry = {"title": "Entry", "link": "https://example.com/article"}
        mock_get_pdf_links_from_entry.return_value = ["https://example.com/doc.pdf"]
        mock_download_pdf.return_value = tmp_path / "cache" / "rss" / "doc.pdf"
        mock_process_pdf.return_value = 7

        result = process_feed_entry(entry, domain="construction_science", db_path=Path("db/test.sqlite"))

        assert result["pdf_processed"] == 1
        assert result["pdf_events"] == 7
        assert result["used_abstract_fallback"] is False
        mock_process_pdf.assert_called_once()
        mock_process_html_document.assert_not_called()
        mock_process_pdf.assert_called_with(
            mock_download_pdf.return_value,
            "construction_science",
            Path("db/test.sqlite"),
            source_url="https://example.com/doc.pdf",
            source_title="Entry",
        )

    @patch("run_rss_ingest.process_html_document")
    @patch("run_rss_ingest.extract_abstract_text_from_url")
    @patch("run_rss_ingest.find_abstract_links")
    @patch("run_rss_ingest.get_pdf_links_from_entry")
    def test_abstract_fallback_processes_text_when_pdf_missing(
        self,
        mock_get_pdf_links_from_entry,
        mock_find_abstract_links,
        mock_extract_abstract_text_from_url,
        mock_process_html_document,
    ):
        entry = {"title": "Entry", "link": "https://example.com/article"}
        mock_get_pdf_links_from_entry.return_value = []
        mock_find_abstract_links.return_value = ["https://doi.org/10.1234/example"]
        mock_extract_abstract_text_from_url.return_value = "This abstract reports moisture failure and remediation in detail."
        mock_process_html_document.return_value = 3

        result = process_feed_entry(entry, domain="construction_science", db_path=Path("db/test.sqlite"))

        assert result["pdf_processed"] == 0
        assert result["abstract_processed"] == 1
        assert result["abstract_events"] == 3
        assert result["used_abstract_fallback"] is True
        mock_process_html_document.assert_called_once_with(
            source_url="https://doi.org/10.1234/example",
            source_title="Entry",
            text="This abstract reports moisture failure and remediation in detail.",
            domain="construction_science",
            db_path=Path("db/test.sqlite"),
            source_type="abstract_fallback",
        )

    @patch("run_rss_ingest.process_html_document")
    @patch("run_rss_ingest.process_pdf")
    @patch("run_rss_ingest.is_valid_pdf", return_value=True)
    @patch("run_rss_ingest.download_pdf")
    @patch("run_rss_ingest.find_abstract_links")
    @patch("run_rss_ingest.get_pdf_links_from_entry")
    def test_pdf_success_prevents_duplicate_abstract_processing(
        self,
        mock_get_pdf_links_from_entry,
        mock_find_abstract_links,
        mock_download_pdf,
        mock_is_valid_pdf,
        mock_process_pdf,
        mock_process_html_document,
        tmp_path,
    ):
        entry = {"title": "Entry", "link": "https://example.com/article"}
        mock_get_pdf_links_from_entry.return_value = ["https://example.com/doc.pdf"]
        mock_find_abstract_links.return_value = ["https://doi.org/10.1234/example"]
        mock_download_pdf.return_value = tmp_path / "cache" / "rss" / "doc.pdf"
        mock_process_pdf.return_value = 4

        result = process_feed_entry(entry, domain="construction_science", db_path=Path("db/test.sqlite"))

        assert result["pdf_processed"] == 1
        assert result["pdf_events"] == 4
        assert result["used_abstract_fallback"] is False
        mock_process_html_document.assert_not_called()

    @patch("run_rss_ingest.process_html_document")
    @patch("run_rss_ingest.process_pdf")
    @patch("run_rss_ingest.scan_pdf")
    @patch("run_rss_ingest.is_valid_pdf", return_value=True)
    @patch("run_rss_ingest.download_pdf")
    @patch("run_rss_ingest.get_pdf_links_from_entry")
    def test_construction_triage_skips_non_keep_pdfs(
        self,
        mock_get_pdf_links_from_entry,
        mock_download_pdf,
        mock_is_valid_pdf,
        mock_scan_pdf,
        mock_process_pdf,
        mock_process_html_document,
        tmp_path,
    ):
        entry = {"title": "Entry", "link": "https://example.com/article"}
        mock_get_pdf_links_from_entry.return_value = ["https://example.com/doc.pdf"]
        mock_download_pdf.return_value = tmp_path / "cache" / "rss" / "doc.pdf"
        mock_scan_pdf.return_value = TriagedSource(
            file_path=str(mock_download_pdf.return_value),
            title="Stem cell assay paper",
            detected_domain="biomedical",
            keep_skip_review="skip",
            confidence="high",
            construction_signals="",
            contamination_signals="stem cell; assay; protein",
            reason="strong biomedical contamination",
        )

        result = process_feed_entry(
            entry,
            domain="construction_science",
            db_path=Path("db/test.sqlite"),
            source_triage_rows=[],
        )

        assert result["pdf_processed"] == 0
        assert result["pdf_events"] == 0
        assert result["used_abstract_fallback"] is False
        mock_process_pdf.assert_not_called()
        mock_process_html_document.assert_not_called()
