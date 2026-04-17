from utils.db_utils import inspect_database

# Test for lines 38–46, 52–53, 55, 59 in tools/inspect_db.py

def test_inspect_database_basic(init_test_schema, caplog):
    # Use the shared schema fixture to create a DB
    db_path = init_test_schema
    # Should log table info
    with caplog.at_level("INFO"):
        inspect_database(str(db_path), detailed=True)
    log_output = "\n".join(caplog.messages)
    assert "DATABASE INSPECTION" in log_output
    assert "Tables found" in log_output
    assert "sources" in log_output

# Add more tests for error handling and edge cases as needed
