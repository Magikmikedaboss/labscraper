from utils.db_utils import inspect_database
from pathlib import Path

# Test for lines 38–46, 52–53, 55, 59 in tools/inspect_db.py

def test_inspect_database_basic(init_test_schema, capsys):
    # Use the shared schema fixture to create a DB
    db_path = init_test_schema
    # Should print table info
    inspect_database(str(db_path), detailed=True)
    out = capsys.readouterr().out
    assert "DATABASE INSPECTION" in out
    assert "Tables found" in out
    assert "sources" in out

# Add more tests for error handling and edge cases as needed
