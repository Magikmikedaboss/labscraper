#!/usr/bin/env python3
"""
Fixed SQLite query script to check domain persistence in construction DB.
This script addresses the original error: "no such column: event_data"
"""

import sqlite3
import json

def check_domain_persistence():
    """Check domain persistence in construction DB with corrected column names."""
    
    # Database path
    db_path = 'runs/construction_science_test.sqlite'
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== DOMAIN PERSISTENCE CHECK ===")
        
        # Check distinct domains       
        cursor.execute('SELECT DISTINCT research_domain FROM research_events')
        domains = cursor.fetchall()    
        print('Distinct domains in construction DB:', domains)
        
        # Check recent events - FIXED: Using correct column names instead of event_data
        # The original error was: "no such column: event_data"
        # The actual columns are: outcome, failure_reason, decision_taken, etc.
        cursor.execute('''
            SELECT research_domain, event_type, outcome, failure_reason, decision_taken 
            FROM research_events 
            ORDER BY event_id DESC 
            LIMIT 5
        ''')
        recent_events = cursor.fetchall()
        print('\nRecent events:')
        
        for event in recent_events:    
            print(f'  Domain: {event[0]}, Type: {event[1]}')
            print(f'    Outcome: {event[2]}')
            print(f'    Failure Reason: {event[3]}')
            print(f'    Decision Taken: {event[4]}')
        
        # Additional info about table structure
        print('\n=== TABLE STRUCTURE ===')
        cursor.execute('PRAGMA table_info(research_events)')
        columns = cursor.fetchall()
        print('Available columns in research_events table:')
        for col in columns:
            pk_marker = " (PRIMARY KEY)" if col[5] == 1 else ""
            print(f'  {col[1]} ({col[2]}){pk_marker}')
        
        conn.close()
        print('\n✓ Query executed successfully!')
        
    except sqlite3.Error as e:
        print(f'❌ Database error: {e}')
        return False
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    
    return True

if __name__ == '__main__':
    success = check_domain_persistence()
    if success:
        print('\n🎉 Domain persistence check completed successfully!')
    else:
        print('\n💥 Domain persistence check failed!')