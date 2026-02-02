#!/usr/bin/env python3
import sqlite3
import os

def check_database():
    db_path = 'db/runs.sqlite'
    
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables in database: {tables}")
        
        # Check if sources table exists
        if 'sources' in tables:
            cursor.execute("SELECT COUNT(*) FROM sources")
            count = cursor.fetchone()[0]
            print(f"Sources table has {count} records")
        else:
            print("Sources table does not exist")
            
        conn.close()
        print("Database check completed successfully")
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database()