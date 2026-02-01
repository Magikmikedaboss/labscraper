# This script initializes the peptide_intel.sqlite database schema using Python (no sqlite3 CLI required)
import sqlite3
from pathlib import Path

# Use the canonical schema file to avoid schema drift
SCHEMA_PATH = Path(__file__).resolve().parent.parent / 'utils' / 'schema.sql'

def load_schema():
    return SCHEMA_PATH.read_text(encoding='utf-8')

def main():
    db_path = Path('output/peptide_intel.sqlite')
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = load_schema()
    con = sqlite3.connect(str(db_path))
    try:
        # Enable foreign key enforcement for this connection
        con.execute("PRAGMA foreign_keys = ON;")
        con.executescript(schema)
        print(f"Initialized schema in {db_path.resolve()}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
