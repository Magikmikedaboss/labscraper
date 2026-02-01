import csv
from pathlib import Path

def test_export_quality():
    """Test the quality of domain-aware export CSV outputs"""
    
    print("\n" + "="*60)
    print("TESTING EXPORT QUALITY - FIXES A & B")
    
    # Test events_export.csv
    events_csv = Path("output") / "events_export.csv"
    
    if not events_csv.exists():
        print(f"❌ Events CSV not found: {events_csv}")
        return
    
    with open(events_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)    
    
    if not rows:
        print("❌ Events CSV is empty (no data rows)")
        return
    
    print(f"\n✅ Events CSV loaded: {len(rows)} rows")
    
    # Test Fix A: No NULL values
    print("\n" + "="*60)
    print("FIX A: Testing for NULL values")
    print("="*60)
    
    null_count = 0
    check_cols = ['entities', 'model_organisms', 'biofluids', 'tags']
    
    for i, row in enumerate(rows[:10]):  # Check first 10 rows
        for col in check_cols:
            val = row.get(col)
            if val is None or val == 'None':
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
    
    column_ok = True
    for col in expected_cols:
        if col in actual_cols:
            print(f"✅ Column '{col}' exists")
        else:
            print(f"❌ Column '{col}' missing")
            column_ok = False

    if column_ok:
        print("✅ Column structure: PASS")
    else:
        print("❌ Column structure: FAIL — One or more expected columns are missing.")

    # Show sample data
    print("\n" + "="*60)
    print("SAMPLE DATA (First 3 rows)")
    print("="*60)
    
    for i, row in enumerate(rows[:3], 1):
        print(f"\nRow {i}:")
        print(f"  Event Type: {row.get('event_type', '(missing)')}")
        print(f"  Confidence: {row.get('confidence', '(missing)')}")
        print(f"  Entities: {(row.get('entities') or '')[:80] or '(empty)'}")
        print(f"  Model Organisms: {(row.get('model_organisms') or '')[:50] or '(empty)'}")
        print(f"  Biofluids: {(row.get('biofluids') or '')[:50] or '(empty)'}")
        print(f"  Tags: {(row.get('tags') or '')[:50] or '(empty)'}")
    
    # Test candidates_export.csv
    print("\n" + "="*60)
    print("CANDIDATES CSV - FIX B VERIFICATION")
    print("="*60)
    
    candidates_csv = Path("output") / "candidates_export.csv"
    
    if not candidates_csv.exists():
        print(f"❌ Candidates CSV not found: {candidates_csv}")
        return
    
    with open(candidates_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    if not candidates:
        print("❌ Candidates CSV is empty (no data rows)")
        return
    
    print(f"\n✅ Candidates CSV loaded: {len(candidates)} entities")    
    
    # Check for generic models
    generic_models = ['HUMAN', 'HUMANS', 'RAT', 'RATS', 'MOUSE', 'MICE', 
                     'SERUM', 'PLASMA', 'BLOOD', 'CSF', 'URINE']
    
    found_generic = []
    for cand in candidates:
        entity_name = cand.get('entity_name', '')
        if entity_name.upper() in generic_models:
            found_generic.append(entity_name)    
    
    if found_generic:
        print(f"❌ FIX B FAILED: Found generic models in candidates: {found_generic}")
    else:
        print("✅ FIX B VERIFIED: No generic models in candidates list")
    
    # Show top 10 candidates
    print("\n" + "="*60)
    print("TOP 10 CANDIDATES (should be meaningful entities)")
    print("="*60)
    
    for i, cand in enumerate(candidates[:10], 1):
        name = cand.get('entity_name', 'N/A')
        etype = cand.get('entity_type', 'N/A')
        events = cand.get('total_events', '0')
        print(f"{i:2d}. {name:20s} ({etype:10s}) - {events:3s} events")
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL VERIFICATION")
    print("="*60)
    
    print(f"✅ Events exported: {len(rows)}")
    print(f"{'✅' if null_count == 0 else '❌'} Fix A (No NULLs): {'PASS' if null_count == 0 else 'FAIL'}")
    print(f"{'✅' if not found_generic else '❌'} Fix B (No generic models): {'PASS' if not found_generic else 'FAIL'}")
    print(f"{'✅' if column_ok else '❌'} Column structure: {'PASS' if column_ok else 'FAIL'}")
    
    print("\n" + "="*60)
    print("EXPORT QUALITY TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_export_quality()
