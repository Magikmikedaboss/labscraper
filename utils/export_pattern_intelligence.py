"""
Export Pattern Intelligence Results to CSV
Creates a comprehensive pattern analysis export for dashboard integration.
"""

import csv
from pathlib import Path
from datetime import datetime
from pattern_intelligence import analyze_patterns

# Output path
OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "pattern_intelligence_export.csv"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def export_to_csv(results, output_file):
    """Export pattern analysis results to CSV"""
    
    print(f"\n📊 Exporting {len(results)} pattern analyses to CSV...")
    
    # Ensure parent directory exists
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Get current timestamp
    export_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Define CSV columns
    fieldnames = [
        "entity_name",
        "entity_type",
        "pattern_type",
        "health_score",
        "event_count",
        "positive_signals",
        "neutral_signals",
        "negative_signals",
        "replication_signals",
        "total_signals",
        "time_momentum",
        "confidence_level",
        "interpretation",
        "export_timestamp"
    ]
    
    # Write CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for analysis in results:
            writer.writerow({
                "entity_name": analysis.entity_name,
                "entity_type": analysis.entity_type,
                "pattern_type": analysis.pattern_type,
                "health_score": analysis.health_score,
                "event_count": analysis.event_count,
                "positive_signals": analysis.outcome_signals.positive,
                "neutral_signals": analysis.outcome_signals.neutral,
                "negative_signals": analysis.outcome_signals.negative,
                "replication_signals": analysis.outcome_signals.replication,
                "total_signals": analysis.outcome_signals.total(),
                "time_momentum": analysis.time_momentum,
                "confidence_level": analysis.confidence_level,
                "interpretation": analysis.interpretation,
                "export_timestamp": export_timestamp
            })
    
    print(f"✅ Exported to: {output_file}")
    print(f"\n📋 CSV Columns:")
    for col in fieldnames:
        print(f"   - {col}")


def main():
    """Main export function"""
    print("="*70)
    print("PATTERN INTELLIGENCE EXPORT")
    print("="*70)
    
    # Analyze patterns (top 50 entities)
    print("\n🔍 Analyzing patterns...")
    results = analyze_patterns(top_n=50)
    
    # Export to CSV
    export_to_csv(results, OUTPUT_FILE)
    
    # Summary
    print("\n" + "="*70)
    print("EXPORT SUMMARY")
    print("="*70)
    
    print(f"\n📊 Pattern Distribution:")
    from collections import Counter
    pattern_counts = Counter(a.pattern_type for a in results)
    for pattern, count in pattern_counts.most_common():
        print(f"   {pattern}: {count}")
    
    print(f"\n📈 Health Score Distribution:")
    score_ranges = {
        "Strong (80-100)": len([a for a in results if a.health_score >= 80]),
        "Promising (60-79)": len([a for a in results if 60 <= a.health_score < 80]),
        "Exploratory (40-59)": len([a for a in results if 40 <= a.health_score < 60]),
        "Stalled (20-39)": len([a for a in results if 20 <= a.health_score < 40]),
        "Deprioritized (0-19)": len([a for a in results if a.health_score < 20])
    }
    for range_name, count in score_ranges.items():
        print(f"   {range_name}: {count}")
    
    print(f"\n🚀 Top 10 by Health Score:")
    for i, analysis in enumerate(results[:10], 1):
        print(f"   {i}. {analysis.entity_name} ({analysis.entity_type}): {analysis.health_score}/100")
    
    print(f"\n✅ Pattern intelligence export complete!")
    print(f"\nNext steps:")
    print(f"  - Open {OUTPUT_FILE} in Excel/Google Sheets")
    print(f"  - Filter by pattern_type or health_score")
    print(f"  - Integrate with dashboard visualization")


if __name__ == "__main__":
    main()
