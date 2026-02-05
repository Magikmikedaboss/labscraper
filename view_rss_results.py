#!/usr/bin/env python3
"""
View RSS ingestion results comprehensively
"""

import sqlite3
import os

def view_rss_results():
    """View comprehensive RSS ingestion results"""
    print("📊 RSS INGESTION RESULTS")
    print("=" * 50)
    
    if not os.path.exists('db/runs.sqlite'):
        print("❌ Database not found")
        return
    
    conn = sqlite3.connect('db/runs.sqlite')
    cursor = conn.cursor()
    
    # Database overview
    print("📈 DATABASE OVERVIEW")
    print("-" * 30)
    
    # Check sources
    cursor.execute('SELECT COUNT(*) FROM sources')
    source_count = cursor.fetchone()[0]
    print(f"Sources: {source_count}")
    
    # Check events
    cursor.execute('SELECT COUNT(*) FROM research_events')
    event_count = cursor.fetchone()[0]
    print(f"Events: {event_count}")
    
    # Check entities
    cursor.execute('SELECT COUNT(*) FROM entities')
    entity_count = cursor.fetchone()[0]
    print(f"Entities: {entity_count}")
    
    # Check recent RSS sources (from O'Reilly feed)
    print("\n📰 RSS SOURCES (Recent)")
    print("-" * 30)
    cursor.execute('SELECT source_id, title, pdf_file FROM sources ORDER BY source_id DESC LIMIT 5')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
        if row[2]:
            print(f"    PDF: {row[2]}")
    
    # Check PDF cache
    print("\n📁 PDF CACHE")
    print("-" * 20)
    cache_dir = 'input/rss_cache'
    if os.path.exists(cache_dir):
        pdf_files = [f for f in os.listdir(cache_dir) if f.endswith('.pdf')]
        print(f"Downloaded PDFs: {len(pdf_files)}")
        for pdf_file in pdf_files:
            file_path = os.path.join(cache_dir, pdf_file)
            file_size = os.path.getsize(file_path)
            print(f"  - {pdf_file} ({file_size:,} bytes)")
    else:
        print("No cache directory found")
    
    # Check event types
    print("\n🎯 EVENT ANALYSIS")
    print("-" * 25)
    cursor.execute('SELECT event_type, COUNT(*) FROM research_events GROUP BY event_type ORDER BY COUNT(*) DESC LIMIT 5')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} events")
    
    # Check domains
    print("\n🌍 DOMAINS")
    print("-" * 15)
    cursor.execute('SELECT research_domain, COUNT(*) FROM research_events GROUP BY research_domain ORDER BY COUNT(*) DESC')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} events")
    
    conn.close()

def main():
    """View RSS results"""
    view_rss_results()

if __name__ == "__main__":
    main()