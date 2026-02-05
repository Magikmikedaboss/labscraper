#!/usr/bin/env python3
"""
Check RSS ingests and view processed data
"""

import sqlite3
import os

def check_rss_ingests():
    """Check RSS ingests in the database"""
    print("📊 RSS INGEST SUMMARY")
    print("=" * 40)
    
    # Check if database exists
    if not os.path.exists('db/runs.sqlite'):
        print("❌ Database not found: db/runs.sqlite")
        return
    
    try:
        conn = sqlite3.connect('db/runs.sqlite')
        cursor = conn.cursor()
        
        # Check for construction science events
        cursor.execute('SELECT COUNT(*) FROM research_events WHERE research_domain="construction_science"')
        construction_events = cursor.fetchone()[0]
        
        # Check for all events
        cursor.execute('SELECT COUNT(*) FROM research_events')
        total_events = cursor.fetchone()[0]
        
        # Check for sources
        cursor.execute('SELECT COUNT(*) FROM sources')
        total_sources = cursor.fetchone()[0]
        
        print(f'Construction science events: {construction_events}')
        print(f'Total events in database: {total_events}')
        print(f'Total sources: {total_sources}')
        
        # Show recent events
        print('\n📝 RECENT EVENTS:')
        cursor.execute('''
            SELECT re.source_id, s.title, re.research_domain, COUNT(*) as event_count 
            FROM research_events re
            JOIN sources s ON re.source_id = s.source_id
            GROUP BY re.source_id 
            ORDER BY event_count DESC 
            LIMIT 5
        ''')
        for row in cursor.fetchall():
            print(f'  Source: {row[0]} ({row[2]}) - {row[3]} events')
        
        # Check PDF cache
        print('\n📁 PDF CACHE:')
        cache_dir = 'input/rss_cache'
        if os.path.exists(cache_dir):
            pdf_files = [f for f in os.listdir(cache_dir) if f.endswith('.pdf')]
            print(f'  Downloaded PDFs: {len(pdf_files)}')
            for pdf_file in pdf_files[:5]:  # Show first 5
                file_path = os.path.join(cache_dir, pdf_file)
                file_size = os.path.getsize(file_path)
                print(f'    - {pdf_file} ({file_size:,} bytes)')
        else:
            print('  No cache directory found')
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Check RSS ingests"""
    check_rss_ingests()

if __name__ == "__main__":
    main()