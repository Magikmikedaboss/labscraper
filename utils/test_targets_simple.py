import sqlite3

con = sqlite3.connect("output/peptide_intel.sqlite")
cursor = con.cursor()

# Check all entities
print("=" * 60)
print("ALL ENTITIES BY TYPE")
print("=" * 60)
cursor.execute("""
    SELECT entity_type, entity_name, COUNT(*) as event_count
    FROM entities e
    LEFT JOIN event_entities ee ON e.entity_id = ee.entity_id
    GROUP BY entity_type, entity_name
    ORDER BY entity_type, event_count DESC
""")

current_type = None
for row in cursor.fetchall():
    entity_type, entity_name, count = row
    if entity_type != current_type:
        print(f"\n{entity_type.upper()}:")
        current_type = entity_type
    print(f"  {entity_name}: {count} events")

# Check if any targets exist
print("\n" + "=" * 60)
print("TARGET CHECK")
print("=" * 60)
cursor.execute("SELECT COUNT(*) FROM entities WHERE entity_type = 'target'")
target_count = cursor.fetchone()[0]
print(f"Total targets in database: {target_count}")

if target_count == 0:
    print("\n❌ NO TARGETS FOUND!")
    print("\nLet's check if target extraction is working...")
    
    # Test the extraction function
    from scrape_pdfs import extract_targets
    
    test_sentences = [
        "The compound inhibited MTOR signaling.",
        "AMPK activation was observed.",
        "GLP-1R agonist showed efficacy.",
        "The peptide binds to mTOR.",
        "AKT phosphorylation increased.",
    ]
    
    print("\nTesting extract_targets() function:")
    for sent in test_sentences:
        targets = extract_targets(sent)
        if targets:
            print(f"  ✓ '{sent[:50]}...' → {[t['entity_name'] for t in targets]}")
        else:
            print(f"  ✗ '{sent[:50]}...' → No targets")

con.close()
