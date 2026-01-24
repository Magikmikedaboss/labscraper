"""
View Pattern Intelligence Export
Displays the pattern intelligence results in a readable format
"""

import csv
from pathlib import Path
from collections import Counter

OUTPUT_FILE = Path("output") / "pattern_intelligence_export.csv"


def view_export():
    """View pattern intelligence export"""
    
    if not OUTPUT_FILE.exists():
        print(f"❌ Export file not found: {OUTPUT_FILE}")
        print(f"\nRun: python export_pattern_intelligence.py")
        return
    
    print("="*80)
    print("PATTERN INTELLIGENCE EXPORT VIEWER")
    print("="*80)
    
    # Read CSV
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Check for empty export
    if not rows:
        print(f"\n⚠️  Export file is empty - no data to display")
        print(f"\nRun: python export_pattern_intelligence.py")
        return
    
    print(f"\n📊 Total Entities Analyzed: {len(rows)}")
    
    # Pattern distribution
    print(f"\n📋 Pattern Distribution:")
    pattern_counts = Counter(row['pattern_type'] for row in rows)
    for pattern, count in pattern_counts.most_common():
        pct = (count / len(rows) * 100)
        print(f"   {pattern:15s}: {count:2d} ({pct:5.1f}%)")
    
    # Health score distribution
    print(f"\n📈 Health Score Distribution:")
    def safe_health_score(row):
        try:
            return int(row.get('health_score', 0))
        except (ValueError, TypeError):
            return 0
    score_ranges = {
        "Strong (80-100)": [r for r in rows if safe_health_score(r) >= 80],
        "Promising (60-79)": [r for r in rows if 60 <= safe_health_score(r) < 80],
        "Exploratory (40-59)": [r for r in rows if 40 <= safe_health_score(r) < 60],
        "Stalled (20-39)": [r for r in rows if 20 <= safe_health_score(r) < 40],
        "Deprioritized (0-19)": [r for r in rows if safe_health_score(r) < 20]
    }
    
    for range_name, entities in score_ranges.items():
        count = len(entities)
        pct = (count / len(rows) * 100)
        print(f"   {range_name:20s}: {count:2d} ({pct:5.1f}%)")
    
    # Top 15 by health score
    print(f"\n🏆 Top 15 Entities by Health Score:")
    print(f"{'#':<4} {'Entity':<25} {'Type':<12} {'Score':<6} {'Pattern':<15} {'Events':<7}")
    print("-"*80)
    
    sorted_rows = sorted(rows, key=lambda x: int(x['health_score']), reverse=True)
    for i, row in enumerate(sorted_rows[:15], 1):
        entity = row['entity_name'][:24]
        etype = row['entity_type'][:11]
        score = row['health_score']
        pattern = row['pattern_type'][:14]
        events = row['event_count']
        
        print(f"{i:<4} {entity:<25} {etype:<12} {score:<6} {pattern:<15} {events:<7}")
    
    # Bottom 10 by health score
    print(f"\n⚠️  Bottom 10 Entities by Health Score:")
    print(f"{'#':<4} {'Entity':<25} {'Type':<12} {'Score':<6} {'Pattern':<15} {'Events':<7}")
    print("-"*80)
    
    for i, row in enumerate(sorted_rows[-10:], 1):
        entity = row['entity_name'][:24]
        etype = row['entity_type'][:11]
        score = row['health_score']
        pattern = row['pattern_type'][:14]
        events = row['event_count']
        
        print(f"{i:<4} {entity:<25} {etype:<12} {score:<6} {pattern:<15} {events:<7}")
    
    # Signal statistics
    print(f"\n📊 Signal Statistics:")
    total_positive = sum(int(row['positive_signals']) for row in rows)
    total_neutral = sum(int(row['neutral_signals']) for row in rows)
    total_negative = sum(int(row['negative_signals']) for row in rows)
    total_replication = sum(int(row['replication_signals']) for row in rows)
    total_signals = total_positive + total_neutral + total_negative + total_replication
    
    print(f"   Total Signals Detected: {total_signals}")
    
    # Handle zero total_signals to avoid ZeroDivisionError
    if total_signals > 0:
        print(f"   Positive:    {total_positive:4d} ({total_positive/total_signals*100:5.1f}%)")
        print(f"   Neutral:     {total_neutral:4d} ({total_neutral/total_signals*100:5.1f}%)")
        print(f"   Negative:    {total_negative:4d} ({total_negative/total_signals*100:5.1f}%)")
        print(f"   Replication: {total_replication:4d} ({total_replication/total_signals*100:5.1f}%)")
    else:
        print(f"   Positive:    {total_positive:4d} (0.0%)")
        print(f"   Neutral:     {total_neutral:4d} (0.0%)")
        print(f"   Negative:    {total_negative:4d} (0.0%)")
        print(f"   Replication: {total_replication:4d} (0.0%)")
    
    # Sample interpretations
    print(f"\n💬 Sample Interpretations:")
    length = len(sorted_rows)
    if length >= 1:
        print(f"\n1. Highest Score ({sorted_rows[0]['entity_name']}):")
        print(f"   {sorted_rows[0]['interpretation']}")
    if length >= 3:
        mid_idx = length // 2
        # Only print mid if not duplicating highest/lowest
        if mid_idx != 0 and mid_idx != length - 1:
            print(f"\n2. Mid-Range Score ({sorted_rows[mid_idx]['entity_name']}):")
            print(f"   {sorted_rows[mid_idx]['interpretation']}")
    if length >= 2:
        print(f"\n3. Lowest Score ({sorted_rows[-1]['entity_name']}):")
        print(f"   {sorted_rows[-1]['interpretation']}")
    
    # Export info
    print(f"\n" + "="*80)
    print(f"📁 Export File: {OUTPUT_FILE}")
    print(f"📋 Columns: {len(rows[0])} columns")
    print(f"📊 Rows: {len(rows)} entities")
    print(f"\n✅ Open in Excel/Google Sheets for full analysis")
    print("="*80)


if __name__ == "__main__":
    view_export()
