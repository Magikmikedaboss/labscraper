import sqlite3
from pathlib import Path

DB_PATH = Path("output") / "peptide_intel.sqlite"

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

print("\n" + "="*60)
print("EVENT-ENTITY LINKAGE QUALITY TEST")
print("="*60)

# 1. Check for duplicate entities (same name, different types)
print("\n1. Checking for duplicate entity names...")
print("-" * 60)

cur.execute("""
    SELECT entity_name, GROUP_CONCAT(entity_type || ' (' || COALESCE(entity_variant, 'none') || ')', ', ') as types, COUNT(*) as count
    FROM entities
    GROUP BY LOWER(entity_name)
    HAVING COUNT(*) > 1
""")

duplicates = cur.fetchall()
if duplicates:
    for name, types, count in duplicates:
        print(f"  ⚠️  '{name}' appears {count} times as: {types}")
else:
    print("  ✓ No duplicate entity names found")

# 2. Check multi-entity events
print("\n2. Checking events with multiple entities...")
print("-" * 60)

cur.execute("""
    SELECT e.event_id, e.evidence_snippet, COUNT(DISTINCT ee.entity_id) as entity_count
    FROM research_events e
    JOIN event_entities ee ON e.event_id = ee.event_id
    GROUP BY e.event_id
    HAVING entity_count > 1
    ORDER BY entity_count DESC
    LIMIT 5
""")

multi_entity_events = cur.fetchall()
if multi_entity_events:
    print(f"  Found {len(multi_entity_events)} events with multiple entities\n")
    
    for event_id, snippet, entity_count in multi_entity_events[:3]:
        print(f"  Event with {entity_count} entities:")
        safe_snippet = (snippet or "")[:100]
        print(f"    Snippet: {safe_snippet}...")
        
        # Show which entities
        cur.execute("""
            SELECT ent.entity_type, ent.entity_name, ent.entity_variant, ee.role
            FROM event_entities ee
            JOIN entities ent ON ee.entity_id = ent.entity_id
            WHERE ee.event_id = ?
        """, (event_id,))
        
        for entity_type, name, variant, role in cur.fetchall():
            variant_str = f" ({variant})" if variant else ""
            print(f"      - {entity_type}: {name}{variant_str} [role: {role}]")
        print()
else:
    print("  ℹ️  No events with multiple entities found")

# 3. Check entity role distribution
print("\n3. Checking entity role distribution...")
print("-" * 60)

cur.execute("""
    SELECT ee.role, COUNT(*) as count
    FROM event_entities ee
    GROUP BY ee.role
    ORDER BY count DESC
""")

for role, count in cur.fetchall():
    print(f"  {role:15} {count:4} linkages")

# 4. Check if compound events link to models
print("\n4. Checking if compound events also link to models...")
print("-" * 60)

cur.execute("""
    SELECT DISTINCT e.event_id, e.evidence_snippet
    FROM research_events e
    JOIN event_entities ee1 ON e.event_id = ee1.event_id
    JOIN entities ent1 ON ee1.entity_id = ent1.entity_id
    JOIN event_entities ee2 ON e.event_id = ee2.event_id
    JOIN entities ent2 ON ee2.entity_id = ent2.entity_id
    WHERE ent1.entity_type = 'compound'
      AND ent2.entity_type = 'model'
    LIMIT 3
""")

compound_model_events = cur.fetchall()
if compound_model_events:
    print(f"  ✓ Found {len(compound_model_events)} events linking compounds to models\n")
    
    for event_id, snippet in compound_model_events:
        safe_snippet = (snippet or "")[:100]
        print(f"  Example: {safe_snippet}...")
        
        # Show entities
        cur.execute("""
            SELECT ent.entity_type, ent.entity_name
            FROM event_entities ee
            JOIN entities ent ON ee.entity_id = ent.entity_id
            WHERE ee.event_id = ?
        """, (event_id,))
        
        entities = cur.fetchall()
        print(f"    Entities: {', '.join([f'{t}:{n}' for t, n in entities])}")
        print()
else:
    print("  ℹ️  No events linking compounds to models")

# 5. Check entity_variant population
print("\n5. Checking entity_variant field population...")
print("-" * 60)

cur.execute("""
    SELECT entity_type, 
           SUM(CASE WHEN entity_variant IS NOT NULL THEN 1 ELSE 0 END) as with_variant,
           COUNT(*) as total
    FROM entities
    GROUP BY entity_type
""")

for entity_type, with_variant, total in cur.fetchall():
    pct = (with_variant / total * 100) if total > 0 else 0
    print(f"  {entity_type:12} {with_variant}/{total} ({pct:.0f}%) have variant")

con.close()
