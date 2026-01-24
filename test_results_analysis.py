import sqlite3
from pathlib import Path

def analyze_test_results():
    """Analyze the enhanced seeds test scrape results"""
    
    db_path = Path("output/test_enhanced_seeds.sqlite")
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    print("\n" + "="*70)
    print("ENHANCED SEEDS TEST RESULTS - 25 PDFs")
    print("="*70)
    
    # Overall stats
    cur.execute("SELECT COUNT(*) FROM research_events")
    total_events = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT entity_id) FROM entities")
    total_entities = cur.fetchone()[0]
    
    print(f"\n📊 OVERALL EXTRACTION:")
    print(f"   Events: {total_events}")
    print(f"   Unique Entities: {total_entities}")
    
    # Entity type breakdown
    print(f"\n🏷️  ENTITY TYPE DISTRIBUTION:")
    cur.execute("""
        SELECT entity_type, 
               COUNT(DISTINCT entity_name) as unique_count,
               COUNT(*) as total_mentions
        FROM entities 
        GROUP BY entity_type 
        ORDER BY total_mentions DESC
    """)
    
    for row in cur.fetchall():
        entity_type, unique, mentions = row
        print(f"   {entity_type:12s}: {unique:3d} unique entities | {mentions:4d} total mentions")
    
    # Top models (showing new additions working)
    print(f"\n🔬 TOP MODELS EXTRACTED (from 160 in enhanced seeds):")
    cur.execute("""
        SELECT DISTINCT e.entity_name
        FROM entities e
        WHERE e.entity_type = 'model'
        ORDER BY e.entity_name
        LIMIT 30
    """)
    models = [row[0] for row in cur.fetchall()]
    
    # Check for new neuroscience models
    new_neuro_models = ['MICROGLIA', 'ASTROCYTES', 'CORTICAL NEURONS', 'HIPPOCAMPAL NEURONS', 
                        'PRIMARY NEURONS', 'OLIGODENDROCYTES', 'BRAIN SLICE', 'IPSC-DERIVED NEURONS']
    found_new = [m for m in models if m.upper() in new_neuro_models]
    
    print(f"   Total models found: {len(models)}")
    if found_new:
        print(f"   ✅ NEW neuroscience models detected: {', '.join(found_new[:5])}")
    
    for i, model in enumerate(models[:15], 1):
        marker = "🆕" if model.upper() in new_neuro_models else "  "
        print(f"   {marker} {i:2d}. {model}")
    
    # Top targets
    print(f"\n🎯 TOP TARGETS EXTRACTED (from 177 in enhanced seeds):")
    cur.execute("""
        SELECT DISTINCT e.entity_name
        FROM entities e
        WHERE e.entity_type = 'target'
        ORDER BY e.entity_name
        LIMIT 30
    """)
    targets = [row[0] for row in cur.fetchall()]
    
    # Check for new targets
    new_targets = ['BDNF', 'NTRK2', 'GRIN2B', 'MAPT', 'APP', 'SNCA', 'TERT', 'TERC', 
                   'WRN', 'LMNA', 'FASN', 'ACC', 'CPT1', 'PDK1', 'HK2', 'IFNG', 
                   'IL10', 'TLR4', 'TLR9', 'NLRP3']
    found_new_targets = [t for t in targets if t.upper() in new_targets]
    
    print(f"   Total targets found: {len(targets)}")
    if found_new_targets:
        print(f"   ✅ NEW targets detected: {', '.join(found_new_targets[:5])}")
    
    for i, target in enumerate(targets[:15], 1):
        marker = "🆕" if target.upper() in new_targets else "  "
        print(f"   {marker} {i:2d}. {target}")
    
    # Stem cells
    print(f"\n🧬 STEM CELL ENTITIES:")
    cur.execute("""
        SELECT DISTINCT entity_name
        FROM entities
        WHERE entity_type = 'stem_cell'
        ORDER BY entity_name
    """)
    for row in cur.fetchall():
        print(f"   - {row[0]}")
    
    # Event types
    print(f"\n📋 EVENT TYPE DISTRIBUTION:")
    cur.execute("""
        SELECT event_type, COUNT(*) as count
        FROM research_events
        GROUP BY event_type
        ORDER BY count DESC
        LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"   {row[0]:30s}: {row[1]:4d}")
    
    # Confidence distribution
    print(f"\n📊 CONFIDENCE DISTRIBUTION:")
    cur.execute("""
        SELECT confidence, COUNT(*) as count
        FROM research_events
        GROUP BY confidence
        ORDER BY 
            CASE confidence 
                WHEN 'high' THEN 1 
                WHEN 'med' THEN 2 
                WHEN 'low' THEN 3 
            END
    """)
    for row in cur.fetchall():
        conf, count = row
        pct = (count / total_events * 100) if total_events > 0 else 0
        print(f"   {conf:4s}: {count:4d} ({pct:5.1f}%)")
    
    print("\n" + "="*70)
    print("ENHANCEMENT IMPACT SUMMARY")
    print("="*70)
    print(f"✅ Base seeds loaded: 177 targets, 160 models, 39 compounds")
    print(f"✅ Entities extracted: {total_entities} unique entities")
    print(f"✅ Events captured: {total_events} research events")
    
    if found_new:
        print(f"✅ NEW neuroscience models working: {len(found_new)} detected")
    if found_new_targets:
        print(f"✅ NEW targets working: {len(found_new_targets)} detected")
    
    print(f"\n💡 Next steps:")
    print(f"   1. Compare with old seed results to quantify improvement")
    print(f"   2. Use domain-aware export to separate by research area")
    print(f"   3. Full re-scrape of all ~220 PDFs with enhanced seeds")
    
    con.close()

if __name__ == "__main__":
    analyze_test_results()
