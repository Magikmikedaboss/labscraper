"""
Seed File Linter - Prevents ambiguous abbreviations from causing false positives

Checks for:
1. Short abbreviations (≤3 chars) that might be ambiguous
2. Terms that appear in multiple seed categories
3. Known problematic abbreviations
4. Missing word boundary protection

Usage:
    python lint_seeds.py
"""

import json
from pathlib import Path
from collections import defaultdict

# Known problematic abbreviations to flag
KNOWN_PROBLEMATIC = {
    "MS": "Multiple Sclerosis vs Mass Spectrometry",
    "KI": "Inhibition constant vs part of 'kinase'",
    "RB": "Retinoblastoma vs Rubidium",
    "NA": "Sodium (too generic)",
    "K": "Potassium (too generic)",
    "CA": "Calcium (too generic)",
    "IC": "Inhibitory Concentration vs part of 'clinical'",
    "EC": "Effective Concentration (needs word boundary)",
}

# Safe short abbreviations (unambiguous)
SAFE_SHORT_TERMS = {
    "LC-MS", "LC-MS/MS", "HPLC", "ELISA", "QPCR", "NMR", "SPR", "BLI",
    "MALDI-TOF", "ESI-MS", "QTOF", "GC-MS", "RP-HPLC", "UPLC", "UHPLC",
    "SEC", "TLC", "TOF", "MS/MS", "SRM", "MRM", "PRM", "DDA", "DIA",
    "LOD", "LOQ", "IC50", "EC50", "KD", "AUC", "CMAX", "T1/2", "TMAX",
    "LD50", "ED50", "FBS", "BSA", "CSF", "DMEM", "RPMI", "MEM", "F12",
    "FFPE", "UPR", "EMT", "TCA", "DNA", "RNA", "PCR", "ATP", "GTP",
    "NADH", "FADH", "CAMP", "CGMP", "HSP70", "HSP90", "GRP78", "BIP",
    "PERK", "IRE1", "ATF6", "CHOP", "LC3", "LC3B", "P62", "CDK4", "CDK6",
    "OCT4", "SOX2", "KLF4", "MYC", "MTOR", "AMPK", "SIRT1", "SIRT3",
    "FOXO1", "FOXO3", "PGC1A", "PPARΑ", "PPARΓ", "PPARΔ", "GLP1R",
    "GLP-1R", "GCGR", "GIPR", "IGF1R", "INSR", "EGFR", "FGFR1", "FGFR2",
    "NFKB", "NF-ΚB", "TNF", "TNFA", "TNF-Α", "IL6", "IL-6", "IL1B",
    "COX2", "COX-2", "NRF2", "SOD1", "SOD2", "CAT", "GPX1", "AKT",
    "AKT1", "PI3K", "MAPK", "ERK", "ERK1", "ERK2", "JNK", "P38", "P53",
    "TP53", "BCL2", "BAX", "CASP3", "CASP9", "CASR", "PTH1R",
    "MMP1", "MMP2", "MMP3", "MMP7", "MMP9", "MMP13", "ADAM10", "ADAM17",
    "BACE1", "DPP4", "DPP-4", "NEP", "ACE", "PCSK9", "CASP1", "CASP8",
    "ATG5", "ATG7", "BECN1", "SQSTM1", "RB1", "CCND1", "NANOG", "SUMO",
    "MSC", "HMSC", "IPSC", "HIPSC", "ESC", "HESC", "NSC", "HSC", "PBMC",
    "HEK293", "HELA", "CHO", "A549", "MCF-7", "HCT116", "U2OS", "NIH3T3",
    "K562", "PC12", "HEPG2", "CACO-2", "MDCK", "BHK", "VERO", "COS-7",
    "SCID", "NSG", "SPE", "QC", "3D", "2D", "DUB",
}
SAFE_SHORT_TERMS_UPPER = {t.upper() for t in SAFE_SHORT_TERMS}


def load_json_seeds(filepath: Path) -> list:
    """Load seeds from JSON file"""
    if not filepath.exists():
        return []
    
    data = json.loads(filepath.read_text(encoding='utf-8'))
    
    # Handle different JSON structures
    if isinstance(data, dict):
        # For assays.json, pathways.json, indications.json
        if 'assays' in data:
            return [item.get('name', '') for item in data['assays']] + data.get('metrics', [])
        elif 'pathways' in data:
            return data['pathways']
        elif 'indications' in data:
            return [item.get('name', '') for item in data['indications']]
    
    return []


def load_txt_seeds(filepath: Path) -> list:
    """Load seeds from TXT file"""
    if not filepath.exists():
        return []
    
    seeds = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                seeds.append(line)
    
    return seeds


