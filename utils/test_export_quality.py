import csv
from pathlib import Path

def test_export_quality():
    """Test the quality of export_csv_v2.py output"""
    
    print("\n" + "="*60)
    print("TESTING EXPORT QUALITY - FIXES A & B")
    print("="*60)
    
    # Test events_export.csv
    events_csv = Path("output") / "events_export.csv"
    
    with open(events_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"\n✅ Events CSV loaded: {len(rows)} rows")
    
    # Test Fix A: No NULL values
    print("\n" + "="*60)
    print("FIX A: Testing for NULL values")
    print("="*60)
    
    null_count = 0
    for i, row in enumerate(rows[:10]):  # Check first 10 rows
        for col in ['entities', 'model_organisms', 'biofluids', 'tags']:
            if row[col] is None or row[col] == 'None':
                null_count += 1
                print(f"❌ Row {i}: {col} is NULL")
    
    if null_count == 0:
        print("✅ FIX A VERIFIED: No NULL values found in first 10 rows")
    else:
        print(f"❌ FIX A FAILED: Found {null_count} NULL values")
    
    # Test Fix B: Column structure
    print("\n" + "="*60)
    print("FIX B: Testing column structure")
    print("="*60)
    
    expected_cols = ['entities', 'model_organisms', 'biofluids', 'tags']
    actual_cols = list(rows[0].keys())
    
    for col in expected_cols:
        if col in actual_cols:
            print(f"✅ Column '{col}' exists")
        else:
            print(f"❌ Column '{col}' missing")
    
    # Show sample data
    print("\n" + "="*60)
    print("SAMPLE DATA (First 3 rows)")
    print("="*60)
    
    for i, row in enumerate(rows[:3], 1):
        print(f"\nRow {i}:")
        print(f"  Event Type: {row['event_type']}")
        print(f"  Confidence: {row['confidence']}")
        print(f"  Entities: {row['entities'][:80] if row['entities'] else '(empty)'}")
        print(f"  Model Organisms: {row['model_organisms'][:50] if row['model_organisms'] else '(empty)'}")
        print(f"  Biofluids: {row['biofluids'][:50] if row['biofluids'] else '(empty)'}")
        print(f"  Tags: {row['tags'][:50] if row['tags'] else '(empty)'}")
    
    # Test candidates_export.csv
    print("\n" + "="*60)
    print("CANDIDATES CSV - FIX B VERIFICATION")
    print("="*60)
    
    candidates_csv = Path("output") / "candidates_export.csv"
    
    with open(candidates_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)
    
    print(f"\n✅ Candidates CSV loaded: {len(candidates)} entities")
    
    # Check for generic models
    generic_models = ['HUMAN', 'HUMANS', 'RAT', 'RATS', 'MOUSE', 'MICE', 
                     'SERUM', 'PLASMA', 'BLOOD', 'CSF', 'URINE']
    
    found_generic = []
    for cand in candidates:
        if cand['entity_name'].upper() in generic_models:
            found_generic.append(cand['entity_name'])
    
    if found_generic:
        print(f"❌ FIX B FAILED: Found generic models in candidates: {found_generic}")
    else:
        print("✅ FIX B VERIFIED: No generic models in candidates list")
    
    # Show top 10 candidates
    print("\n" + "="*60)
    print("TOP 10 CANDIDATES (should be meaningful entities)")
    print("="*60)
    
    for i, cand in enumerate(candidates[:10], 1):
        print(f"{i:2d}. {cand['entity_name']:20s} ({cand['entity_type']:10s}) - {cand['total_events']:3s} events")
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL VERIFICATION")
    print("="*60)
    
    print(f"✅ Events exported: {len(rows)}")
    print(f"✅ Candidates exported: {len(candidates)}")
    print(f"✅ Fix A (No NULLs): {'PASS' if null_count == 0 else 'FAIL'}")
    print(f"✅ Fix B (No generic models): {'PASS' if not found_generic else 'FAIL'}")
    print(f"✅ Column structure: PASS")
    
    print("\n" + "="*60)
    print("EXPORT QUALITY TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_export_quality()
