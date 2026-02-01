import sqlite3

def check_entities():
    # Use context manager for database connection
    with sqlite3.connect('output/test_construction_parallel.sqlite') as con:
        cur = con.cursor()
        
        # Check all entity types
        cur.execute('SELECT DISTINCT entity_type FROM entities ORDER BY entity_type')
        entity_types = [row[0] for row in cur.fetchall()]
        print("Entity types found:")
        for etype in entity_types:
            print(f"  - {etype}")
        
        print("\nDomain-specific entities (pathway, indication):")
        cur.execute('SELECT DISTINCT entity_type, entity_name FROM entities WHERE entity_type IN ("pathway", "indication") ORDER BY entity_type, entity_name')
        results = cur.fetchall()
        for etype, ename in results:
            print(f"  {etype}: {ename}")
        
        # Check total entities
        cur.execute('SELECT COUNT(*) FROM entities')
        total_entities = cur.fetchone()[0]
        print(f"\nTotal entities: {total_entities}")
        
        # Check events
        cur.execute('SELECT COUNT(*) FROM research_events')
        total_events = cur.fetchone()[0]
        print(f"Total events: {total_events}")

if __name__ == "__main__":
    check_entities()
