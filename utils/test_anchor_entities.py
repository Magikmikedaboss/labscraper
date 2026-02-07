"""
Comprehensive test of anchor entity extraction functionality
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("output") / "peptide_intel.sqlite"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_entity_counts():
    """Test 1: Verify entity counts by type"""
    print_section("TEST 1: Entity Counts by Type")
    
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT entity_type, COUNT(*) as count
            FROM entities
            GROUP BY entity_type
            ORDER BY count DESC
        """)
        results = cur.fetchall()
        total = sum(r[1] for r in results)
        print(f"\nTotal entities: {total}")
        print("\nBreakdown:")
        for entity_type, count in results:
            print(f"  ✓ {entity_type:12} {count:3} entities")
        # Assertions
        assert total >= 16, f"Expected at least 16 entities, got {total}"
        assert any(t == 'compound' for t, _ in results), "No compounds found!"
        assert any(t == 'model' for t, _ in results), "No models found!"
        print("\n✅ PASSED: Entity counts verified")

def test_compound_extraction():
    """Test 2: Verify compound extraction"""
    print_section("TEST 2: Compound Extraction")
    
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT entity_name, entity_variant, COUNT(ee.event_id) as events
            FROM entities e
            LEFT JOIN event_entities ee ON e.entity_id = ee.entity_id
            WHERE e.entity_type = 'compound'
            GROUP BY e.entity_id
            ORDER BY events DESC
        """)
        compounds = cur.fetchall()
        print(f"\nFound {len(compounds)} compounds:")
        for name, variant, events in compounds:
            print(f"  ✓ {name:20} ({variant:10}) {events:3} events")
        # Assertions
        assert len(compounds) >= 5, f"Expected at least 5 compounds, got {len(compounds)}"
        compound_names = [c[0] for c in compounds]
        assert 'LIRAGLUTIDE' in compound_names, "LIRAGLUTIDE not found!"
        assert 'SEMAGLUTIDE' in compound_names, "SEMAGLUTIDE not found!"
        print("\n✅ PASSED: Compounds extracted correctly")

def test_model_extraction():
    """Test 3: Verify model extraction"""
    print_section("TEST 3: Model Extraction")
    
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT entity_name, entity_variant, COUNT(ee.event_id) as events
            FROM entities e
            LEFT JOIN event_entities ee ON e.entity_id = ee.entity_id
            WHERE e.entity_type = 'model'
            GROUP BY e.entity_id
            ORDER BY events DESC
        """)
        models = cur.fetchall()
        print(f"\nFound {len(models)} models:")
        for name, variant, events in models:
            print(f"  ✓ {name:20} ({variant:10}) {events:3} events")
        # Assertions
        assert len(models) >= 4, f"Expected at least 4 models, got {len(models)}"
        model_names = [m[0] for m in models]
        assert 'Serum' in model_names or 'SERUM' in model_names, "Serum not found!"
        assert 'Human' in model_names or 'HUMAN' in model_names, "Human not found!"
        print("\n✅ PASSED: Models extracted correctly")

