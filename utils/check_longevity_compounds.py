from pathlib import Path

def check_longevity_compounds():
    """Check which popular longevity compounds are in seeds"""
    
    # Read current compounds
    try:
        compounds_text = Path('seeds/base/life_sciences/compounds.txt').read_text(encoding='utf-8').lower()
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error: Could not read compounds file: {e}")
        parsed_compounds_set = set()
    else:
        parsed_compounds_set = set()
        for line in compounds_text.splitlines():
            # Strip inline comments
            line = line.split('#', 1)[0].strip()
            compound = ' '.join(line.split())
            if compound:
                parsed_compounds_set.add(compound)
    
    # Popular longevity/biohacking compounds
    longevity_compounds = [
        'nad+',
        'nmn',
        'nr',
        'resveratrol',
        'spermidine',
        'fisetin',
        'quercetin',
        'curcumin',
        'berberine',
        'alpha-ketoglutarate',
        'ca-akg',
        'urolithin a',
        'apigenin',
        'luteolin',
        'pterostilbene',
        'sulforaphane',
        'egcg',
        'astaxanthin',
        'coq10',
        'pqq'
    ]
    
    print("\n" + "="*70)
    print("LONGEVITY COMPOUND CHECK")
    print("="*70)
    
    print("\nChecking for popular longevity/biohacking compounds...")
    
    found = []
    missing = []
    
    for compound in longevity_compounds:
        if compound in parsed_compounds_set:
            found.append(compound)
        else:
            missing.append(compound)
    
    print(f"\n✅ ALREADY IN SEEDS ({len(found)}/{len(longevity_compounds)}):")
    if found:
        for c in found:
            print(f"   ✓ {c}")
    else:
        print("   (none)")
    
    print(f"\n❌ MISSING ({len(missing)}/{len(longevity_compounds)}):")
    if missing:
        for c in missing:
            print(f"   ✗ {c}")
    else:
        print("   (none)")
    
    # Show current compounds
    print("\n" + "="*70)
    print("CURRENT COMPOUNDS IN SEEDS")
    print("="*70)
    
    all_compounds = sorted(parsed_compounds_set)
    print(f"\nTotal compounds: {len(all_compounds)}\n")
    for i, compound in enumerate(all_compounds, 1):
        print(f"   {i:2d}. {compound}")
    
    # Recommendations
    if missing:
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        print("\nTo add missing longevity compounds, append to seeds/base/life_sciences/compounds.txt:")
        print("\n# longevity & anti-aging compounds")
        for c in missing[:10]:  # Show first 10
            print(c)
        if len(missing) > 10:
            print(f"# ... and {len(missing)-10} more")

if __name__ == "__main__":
    check_longevity_compounds()
