from utils import run_multi_folder_scrape

def test_run_scraper_invokes_script(monkeypatch, tmp_path):
    # Patch subprocess.run to simulate a successful run
    called = {}
    def fake_run(cmd, capture_output, timeout):
        called['cmd'] = cmd
        class Result:
            returncode = 0
        return Result()
    monkeypatch.setattr(run_multi_folder_scrape.subprocess, 'run', fake_run)
    # Patch script_path to always exist
    monkeypatch.setattr(run_multi_folder_scrape.Path, 'exists', lambda self: True)
    # Call run_scraper with dummy args
    run_multi_folder_scrape.run_scraper(str(tmp_path), 'methods_tooling', str(tmp_path / 'out.db'))
    assert 'cmd' in called
    assert '--domain' in called['cmd']
    assert '--input-dir' in called['cmd']
    assert '--output-db' in called['cmd']
