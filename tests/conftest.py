
import sys
import gc
import pytest
from utils.db_init import init_db_schema

# Ensure lingering file handles are finalized before tmp dirs are removed on Windows
@pytest.fixture(autouse=True)
def _win_release_file_locks():
    yield
    if sys.platform == "win32":
        gc.collect()

@pytest.fixture(scope="function")
def init_test_schema(tmp_path):
    """Fixture to initialize the test database schema using the shared helper."""
    db_path = tmp_path / "test_db.sqlite"
    init_db_schema(db_path)
    return db_path
