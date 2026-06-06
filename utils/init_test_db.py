"""
Initialize a test SQLite database with all required tables for CI and local testing.
"""
import sqlite3
from pathlib import Path

def init_test_db(db_path="test.db"):
    """Initialize schema at ``db_path`` for test use.

    Note:
        This function does not prompt before opening an existing target DB.
        If ``db_path`` already exists, schema initialization is applied in-place,
        which may modify the existing database.
    """
    # Canonical DB guard: prevent overwriting production DB
    project_root = Path(__file__).resolve().parents[1]
    canonical_db = (project_root / "db" / "runs.sqlite").resolve()
    target_db = Path(db_path).resolve()
    if target_db == canonical_db:
        raise RuntimeError(f"Refusing to initialize canonical DB at {canonical_db} from init_test_db!")

    # Always use the canonical root-level schema.sql
    schema_path = project_root / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema.sql at {schema_path}")
    schema_sql = schema_path.read_text(encoding="utf-8")
    with sqlite3.connect(str(target_db)) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(schema_sql)
    print(f"Initialized test DB at {target_db}")

if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "test.db"
    init_test_db(db_path)
