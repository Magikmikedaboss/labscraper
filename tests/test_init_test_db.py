import pytest

from utils import init_test_db


def test_init_test_db_creates_database(tmp_path):
    db_path = tmp_path / "test.sqlite"
    init_test_db.init_test_db(str(db_path))
    assert db_path.exists()


def test_init_test_db_rejects_canonical_db(tmp_path):
    project_root = init_test_db.Path(__file__).resolve().parents[1]
    canonical = project_root / "db" / "runs.sqlite"
    with pytest.raises(RuntimeError):
        init_test_db.init_test_db(str(canonical))
