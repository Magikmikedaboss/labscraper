import sqlite3
from pathlib import Path

DB_PATH = Path("output") / "peptide_intel.sqlite"

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

print("\n" + "="*60)
print("TARGET EXTRACTION INVESTIGATION")
print("="*60)

# Check for target context words in events
TARGET_CONTEXT_WORDS = [
    "agonist", "antagonist", "inhibitor", "activator",
    "binding", "affinity", "receptor", "pathway", "signaling",
    "target", "modulator", "blocker",
]

print("\n1. Checking for target context words in events...")
print("-" * 60)

for word in TARGET_CONTEXT_WORDS:
    cur.execute("""
        SELECT COUNT(*)
        FROM research_events
        WHERE LOWER(evidence_snippet) LIKE ?
    """, (f'%{word}%',))
    
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  ✓ '{word}': {count} events")
        
        # Show sample
        cur.execute("""
            SELECT evidence_snippet
            FROM research_events
            WHERE LOWER(evidence_snippet) LIKE ?
            LIMIT 1
        """, (f'%{word}%',))
        
        sample = cur.fetchone()
        if sample:
            print(f"    Sample: {sample[0][:100]}...")

# Check for target names in events
TARGET_SEED_LIST = [
    "mtor", "ampk", "sirt1", "sirt3", "igf1", "igf1r",
    "foxo", "p53", "nfkb", "tnf", "il6",
    "glp1r", "glp-1r", "gcgr", "gipr",
    "nrf2", "akt", "pi3k", "mapk", "erk",
]

print("\n2. Checking for target names in events...")
print("-" * 60)

for target in TARGET_SEED_LIST:
    cur.execute("""
        SELECT COUNT(*)
        FROM research_events
        WHERE LOWER(evidence_snippet) LIKE ?
    """, (f'%{target}%',))
    
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  ✓ '{target}': {count} events")
        
        # Check if it has context
        cur.execute("""
            SELECT evidence_snippet
            FROM research_events
            WHERE LOWER(evidence_snippet) LIKE ?
            LIMIT 1
        """, (f'%{target}%',))
        
        sample = cur.fetchone()
        if sample:
            snippet = sample[0].lower()
            has_context = any(word in snippet for word in TARGET_CONTEXT_WORDS)
            context_str = "WITH context" if has_context else "NO context"
            print(f"    {context_str}: {sample[0][:100]}...")

# Check for sentences with BOTH target name AND context
print("\n3. Checking for sentences with target name + context...")
print("-" * 60)

for target in TARGET_SEED_LIST:
    for context_word in TARGET_CONTEXT_WORDS:
        cur.execute("""
            SELECT evidence_snippet
            FROM research_events
            WHERE LOWER(evidence_snippet) LIKE ?
              AND LOWER(evidence_snippet) LIKE ?
            LIMIT 1
        """, (f'%{target}%', f'%{context_word}%'))
        
        result = cur.fetchone()
        if result:
            print(f"  ✓ Found '{target}' + '{context_word}':")
            print(f"    {result[0][:150]}...")
            break

con.close()
