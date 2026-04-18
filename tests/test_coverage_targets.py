
import types
import sys
from unittest import mock
from utils.axon_domains import DomainProfile
from utils import pattern_intelligence
from utils import run_multi_folder_scrape
from utils import scrape_all_pdfs_recursive

def test_domain_profile_methods():
    profile = DomainProfile(
        id="test",
        name="Test Domain",
        description="desc",
        claims_mode="observational_only",
        domain_profile_version="1.0",
        seed_overlays={},
        exclusions={"terms": ["forbidden"]},
        pattern_emphasis={},
        language={"allowed": ["en"], "forbidden": ["badword"]},
        output_allowed_phrases=["ok"]
    )
    # get_output_allowed_phrases
    assert profile.get_output_allowed_phrases() == ["ok"]
    # is_excluded_text
    assert profile.is_excluded_text("This contains forbidden stuff.")
    assert not profile.is_excluded_text("This is fine.")

def test_get_outcome_signals(tmp_path, monkeypatch):
    # Patch SEEDS_DIR to tmp_path
    monkeypatch.setattr(pattern_intelligence, "SEEDS_DIR", tmp_path)
    # No file: should warn and return empty signals
    signals = pattern_intelligence._get_outcome_signals()
    assert isinstance(signals, dict)
    # Create a file and test loading
    data = {"positive": ["good"], "neutral": [], "negative": [], "replication": []}
    (tmp_path / "outcome_signals.json").write_text(str(data).replace("'", '"'))
    pattern_intelligence._OUTCOME_SIGNALS = None  # reset cache
    signals = pattern_intelligence._get_outcome_signals()
    assert "positive" in signals

def test_outcome_signals_class():
    s = pattern_intelligence.OutcomeSignals(positive=1, neutral=2, negative=3, replication=4)
    assert s.total() == 10

def test_run_scraper(monkeypatch):
    # Patch subprocess.run to simulate success
    monkeypatch.setattr(run_multi_folder_scrape.subprocess, "run", lambda *a, **k: types.SimpleNamespace(returncode=0))
    ret = run_multi_folder_scrape.run_scraper("input", "domain", "db")
    assert ret == 0
    # Simulate timeout
    def raise_timeout(*a, **k):
        raise run_multi_folder_scrape.subprocess.TimeoutExpired(cmd="", timeout=1)
    monkeypatch.setattr(run_multi_folder_scrape.subprocess, "run", raise_timeout)
    assert run_multi_folder_scrape.run_scraper("input", "domain", "db") == 1

def test_main_configs(monkeypatch):
    # Patch run_scraper to avoid real calls
    monkeypatch.setattr(run_multi_folder_scrape, "run_scraper", lambda *a, **k: 0)
    # Patch sys.argv
    monkeypatch.setattr(sys, "argv", ["prog"])
    # Patch input to avoid stdin error
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")
    # Should not raise
    run_multi_folder_scrape.main()

def test_find_all_pdfs(tmp_path):
    # Create nested dirs and PDFs
    d1 = tmp_path / "a"
    d1.mkdir()
    d2 = tmp_path / "b"
    d2.mkdir()
    (d1 / "f1.pdf").write_bytes(b"%PDF-1.4")
    (d2 / "f2.PDF").write_bytes(b"%PDF-1.4")
    (d2 / "not_a_pdf.txt").write_text("hi")
    pdfs = scrape_all_pdfs_recursive.find_all_pdfs([str(tmp_path)])
    assert any(str(p).endswith(".pdf") or str(p).endswith(".PDF") for p in pdfs)

def test_main_smoke(monkeypatch):
    # Patch argument parser to avoid real CLI
    monkeypatch.setattr(scrape_all_pdfs_recursive, "find_all_pdfs", lambda x: [])
    monkeypatch.setattr(scrape_all_pdfs_recursive, "process_single_pdf", lambda *a, **k: None)
    monkeypatch.setattr(scrape_all_pdfs_recursive, "Pool", lambda *a, **k: mock.MagicMock())
    monkeypatch.setattr(scrape_all_pdfs_recursive, "tqdm", lambda x, **k: x)
    # Patch sys.argv
    import sys
    monkeypatch.setattr(sys, "argv", ["prog", "--root-dirs", "foo", "--domain", "bar", "--output-db", "baz"])
    # Should not raise
    try:
        scrape_all_pdfs_recursive.main()
    except SystemExit:
        pass
