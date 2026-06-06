from utils import run_multi_folder_scrape
from unittest.mock import Mock

def test_run_scraper_invokes_script(monkeypatch, tmp_path):
    # Patch subprocess.run to simulate a successful run
    called = {}
    def fake_run(*args, **kwargs):
        # Extract the command argument in a subprocess.run-compatible way
        if args:
            called['cmd'] = args[0]
        else:
            called['cmd'] = kwargs.get('args')
        return Mock(returncode=0)
    monkeypatch.setattr(run_multi_folder_scrape.subprocess, 'run', fake_run)
    # Patch Path.exists to return True only for the expected script_path
    orig_exists = run_multi_folder_scrape.Path.exists
    def custom_exists(self):
        script_dir = run_multi_folder_scrape.Path(run_multi_folder_scrape.__file__).resolve().parent
        script_path = script_dir / "scrape_pdfs_phase1.py"
        if str(self) == str(script_path):
            return True
        # Delegate to the original exists method for other paths
        return orig_exists(self)
    monkeypatch.setattr(run_multi_folder_scrape.Path, 'exists', custom_exists)
    # Call run_scraper with dummy args
    expected_domain = 'methods_tooling'
    expected_input = str(tmp_path)
    expected_output = str(tmp_path / 'out.db')
    run_multi_folder_scrape.run_scraper(expected_input, expected_domain, expected_output)
    assert 'cmd' in called
    # Check --domain flag and value
    assert '--domain' in called['cmd']
    idx = called['cmd'].index('--domain')
    assert called['cmd'][idx + 1] == expected_domain
    # Check --input-dir flag and value
    assert '--input-dir' in called['cmd']
    idx = called['cmd'].index('--input-dir')
    assert called['cmd'][idx + 1] == expected_input
    # Check --output-db flag and value
    assert '--output-db' in called['cmd']
    idx = called['cmd'].index('--output-db')
    assert called['cmd'][idx + 1] == expected_output
