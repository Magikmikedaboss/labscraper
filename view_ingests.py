#!/usr/bin/env python3
"""
View RSS ingests - database and cache
"""

import sqlite3
import os

def view_database():
    """Check database contents"""
    print("📊 DATABASE CONTENTS")
    print("=" * 30)
    
    if not os.path.exists('db/runs.sqlite'):
        print("❌ Database not found")
        return
    
    try:
        conn = sqlite3.connect('db/runs.sqlite')
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = cursor.fetchall()
        print(f"Tables found: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

def view_pdf_cache():
    """Check PDF cache"""
    print("\n📁 PDF CACHE")
    print("=" * 20)
    
    cache_dir = 'input/rss_cache'
    if not os.path.exists(cache_dir):
        print("❌ No cache directory")
        return
    
    pdf_files = [f for f in os.listdir(cache_dir) if f.endswith('.pdf')]
    print(f"Downloaded PDFs: {len(pdf_files)}")
    
    for pdf_file in pdf_files:
        file_path = os.path.join(cache_dir, pdf_file)
        file_size = os.path.getsize(file_path)
        print(f"  - {pdf_file} ({file_size:,} bytes)")

def main():
    """View ingests"""
    view_database()
    view_pdf_cache()

if __name__ == "__main__":
    main()