from pathlib import Path
import sqlite3

DB_PATH = Path("output") / "peptide_intel.sqlite"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    con = sqlite3.connect(DB_PATH)
    try:
        con.executescript(schema)
        con.commit()
        print(f"✅ Database initialized at: {DB_PATH.resolve()}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
