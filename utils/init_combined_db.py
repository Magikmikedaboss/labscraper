import sqlite3
from pathlib import Path

DB_PATH = Path('output/combined_biohacking_all.sqlite')
SCHEMA_PATH = Path(__file__).resolve().parent / 'schema.sql'

def main():
    DB_PATH.parent.mkdir(exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding='utf-8')

    with sqlite3.connect(DB_PATH) as con:
        con.executescript(schema_sql)

    print(f'✅ Database initialized: {DB_PATH}')

if __name__ == "__main__":
    main()