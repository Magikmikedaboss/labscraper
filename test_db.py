#!/usr/bin/env python3
import sqlite3

def test_db():
    conn = sqlite3.connect('runs/construction_science_final.sqlite')
    tables = [r[0] for r in conn.execute('SELECT name FROM sqlite_master WHERE type="table"')]
    print('Tables:', tables)
    conn.close()

if __name__ == "__main__":
    test_db()