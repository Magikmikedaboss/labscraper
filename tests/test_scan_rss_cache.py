from pathlib import Path

import pytest

from tools import scan_rss_cache


def test_main_defaults_cache_dir(monkeypatch):
    seen = {}

    def fake_scan_cache(cache_dir: Path) -> None:
        seen["cache_dir"] = cache_dir

    monkeypatch.setattr(scan_rss_cache, "scan_cache", fake_scan_cache)

    exit_code = scan_rss_cache.main([])

    assert exit_code == 0
    assert seen["cache_dir"] == Path("data/cache/rss")


def test_main_accepts_cache_dir_argument(monkeypatch, tmp_path):
    seen = {}

    def fake_scan_cache(cache_dir: Path) -> None:
        seen["cache_dir"] = cache_dir

    monkeypatch.setattr(scan_rss_cache, "scan_cache", fake_scan_cache)

    custom_cache = tmp_path / "rss"
    exit_code = scan_rss_cache.main([str(custom_cache)])

    assert exit_code == 0
    assert seen["cache_dir"] == custom_cache


def test_main_accepts_cache_dir_flag(monkeypatch, tmp_path):
    seen = {}

    def fake_scan_cache(cache_dir: Path) -> None:
        seen["cache_dir"] = cache_dir

    monkeypatch.setattr(scan_rss_cache, "scan_cache", fake_scan_cache)

    custom_cache = tmp_path / "rss"
    exit_code = scan_rss_cache.main(["--cache-dir", str(custom_cache)])

    assert exit_code == 0
    assert seen["cache_dir"] == custom_cache


def test_scan_cache_propagates_unexpected_errors(monkeypatch, tmp_path):
    pdf_path = tmp_path / "bad.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    class Boom(RuntimeError):
        pass

    def boom_open(*args, **kwargs):
        raise Boom("unexpected failure")

    monkeypatch.setattr(scan_rss_cache.pdfplumber, "open", boom_open)

    with pytest.raises(Boom, match="unexpected failure"):
        scan_rss_cache.scan_cache(tmp_path)
