from utils.db_utils import inspect_database

# Test for inspect_database function in utils/db_utils.py
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

# TODOs for error handling and edge cases:
# - test_missing_db: Should handle missing DB file gracefully
# - test_corrupt_db: Should handle corrupted DB/schema
# - test_permission_error: Should handle permission denied on DB file
# - test_empty_tables: Should handle DBs with empty tables
# - test_invalid_params: Should handle invalid query params
# - test_large_result_set: Should handle very large result sets
