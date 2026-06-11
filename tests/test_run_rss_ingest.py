from pathlib import Path
from types import SimpleNamespace

from requests.exceptions import HTTPError
from unittest.mock import Mock, patch

import pytest

from run_rss_ingest import _process_pdf_urls, download_pdf, get_pdf_links_from_feed, process_feed_entry
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


class TestDownloadPdf:
    @patch("run_rss_ingest.requests.get")
    def test_download_pdf_logs_and_skips_on_403(
        self,
        mock_get,
        tmp_path,
        caplog,
    ):
        def make_http_error(status_code: int) -> HTTPError:
            error = HTTPError(f"{status_code} error")
            error.response = SimpleNamespace(status_code=status_code)
            return error

        first_response = SimpleNamespace(raise_for_status=Mock(side_effect=make_http_error(403)))
        ranged_response = SimpleNamespace(raise_for_status=Mock(side_effect=make_http_error(403)))
        mock_get.side_effect = [first_response, ranged_response]

        with caplog.at_level("WARNING"):
            result = download_pdf("https://www.fema.gov/example.pdf", tmp_path)

        assert result is None
        assert any("HTTP 403" in message for message in caplog.messages)


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
    @patch("run_rss_ingest.find_abstract_links")
    @patch("run_rss_ingest.get_pdf_links_from_entry")
    @patch("run_rss_ingest.is_valid_pdf", return_value=True)
    @patch("run_rss_ingest.download_pdf")
    def test_pdf_success_prevents_duplicate_abstract_processing(
        self,
        mock_download_pdf,
        mock_is_valid_pdf,
        mock_get_pdf_links_from_entry,
        mock_find_abstract_links,
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
    @patch("run_rss_ingest._score_construction_review_lenses", return_value={"building_physics": 0, "materials": 0, "climate": 0, "failure": 0, "compliance": 0, "insurance_risk": 0})
    @patch("run_rss_ingest.is_valid_pdf", return_value=True)
    @patch("run_rss_ingest.download_pdf")
    @patch("run_rss_ingest.get_pdf_links_from_entry")
    def test_construction_triage_skips_non_keep_pdfs(
        self,
        mock_get_pdf_links_from_entry,
        mock_download_pdf,
        mock_is_valid_pdf,
        mock_score_review_lenses,
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

    @patch("run_rss_ingest.process_html_document")
    @patch("run_rss_ingest.process_pdf")
    @patch("run_rss_ingest.scan_pdf")
    @patch("run_rss_ingest._score_construction_review_lenses", return_value={"building_physics": 0, "materials": 0, "climate": 0, "failure": 0, "compliance": 0, "insurance_risk": 0})
    @patch("run_rss_ingest.is_valid_pdf", return_value=True)
    @patch("run_rss_ingest.download_pdf")
    @patch("run_rss_ingest.route_construction_source")
    def test_construction_triage_stores_keep_and_review_pdfs(
        self,
        mock_route_construction_source,
        mock_download_pdf,
        mock_is_valid_pdf,
        mock_score_review_lenses,
        mock_scan_pdf,
        mock_process_pdf,
        mock_process_html_document,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.setattr("run_rss_ingest.RSS_ORGANIZED_DIR", tmp_path / "organized")
        mock_route_construction_source.return_value = SimpleNamespace(decision="keep", reason="ok")

        pdf_path = tmp_path / "cache" / "rss" / "doc.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
        mock_download_pdf.return_value = pdf_path

        for decision, expected_processed in [("keep", 1), ("review", 0)]:
            mock_scan_pdf.reset_mock()
            mock_process_pdf.reset_mock()
            mock_scan_pdf.return_value = TriagedSource(
                file_path=str(pdf_path),
                title="Construction paper",
                detected_domain="construction_science",
                keep_skip_review=decision,
                confidence="med",
                construction_signals="roof; wall",
                contamination_signals="",
                reason=f"{decision} decision",
            )

            result = _process_pdf_urls(
                ["https://example.com/doc.pdf"],
                "construction_science",
                Path("db/test.sqlite"),
                "Moisture and wall assembly durability",
                source_triage_rows=[],
            )

            bucket_path = tmp_path / "organized" / "construction_science" / decision / "doc.pdf"
            assert bucket_path.exists()
            assert result["pdf_processed"] == expected_processed
            if decision == "keep":
                mock_process_pdf.assert_called_once()
            else:
                mock_process_pdf.assert_not_called()

    @patch("run_rss_ingest.process_html_document")
    @patch("run_rss_ingest.process_pdf")
    @patch("run_rss_ingest._score_construction_review_lenses")
    @patch("run_rss_ingest.scan_pdf")
    @patch("run_rss_ingest.is_valid_pdf", return_value=True)
    @patch("run_rss_ingest.download_pdf")
    @patch("run_rss_ingest.route_construction_source")
    def test_construction_review_pdf_promotes_to_keep_with_lens_hits(
        self,
        mock_route_construction_source,
        mock_download_pdf,
        mock_is_valid_pdf,
        mock_scan_pdf,
        mock_score_review_lenses,
        mock_process_pdf,
        mock_process_html_document,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.setattr("run_rss_ingest.RSS_ORGANIZED_DIR", tmp_path / "organized")
        mock_route_construction_source.return_value = SimpleNamespace(decision="keep", reason="ok")
        mock_score_review_lenses.return_value = {
            "building_physics": 3,
            "materials": 0,
            "climate": 0,
            "failure": 0,
            "compliance": 0,
            "insurance_risk": 0,
        }

        pdf_path = tmp_path / "cache" / "rss" / "review.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
        mock_download_pdf.return_value = pdf_path
        mock_scan_pdf.return_value = TriagedSource(
            file_path=str(pdf_path),
            title="Construction review paper",
            detected_domain="construction_science",
            keep_skip_review="review",
            confidence="med",
            construction_signals="roof; wall",
            contamination_signals="",
            reason="review decision",
        )
        mock_process_pdf.return_value = 0

        result = _process_pdf_urls(
            ["https://example.com/review.pdf"],
            "construction_science",
            Path("db/test.sqlite"),
            "Moisture and wall assembly durability",
            source_triage_rows=[],
        )

        assert result["pdf_processed"] == 1
        assert result["pdf_events"] == 0
        assert mock_process_pdf.call_count == 1
        assert (tmp_path / "organized" / "construction_science" / "review" / "review.pdf").exists()
        assert (tmp_path / "organized" / "construction_science" / "keep" / "review.pdf").exists()