def lint_seeds():
    """Check all seed files for potential issues"""
    seeds_dir = Path(__file__).resolve().parent / "../seeds"
    
    print("=" * 70)
    print("SEED FILE LINTER - Checking for ambiguous abbreviations")
    print("=" * 70)
    
    # Load all seeds
    all_seeds = {}
    all_seeds['assays'] = load_json_seeds(seeds_dir / "assays.json")
    all_seeds['pathways'] = load_json_seeds(seeds_dir / "pathways.json")
    all_seeds['indications'] = load_json_seeds(seeds_dir / "indications.json")
    all_seeds['compounds'] = load_txt_seeds(seeds_dir / "compounds.txt")
    all_seeds['targets'] = load_txt_seeds(seeds_dir / "targets.txt")
    all_seeds['models'] = load_txt_seeds(seeds_dir / "models.txt")
    
    issues_found = 0
    warnings_found = 0
    
    # Check 1: Known problematic abbreviations
    print("\n🔍 Check 1: Known Problematic Abbreviations")
    print("-" * 70)
    
    for category, seeds in all_seeds.items():
        for seed in seeds:
            seed_upper = seed.upper()
            if seed_upper in KNOWN_PROBLEMATIC:
                print(f"❌ CRITICAL: '{seed}' in {category}")
                print(f"   Reason: {KNOWN_PROBLEMATIC[seed_upper]}")
                print(f"   Action: Remove or use full term")
                issues_found += 1
    
    if issues_found == 0:
        print("✅ No known problematic abbreviations found")
    
    # Check 2: Short abbreviations (≤3 chars, not in safe list)
    print("\n🔍 Check 2: Short Abbreviations (≤3 chars)")
    print("-" * 70)
    
    short_abbrevs = 0
    for category, seeds in all_seeds.items():
        for seed in seeds:
            if len(seed) <= 3 and seed.upper() not in SAFE_SHORT_TERMS_UPPER:
                # Skip if it's part of a longer term with punctuation
                if any(c in seed for c in ['-', '/', '_', '.']):
                    continue
                
                print(f"⚠️  WARNING: '{seed}' in {category} (length: {len(seed)})")
                print(f"   Suggestion: Use full term or add to SAFE_SHORT_TERMS if unambiguous")
                short_abbrevs += 1
                warnings_found += 1
    
    if short_abbrevs == 0:
        print("✅ No risky short abbreviations found")
    
    # Check 3: Duplicate terms across categories
    print("\n🔍 Check 3: Terms in Multiple Categories")
    print("-" * 70)
    
    term_locations = defaultdict(list)
    for category, seeds in all_seeds.items():
        for seed in seeds:
            term_locations[seed.lower()].append(category)
    
    duplicates = 0
    for term, categories in term_locations.items():
        if len(categories) > 1:
            print(f"⚠️  WARNING: '{term}' appears in: {', '.join(categories)}")
            print(f"   Suggestion: Verify this is intentional")
            duplicates += 1
            warnings_found += 1
    
    if duplicates == 0:
        print("✅ No duplicate terms across categories")
    
    # Check 4: Very common words that might cause noise
    print("\n🔍 Check 4: Potentially Noisy Terms")
    print("-" * 70)
    
    COMMON_WORDS = {
        'cell', 'cells', 'tissue', 'protein', 'peptide', 'drug', 'compound',
        'receptor', 'enzyme', 'factor', 'system', 'process', 'pathway',
        'response', 'signaling', 'metabolism', 'synthesis', 'degradation',
    }
    
    noisy_terms = 0
    for category, seeds in all_seeds.items():
        for seed in seeds:
            if seed.lower() in COMMON_WORDS:
                print(f"⚠️  WARNING: '{seed}' in {category} (very common word)")
                print(f"   Suggestion: Consider using more specific term")
                noisy_terms += 1
                warnings_found += 1
    
    if noisy_terms == 0:
        print("✅ No overly generic terms found")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_seeds = sum(len(seeds) for seeds in all_seeds.values())
    print(f"Total seeds checked: {total_seeds}")
    print(f"  - Assays: {len(all_seeds['assays'])}")
    print(f"  - Pathways: {len(all_seeds['pathways'])}")
    print(f"  - Indications: {len(all_seeds['indications'])}")
    print(f"  - Compounds: {len(all_seeds['compounds'])}")
    print(f"  - Targets: {len(all_seeds['targets'])}")
    print(f"  - Models: {len(all_seeds['models'])}")
    
    print(f"\n❌ Critical issues: {issues_found}")
    print(f"⚠️  Warnings: {warnings_found}")
    
    if issues_found == 0 and warnings_found == 0:
        print("\n✅ All seed files look good!")
        return 0
    elif issues_found > 0:
        print("\n❌ CRITICAL ISSUES FOUND - Fix before running scraper!")
        return 1
    else:
        print("\n⚠️  Warnings found - Review before production use")
        return 0


if __name__ == "__main__":
    exit(lint_seeds())
