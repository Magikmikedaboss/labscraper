from utils.reporting_utils import resolve_seeds_version

def test_env_var(monkeypatch):
    monkeypatch.setenv("SEEDS_VERSION", "env123")
    assert resolve_seeds_version() == "env123"

def test_git_success(monkeypatch):
    monkeypatch.delenv("SEEDS_VERSION", raising=False)
    def fake_run_cmd(cmd, **kwargs):
        return "gitver456"
    assert resolve_seeds_version(run_cmd=fake_run_cmd) == "gitver456"

def test_git_timeout(monkeypatch):
    monkeypatch.delenv("SEEDS_VERSION", raising=False)
    import subprocess

    def fake_run_cmd(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=1.0)

    assert resolve_seeds_version(run_cmd=fake_run_cmd) == "unknown"

def test_git_exception(monkeypatch):
    monkeypatch.delenv("SEEDS_VERSION", raising=False)
    def fake_run_cmd(cmd, **kwargs):
        raise Exception("fail")
    assert resolve_seeds_version(run_cmd=fake_run_cmd) == "unknown"
