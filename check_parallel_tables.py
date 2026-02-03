#!/usr/bin/env python3
"""
Check tables in parallel test database
"""

import sqlite3
from pathlib import Path

def check_parallel_tables():
    db_path = Path('runs/construction_parallel_test.sqlite')
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        tables = cur.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()
        print('Tables in parallel test database:')
        for table in tables:
            print(f'  - {table[0]}')

if __name__ == "__main__":
    check_parallel_tables()