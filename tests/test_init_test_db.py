from pathlib import Path
import sqlite3

import pytest

from utils import init_test_db


def test_init_test_db_creates_database(tmp_path):
    db_path = tmp_path / "test.sqlite"
    init_test_db.init_test_db(str(db_path))
    assert db_path.exists()

    with sqlite3.connect(db_path) as con:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sources', 'documents', 'research_events')"
            )
        }

    assert "sources" in tables
    assert "documents" in tables
    assert "research_events" in tables


def test_init_test_db_rejects_canonical_db(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    canonical = project_root / "db" / "runs.sqlite"
    with pytest.raises(RuntimeError) as excinfo:
        init_test_db.init_test_db(str(canonical))

    assert "canonical" in str(excinfo.value).lower()
