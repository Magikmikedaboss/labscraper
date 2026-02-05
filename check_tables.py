import sqlite3

db_path = 'runs/all_pdfs_combined.sqlite'
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = cursor.fetchall()
    print(f'Tables in {db_path}:')
    for table in tables:
        print(f'  - {table[0]}')