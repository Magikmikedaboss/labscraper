import sqlite3
from pathlib import Path

DB_PATH = Path("output") / "peptide_intel.sqlite"


if not DB_PATH.exists():
    raise FileNotFoundError(f"Database file not found: {DB_PATH}")
con = sqlite3.connect(DB_PATH)
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

print("\n" + "="*60)
print("ALL ENTITIES WITH EVENT COUNTS")
print("="*60)

# Show all entities with their event counts
cur.execute("""
    SELECT e.entity_type, e.entity_name, e.entity_variant, COUNT(ee.event_id) as events
    FROM entities e
    LEFT JOIN event_entities ee ON e.entity_id = ee.entity_id
    GROUP BY e.entity_id
    ORDER BY events DESC, e.entity_type, e.entity_name
""")

for row in cur.fetchall():
    entity_type, name, variant, events = row
    variant_str = f" ({variant})" if variant else ""
    print(f"{entity_type:12} {name:30}{variant_str:20} {events:3} events")

print("\n" + "="*60)
print("SAMPLE SENTENCES WITH COMPOUNDS")
print("="*60)

# Check if any sentences contain compound names
compounds = ["metformin", "rapamycin", "serum", "mouse", "mtor", "ampk"]
for compound in compounds:
    cur.execute("""
        SELECT evidence_snippet
        FROM research_events
        WHERE LOWER(evidence_snippet) LIKE ?
        LIMIT 1
    """, (f'%{compound}%',))
    
    result = cur.fetchone()
    if result:
        snippet = result[0]
        if len(snippet) > 150:
            print(f"\nFound '{compound}':")
            print(f"  {snippet[:150]}...")
        else:
            print(f"\nFound '{compound}':")
            print(f"  {snippet}")
    else:
        print(f"\nNo '{compound}' found")

con.close()
