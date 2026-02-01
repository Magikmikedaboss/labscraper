#!/usr/bin/env python3
import sqlite3
import os

def check_database(db_path):
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return []
    try:
        with sqlite3.connect(db_path) as con:
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            print(f"Tables in {db_path}: {[t[0] for t in tables]}")
            return tables
    except Exception as e:
        print(f"Error checking {db_path}: {e}")
        return []

if __name__ == "__main__":
    databases = [
        "runs/peptide_intel.sqlite",
        "runs/all_pdfs_combined.sqlite",
        "runs/construction_science_test.sqlite"
    ]
    
    for db in databases:
        check_database(db)