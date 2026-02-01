import sqlite3
import json
from pathlib import Path

print("=" * 70)
print("NEURAL CELL EXTRACTION - VERIFICATION RESULTS")
print("=" * 70)

db_path = Path('output/peptide_intel.sqlite')
if not db_path.exists():
    print(f"\u274c Database not found: {db_path}")
    exit(1)

with sqlite3.connect(str(db_path)) as con:
    # Check entity types
    print("\n1. Entity Types Distribution:")
    print("-" * 70)
    cur = con.execute('''
        SELECT entity_type, COUNT(*) as cnt
        FROM entities
        GROUP BY entity_type
        ORDER BY cnt DESC
    ''')
    for row in cur:
        marker = "\u2705" if row[0] == "neural_cell" else "  "
        print(f"   {marker} {row[0]}: {row[1]} unique entities")

    # Check neural cells specifically
    print("\n2. Neural Cell Entities Found:")
    print("-" * 70)
    cur = con.execute('''
        SELECT entity_name
        FROM entities
        WHERE entity_type = "neural_cell"
        ORDER BY entity_name
    ''')
    neural_cells = [row[0] for row in cur]
    if neural_cells:
        for cell in neural_cells:
            print(f"   ✅ {cell}")
    else:
        print("   ❌ No neural cells found")

    # Check event counts for neural cells
    print("\n3. Neural Cell Event Counts:")
    print("-" * 70)
    cur = con.execute('''
        SELECT e.entity_name, COUNT(DISTINCT ee.event_id) as event_count
        FROM entities e
        JOIN event_entities ee ON e.entity_id = ee.entity_id
        WHERE e.entity_type = "neural_cell"
        GROUP BY e.entity_name
        ORDER BY event_count DESC
    ''')
    results = cur.fetchall()
    if results:
        for row in results:
            print(f"   {row[0]}: {row[1]} events")
    else:
        print("   ❌ No events linked to neural cells")

    # Compare with model type (old way)
    print("\n4. Comparison - Model Type Entities:")
    print("-" * 70)
    cur = con.execute('''
        SELECT e.entity_name, COUNT(DISTINCT ee.event_id) as event_count
        FROM entities e
        JOIN event_entities ee ON e.entity_id = ee.entity_id
        WHERE e.entity_type = "model"
        AND (e.entity_name LIKE '%neuron%' OR e.entity_name LIKE '%microglia%' OR e.entity_name LIKE '%astrocyte%')
        GROUP BY e.entity_name
        ORDER BY event_count DESC
    ''')
    model_results = cur.fetchall()
    if model_results:
        print("   ⚠️  Found neural terms still typed as 'model':")
        for row in model_results:
            print(f"      {row[0]}: {row[1]} events")
    else:
        print("   ✅ No neural terms found as 'model' type (good!)")

    # Check stem cell comparison
    print("\n5. Stem Cell Entities (for comparison):")
    print("-" * 70)
    cur = con.execute('''
        SELECT e.entity_name, COUNT(DISTINCT ee.event_id) as event_count
        FROM entities e
        JOIN event_entities ee ON e.entity_id = ee.entity_id
        WHERE e.entity_type = "stem_cell"
        GROUP BY e.entity_name
        ORDER BY event_count DESC
        LIMIT 5
    ''')
    for row in cur:
        print(f"   {row[0]}: {row[1]} events")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
