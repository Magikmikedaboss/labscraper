#!/usr/bin/env python3
"""
Final system verification script
"""

import sys

print('🧪 FINAL SYSTEM VERIFICATION')
print('=' * 50)

all_ok = True

# Test 1: Import functionality
print('1. Testing imports...')
try:
    from utils.integrated_entity_system import IntegratedEntitySystem
    from utils.scrape_pdfs_phase1_full import chunk_sentences
    from utils.overlay_scorer import OverlayScorer
    print('✅ All imports successful')
except Exception as e:
    print(f'❌ Import error: {e}')
    all_ok = False

# Test 2: Entity extraction
print('2. Testing entity extraction...')
try:
    system = IntegratedEntitySystem(domain='construction_science')
    test_text = 'The high-strength concrete beam experienced cracking after exposure to marine environments.'
    entities = system.extract_entities(test_text, 'Test Title')
    print(f'✅ Entity extraction: {len(entities)} entities found')
    for entity in entities[:2]:
        print(f'   - {entity["entity_type"]}: {entity["entity_name"]}')
except Exception as e:
    print(f'❌ Entity extraction error: {e}')
    all_ok = False

# Test 3: Database functionality
print('3. Testing database functionality...')
try:
    import sqlite3
    db_path = 'db/construction_science_parallel.sqlite'
    with sqlite3.connect(db_path) as con:
        stats = con.execute('SELECT COUNT(*) FROM research_events').fetchone()[0]
        print(f'✅ Database access: {stats} events in database')
except Exception as e:
    print(f'❌ Database error: {e}')
    all_ok = False

# Test 4: Overlay scoring
print('4. Testing overlay scoring...')
try:
    from utils.overlay_scorer import load_domain_config
    domain_config = load_domain_config('construction_science')
    scorer = OverlayScorer(domain_config)
    test_event = {'evidence_snippet': 'The concrete beam showed significant cracking.'}
    scores = scorer.apply_event_scores(test_event)
    print(f'✅ Overlay scoring: {len(scores)} overlays scored')
    for overlay_id, score in list(scores.items())[:2]:
        print(f'   - {overlay_id}: {score:+.1f}')
except Exception as e:
    print(f'❌ Overlay scoring error: {e}')
    all_ok = False

# Test 5: PDF processing functions
print('5. Testing PDF processing functions...')
try:
    test_text = 'The beam showed 50% reduction in strength after 10 years.'
    sentences = chunk_sentences(test_text)
    print(f'✅ PDF processing: {len(sentences)} sentences found')
except Exception as e:
    print(f'❌ PDF processing error: {e}')
    all_ok = False

if all_ok:
    print('\n🎉 ALL SYSTEMS ARE FIRING CORRECTLY!')
    print('✅ Imports: All modules load successfully')
    print('✅ Entity extraction: Working properly')
    print('✅ Database: Accessible and functional')
    print('✅ Overlay scoring: Processing correctly')
    print('✅ PDF processing: Functions operational')
else:
    print('\n❌ SOME SYSTEMS FAILED VERIFICATION')
    print('Please check the error messages above and resolve any issues.')
    sys.exit(1)
