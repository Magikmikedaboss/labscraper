#!/usr/bin/env python3
import sqlite3
import json

def test_query():
    # Check domain persistence in construction DB
    db_path = 'runs/construction_science_test.sqlite'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check distinct domains       
    cursor.execute('SELECT DISTINCT research_domain FROM research_events')
    domains = cursor.fetchall()    
    print('Distinct domains in construction DB:', domains)

    # Check recent events - using event_id for ordering
    cursor.execute('SELECT research_domain, event_type, outcome, failure_reason, decision_taken FROM research_events ORDER BY event_id DESC LIMIT 5')
    recent_events = cursor.fetchall()
    print('Recent events:')        
    for event in recent_events:    
        print(f'  Domain: {event[0]}, Type: {event[1]}')
        print(f'    Outcome: {event[2]}')
        print(f'    Failure Reason: {event[3]}')
        print(f'    Decision Taken: {event[4]}')

    conn.close()

if __name__ == '__main__':
    test_query()