def test_multi_entity_events():
    """Test 4: Verify multi-entity event linkage"""
    print_section("TEST 4: Multi-Entity Event Linkage")
    
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT e.event_id, e.evidence_snippet, COUNT(DISTINCT ee.entity_id) as entity_count
            FROM research_events e
            JOIN event_entities ee ON e.event_id = ee.event_id
            GROUP BY e.event_id
            HAVING entity_count > 1
            ORDER BY entity_count DESC
            LIMIT 3
        """)
        multi_events = cur.fetchall()
        print(f"\nFound {len(multi_events)} events with multiple entities")
        print("\nTop 3 examples:")
        for i, (event_id, snippet, entity_count) in enumerate(multi_events, 1):
            safe_preview = snippet[:80] if snippet is not None else "<no snippet>"
            print(f"\n{i}. Event with {entity_count} entities:")
            print(f"   Snippet: {safe_preview}...")
            # Get entities for this event
            cur.execute("""
                SELECT ent.entity_type, ent.entity_name, ee.role
                FROM event_entities ee
                JOIN entities ent ON ee.entity_id = ent.entity_id
                WHERE ee.event_id = ?
            """, (event_id,))
            entities = cur.fetchall()
            print("   Entities:")
            for entity_type, name, role in entities:
                print(f"     - {entity_type:12} {name:20} [role: {role}]")
        # Assertions
        assert len(multi_events) > 0, "No multi-entity events found!"
        print("\n✅ PASSED: Multi-entity linkage working")

def test_entity_roles():
    """Test 5: Verify entity role assignment"""
    print_section("TEST 5: Entity Role Assignment")
    
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT ee.role, COUNT(*) as count
            FROM event_entities ee
            GROUP BY ee.role
            ORDER BY count DESC
        """)
        roles = cur.fetchall()
        print("\nEntity role distribution:")
        for role, count in roles:
            print(f"  ✓ {role:15} {count:4} linkages")
        # Assertions
        assert len(roles) > 0, "No entity roles found!"
        role_names = [r[0] for r in roles]
        assert 'tested' in role_names or 'model' in role_names, "Expected roles not found!"
        print("\n✅ PASSED: Entity roles assigned correctly")

def test_serum_events():
    """Test 6: Query serum-related events (real-world use case)"""
    print_section("TEST 6: Real-World Query - Serum Events")
    
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT e.event_type, e.failure_reason, e.outcome, e.evidence_snippet
            FROM research_events e
            JOIN event_entities ee ON e.event_id = ee.event_id
            JOIN entities ent ON ee.entity_id = ent.entity_id
            WHERE ent.entity_name IN ('Serum', 'SERUM')
            LIMIT 5
        """)
        serum_events = cur.fetchall()
        print(f"\nFound {len(serum_events)} serum-related events")
        print("\nSample events:")
        for i, (event_type, failure_reason, outcome, snippet) in enumerate(serum_events[:3], 1):
            safe_snippet = (snippet or "")
            print(f"\n{i}. Type: {event_type}")
            print(f"   Failure: {failure_reason}")
            print(f"   Outcome: {outcome}")
            print(f"   Snippet: {safe_snippet[:100]}...")
        # Assertions
        assert len(serum_events) > 0, "No serum events found!"
        print("\n✅ PASSED: Can query serum-related events")

def test_compound_summary():
    """Test 7: Compound event summary (dashboard-ready)"""
    print_section("TEST 7: Compound Event Summary (Dashboard Ready)")
    
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT 
                ent.entity_name as compound,
                COUNT(DISTINCT e.event_id) as total_events,
                COUNT(DISTINCT CASE WHEN e.failure_reason != 'unknown' THEN e.event_id END) as failures,
                COUNT(DISTINCT e.source_id) as num_papers,
                MIN(s.year) as first_year,
                MAX(s.year) as last_year
            FROM entities ent
            JOIN event_entities ee ON ent.entity_id = ee.entity_id
            JOIN research_events e ON ee.event_id = e.event_id
            JOIN sources s ON e.source_id = s.source_id
            WHERE ent.entity_type = 'compound'
            GROUP BY ent.entity_id
            ORDER BY total_events DESC
        """)

        summaries = cur.fetchall()

        print("\nCompound Intelligence Summary:")
        print(f"\n{'Compound':<20} {'Events':<8} {'Failures':<10} {'Papers':<8} {'Years':<12}")
        print("-" * 70)

        for compound, events, failures, papers, first_year, last_year in summaries:
            year_range = f"{first_year or 'N/A'}-{last_year or 'N/A'}"
            print(f"{compound:<20} {events:<8} {failures:<10} {papers:<8} {year_range:<12}")

        # Assertions
        assert len(summaries) > 0, "No compound summaries generated!"
    print("\n✅ PASSED: Dashboard-ready summaries working")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("  ANCHOR ENTITY EXTRACTION - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    tests = [
        test_entity_counts,
        test_compound_extraction,
        test_model_extraction,
        test_multi_entity_events,
        test_entity_roles,
        test_serum_events,
        test_compound_summary,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"  TEST RESULTS: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Anchor entity extraction is working perfectly!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
