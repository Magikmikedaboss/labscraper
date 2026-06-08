from utils.export import export_dual_lens
import sqlite3

class DummyScorer:
    def __init__(self, dual=True):
        self._dual = dual
    def is_dual_lens(self): return self._dual
    def get_overlay_ids(self): return ["overlay1", "overlay2"]
    def apply_event_scores(self, event): return {"overlay1": 1, "overlay2": 2}



class DummyCursor:
    def execute(self, *a, **k):
        return self
    def fetchall(self):
        return []
    def __iter__(self):
        return iter([])

class DummyCon:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def cursor(self): return DummyCursor()
    def close(self): pass


class DummySqlite3:
    @staticmethod
    def connect(*a, **k):
        return DummyCon()

    Row = object


def test_export_dual_lens_smoke(monkeypatch, tmp_path):
    import importlib
    module = importlib.import_module("utils.export.export_dual_lens")
    monkeypatch.setattr(module, "load_domain_config", lambda domain_id: {"name": "Test Domain", "overlays": {"overlay1": {}, "overlay2": {}}})
    monkeypatch.setattr(module, "OverlayScorer", lambda config: DummyScorer())

    db_path = tmp_path / "runs.sqlite"
    sqlite3.connect(db_path).close()

    import utils.export.aggregation
    monkeypatch.setattr(utils.export.aggregation, "sqlite3", DummySqlite3)
    # Should not raise
    export_dual_lens(str(db_path), "construction_science", output_dir=str(tmp_path))

    # Assert expected export files are created and non-empty
    output_files = [f for f in tmp_path.glob("*") if f.name != db_path.name]
    assert output_files, f"No export files created in {tmp_path}"
    for f in output_files:
        assert f.is_file(), f"Expected file but found: {f}"
        assert f.stat().st_size > 0, f"Output file {f} is empty"
