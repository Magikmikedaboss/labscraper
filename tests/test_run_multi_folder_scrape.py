import sys
from unittest.mock import Mock

from utils import run_multi_folder_scrape

def test_run_scraper_invokes_script(monkeypatch, tmp_path):
    # Patch subprocess.run to simulate a successful run
    called = {}
    def fake_run(*args, **kwargs):
        # Extract the command argument in a subprocess.run-compatible way
        if args:
            called['cmd'] = args[0]
        else:
            called['cmd'] = kwargs.get('args')
        called['kwargs'] = kwargs
        return Mock(returncode=0)
    monkeypatch.setattr(run_multi_folder_scrape.subprocess, 'run', fake_run)
    script_dir = tmp_path / "script_dir"
    script_dir.mkdir()
    expected_script_path = script_dir / "scrape_pdfs_phase1.py"
    expected_script_path.write_text("print('dummy scraper')\n", encoding="utf-8")
    monkeypatch.setattr(run_multi_folder_scrape, "__file__", str(script_dir / "run_multi_folder_scrape.py"))
    # Call run_scraper with dummy args
    expected_domain = 'methods_tooling'
    expected_input = str(tmp_path)
    expected_output = str(tmp_path / 'out.db')
    run_multi_folder_scrape.run_scraper(expected_input, expected_domain, expected_output)
    assert 'cmd' in called
    cmd = called['cmd']
    assert cmd[0] == sys.executable
    assert cmd[1] == str(expected_script_path)
    # Check --domain flag and value
    assert '--domain' in cmd
    idx = cmd.index('--domain')
    assert cmd[idx + 1] == expected_domain
    # Check --input-dir flag and value
    assert '--input-dir' in cmd
    idx = cmd.index('--input-dir')
    assert cmd[idx + 1] == expected_input
    # Check --output-db flag and value
    assert '--output-db' in cmd
    idx = cmd.index('--output-db')
    assert cmd[idx + 1] == expected_output
    assert called['kwargs'].get('capture_output') is False
    assert called['kwargs'].get('timeout') == 600
