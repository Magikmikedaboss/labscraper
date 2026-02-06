#!/usr/bin/env python3
"""
Unified database inspection utility
Replaces: check_db.py, check_db_status.py, check_db_structure.py, 
check_db_tables.py, check_construction_db.py, check_entities.py,
view_ingests.py, view_rss_results.py, check_rss_ingests.py, etc.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Add the parent directory to the path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db_utils import inspect_database, connect_db, show_pdf_cache

def main():
    parser = argparse.ArgumentParser(description='Inspect database')
    parser.add_argument('--db', default='db/runs.sqlite', 
                       help='Database path')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed stats')
    parser.add_argument('--events', type=int, default=5,
                       help='Number of recent events to show')
    parser.add_argument('--sources', type=int, default=5,
                       help='Number of top sources to show')
    parser.add_argument('--cache', action='store_true',
                       help='Show PDF cache contents')
    args = parser.parse_args()
    
    # Basic inspection
    inspect_database(args.db, detailed=args.detailed)
    
    # Additional details
    try:
        conn = connect_db(args.db)
        
        if args.events:
            from utils.db_utils import show_recent_events
            show_recent_events(conn, args.events)
        
        if args.sources:
            from utils.db_utils import show_top_sources
            show_top_sources(conn, args.sources)
        
        from utils.db_utils import get_entity_distribution, get_event_type_distribution, get_domain_distribution
        get_entity_distribution(conn)
        get_event_type_distribution(conn)
        get_domain_distribution(conn)
        
        conn.close()
    except Exception as e:
        print(f"⚠️  Could not show details: {e}")
    
    if args.cache:
        show_pdf_cache()

if __name__ == "__main__":
    main()