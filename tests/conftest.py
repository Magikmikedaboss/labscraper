import pytest
from utils.db_init import _init_db_schema

@pytest.fixture(scope="function")
def init_test_schema(tmp_path):
    """Fixture to initialize the test database schema using the shared helper."""
    db_path = tmp_path / "test_db.sqlite"
    _init_db_schema(db_path)
    return db_path
