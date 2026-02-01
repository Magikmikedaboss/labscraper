import sqlite3
from pathlib import Path

DB_PATH = Path("output") / "peptide_intel.sqlite"

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()

        print("\n" + "="*60)
        print("ENTITY BREAKDOWN BY TYPE")
        print("="*60)

        # Count by entity type
        cur.execute("""
            SELECT entity_type, COUNT(DISTINCT entity_id) as count
            FROM entities
            GROUP BY entity_type
            ORDER BY count DESC
        """)

        for row in cur.fetchall():
            print(f"{row[0]:15} {row[1]:5} entities")

        # Count by entity name
        cur.execute("""
            SELECT entity_name, entity_type, COUNT(DISTINCT entity_id) as count
            FROM entities
            GROUP BY entity_name, entity_type
            ORDER BY count DESC
            LIMIT 20
        """)

        print("\n" + "="*60)
        print("TOP 20 ENTITIES BY NAME")
        print("="*60)

        for row in cur.fetchall():
            print(f"{row[0]:30} ({row[1]:15}) {row[2]:3} entities")

        # Count by event type
        cur.execute("""
            SELECT event_type, COUNT(DISTINCT event_id) as count
            FROM research_events
            GROUP BY event_type
            ORDER BY count DESC
        """)

        print("\n" + "="*60)
        print("EVENT BREAKDOWN BY TYPE")
        print("="*60)

        for row in cur.fetchall():
            print(f"{row[0]:15} {row[1]:5} events")

        # Count by confidence
        cur.execute("""
            SELECT confidence, COUNT(DISTINCT event_id) as count
            FROM research_events
            GROUP BY confidence
            ORDER BY 
                CASE confidence 
                    WHEN 'high' THEN 1 
                    WHEN 'med' THEN 2 
                    WHEN 'low' THEN 3 
                    ELSE 4
                END
        """)
        print("\n" + "="*60)
        print("EVENT BREAKDOWN BY CONFIDENCE")
        print("="*60)

        for row in cur.fetchall():
            print(f"{row[0]:15} {row[1]:5} events")

        # Count entities per event
        cur.execute("""
            SELECT entity_count, COUNT(*) as event_count
            FROM (
                SELECT event_id, COUNT(*) as entity_count
                FROM event_entities
                GROUP BY event_id
            ) AS t
            GROUP BY entity_count
            ORDER BY entity_count DESC
            LIMIT 10
        """)

        print("\n" + "="*60)
        print("ENTITIES PER EVENT (TOP 10)")
        print("="*60)

        for row in cur.fetchall():
            print(f"{row[0]:3} entities in {row[1]:3} events")

if __name__ == "__main__":
    main()