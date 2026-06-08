from pathlib import Path

from utils.db_utils import connect_with_foreign_keys

def check_biohacking_compounds():
    """Check which compounds were found in the biohacking scrape"""
    
    db_path = Path("output/biohacking_dual_lens.sqlite")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    with connect_with_foreign_keys(db_path) as con:
        cur = con.cursor()
        # Get all compounds found
        results = cur.execute(
            "SELECT DISTINCT entity_name FROM entities WHERE entity_type='compound' ORDER BY entity_name"
        ).fetchall()
        compounds_found = [row[0] for row in results]
        compounds_found_lower = set(c.lower() for c in compounds_found)
        # Longevity compounds we added
        longevity_compounds = [
            'nad+', 'nmn', 'nr', 'resveratrol', 'spermidine', 'fisetin', 
            'quercetin', 'curcumin', 'berberine', 'alpha-ketoglutarate', 
            'ca-akg', 'urolithin a', 'apigenin', 'luteolin', 'pterostilbene',
            'sulforaphane', 'egcg', 'astaxanthin', 'coq10', 'pqq'
        ]

        print("\n" + "="*70)
        print("BIOHACKING SCRAPE - COMPOUND DETECTION RESULTS")
        print("="*70)

        print(f"\n📊 TOTAL COMPOUNDS FOUND: {len(compounds_found)}")

        # Check which longevity compounds were found
        found_longevity = [c for c in longevity_compounds if c in compounds_found_lower]
        missing_longevity = [c for c in longevity_compounds if c not in compounds_found_lower]

        print("\n" + "="*70)
        print("LONGEVITY COMPOUND DETECTION")
        print("="*70)

        print(f"\n✅ FOUND ({len(found_longevity)}/{len(longevity_compounds)} longevity compounds):")
        if found_longevity:
            for compound in found_longevity:
                print(f"   ✓ {compound}")
        else:
            print("   (none)")

        print(f"\n❌ NOT FOUND ({len(missing_longevity)}/{len(longevity_compounds)}):")
        if missing_longevity:
            for compound in missing_longevity:
                print(f"   ✗ {compound}")
        else:
            print("   (none)")
        print("\nAll Compounds Detected:")
        for i, compound in enumerate(compounds_found, 1):
            marker = "🎯" if compound.lower() in longevity_compounds else "  "
            print(f"  {marker} {i:2d}. {compound}")

        # Get compound mention counts
        print("\n" + "="*70)
        print("COMPOUND MENTION FREQUENCY")
        print("="*70)

        mention_counts = cur.execute("""
            SELECT e.entity_name, COUNT(ee.event_id) as mentions
            FROM entities e
            LEFT JOIN event_entities ee ON e.entity_id = ee.entity_id
            WHERE e.entity_type = 'compound'
            GROUP BY e.entity_name
            ORDER BY mentions DESC
        """).fetchall()

        print("\nTop compounds by mentions:")
        for i, (compound, count) in enumerate(mention_counts[:10], 1):
            marker = "🎯" if compound.lower() in longevity_compounds else "  "
            print(f"  {marker} {i:2d}. {compound:20s} - {count:3d} mentions")

        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"✅ Total compounds detected: {len(compounds_found)}")
        total_longevity = len(longevity_compounds)
        print(f"🎯 Longevity compounds found: {len(found_longevity)}/{total_longevity} ({len(found_longevity)/total_longevity*100:.1f}%)")
        print(f"📈 Detection rate: {len(found_longevity)}/{total_longevity} longevity compounds")
if __name__ == "__main__":
    check_biohacking_compounds()
