"""
Pattern Intelligence Module
Detects research patterns and calculates health scores from existing data.

Based on:
- RESEARCH_PATTERNS_FOUNDATION.md (Step 1: Pattern Types)
- OUTCOME_SIGNALS_FOUNDATION.md (Step 2: Outcome Signals)
- PATTERN_SCORING_FOUNDATION.md (Step 3: Pattern Health Score)
"""

import json
import sqlite3
from pathlib import Path
from collections import Counter
from typing import Dict, List
from dataclasses import dataclass

from utils.db_utils import connect_with_foreign_keys

# Paths
DB_PATH = Path("db") / "runs.sqlite"
SEEDS_DIR = Path("seeds")

# Lazy-loaded outcome signals
_OUTCOME_SIGNALS = None

def _get_outcome_signals():
    global _OUTCOME_SIGNALS
    if _OUTCOME_SIGNALS is None:
        signal_file = SEEDS_DIR / "outcome_signals.json"
        
        if not signal_file.exists():
            print(f"⚠️  Warning: {signal_file} not found. Using empty signals.")
            _OUTCOME_SIGNALS = {"positive": [], "neutral": [], "negative": [], "replication": []}
        else:
            with open(signal_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _OUTCOME_SIGNALS = {
                "positive": data.get("positive", []),
                "neutral": data.get("neutral", []),
                "negative": data.get("negative", []),
                "replication": data.get("replication", [])
            }
    return _OUTCOME_SIGNALS

def clear_cache():
    """Reset the cached outcome signals (for testing or reload)."""
    global _OUTCOME_SIGNALS
    _OUTCOME_SIGNALS = None


@dataclass
class OutcomeSignals:
    """Outcome signals detected in text"""
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    replication: int = 0
    
    def total(self) -> int:
        return self.positive + self.neutral + self.negative + self.replication


@dataclass
class PatternAnalysis:
    """Pattern analysis for an entity"""
    entity_name: str
    entity_type: str
    pattern_type: str
    outcome_signals: OutcomeSignals
    event_count: int
    time_momentum: str
    confidence_level: str
    health_score: int
    interpretation: str


# ============================================================================
# STEP 1: Load Outcome Signal Seeds
# ============================================================================

def load_outcome_signals() -> Dict[str, List[str]]:
    """Load outcome signal phrases from seeds/outcome_signals.json (cached)"""
    return _get_outcome_signals()


# ============================================================================
# STEP 2: Detect Outcome Signals in Text
# ============================================================================

def detect_outcome_signals(text: str, signal_seeds: Dict[str, List[str]]) -> OutcomeSignals:
    """
    Detect outcome signals in text.
    Simple deterministic matching (no ML needed).
    """
    if not text:
        return OutcomeSignals()
    
    text_lower = text.lower()
    signals = OutcomeSignals()
    
    # Count each signal type
    for phrase in signal_seeds.get("positive", []):
        if phrase.lower() in text_lower:
            signals.positive += 1
    
    for phrase in signal_seeds.get("neutral", []):
        if phrase.lower() in text_lower:
            signals.neutral += 1
    
    for phrase in signal_seeds.get("negative", []):
        if phrase.lower() in text_lower:
            signals.negative += 1
    
    for phrase in signal_seeds.get("replication", []):
        if phrase.lower() in text_lower:
            signals.replication += 1
    
    return signals


# ============================================================================
# STEP 3: Detect Pattern Type
# ============================================================================

def detect_pattern_type(
    entity_name: str,
    event_count: int,
    events_data: List[Dict],
    all_entity_counts: Dict[str, int]
) -> str:
    """
    Detect pattern type based on entity behavior.
    
    Pattern Types:
    - Convergence: High recurrence, consistent methods
    - Escalation: Progression in validation contexts
    - Stagnation: Recurring problems, no new solutions
    - Abandonment: Low/declining frequency
    - Fragmentation: Low recurrence, high diversity
    """
    
    # Thresholds (tunable)
    HIGH_RECURRENCE = 10  # Events needed for convergence
    LOW_RECURRENCE = 3    # Events below this = potential abandonment
    
    # Check for convergence (high recurrence)
    if event_count >= HIGH_RECURRENCE:
        # Check if it's a problem/challenge (stagnation) or method/entity (convergence)
        problem_keywords = ["aggregation", "degradation", "instability", "toxicity", "poor"]
        if any(kw in entity_name.lower() for kw in problem_keywords):
            return "stagnation"
        else:
            return "convergence"
    
    # Check for abandonment (low recurrence)
    elif event_count <= LOW_RECURRENCE:
        return "abandonment"
    
    # Check for escalation (look for progression signals in events)
    escalation_keywords = ["in vivo", "clinical", "human", "patient", "phase"]
    has_escalation = any(
        any(kw in (event.get("evidence_snippet") or "").lower() for kw in escalation_keywords)
        for event in events_data
    )
    if has_escalation:
        return "escalation"
    
    # Default: fragmentation (moderate recurrence, no clear pattern)
    return "fragmentation"


# ============================================================================
# STEP 4: Determine Time Momentum
# ============================================================================

def determine_time_momentum(event_count: int, avg_event_count: float) -> str:
    """
    Determine time momentum based on event count relative to average.
    
    In a real implementation, this would look at time series data.
    For now, we use relative frequency as a proxy.
    """
    if event_count > avg_event_count * 1.5:
        return "increasing"
    elif event_count < avg_event_count * 0.5:
        return "decreasing"
    else:
        return "stable"


# ============================================================================
# STEP 5: Determine Confidence Level
# ============================================================================

def determine_confidence_level(events_data: List[Dict]) -> str:
    """
    Determine overall confidence level from events.
    """
    if not events_data:
        return "low"
    
    # Count confidence levels
    confidence_counts = Counter(event.get("confidence", "low") for event in events_data)
    
    # Majority vote
    if confidence_counts.get("high", 0) > len(events_data) / 2:
        return "high"
    elif confidence_counts.get("med", 0) + confidence_counts.get("high", 0) > len(events_data) / 2:
        return "med"
    else:
        return "low"


# ============================================================================
# STEP 6: Calculate Pattern Health Score
# ============================================================================

def calculate_health_score(
    pattern_type: str,
    outcome_signals: OutcomeSignals,
    time_momentum: str,
    confidence_level: str
) -> int:
    """
    Calculate Pattern Health Score (0-100).
    
    Components:
    1. Pattern Type Base Score
    2. Outcome Signal Adjustment
    3. Time Momentum Adjustment
    4. Confidence Modifier
    """
    
    # 1. Pattern Type Base Score
    pattern_base = {
        "convergence": 40,
        "escalation": 45,
        "fragmentation": 20,
        "stagnation": 10,
        "abandonment": 0
    }
    score = pattern_base.get(pattern_type, 0)
    
    # 2. Outcome Signal Adjustment
    score += (outcome_signals.positive * 5)
    score -= (outcome_signals.negative * 5)
    score += (outcome_signals.replication * 3)
    score += min(outcome_signals.neutral, 5) * 1  # capped at 5
    
    # 3. Time Momentum Adjustment
    momentum_bonus = {
        "increasing": 10,
        "stable": 5,
        "decreasing": -10
    }
    score += momentum_bonus.get(time_momentum, 0)
    
    # 4. Confidence Modifier
    confidence_multiplier = {
        "high": 1.1,
        "med": 1.0,
        "low": 0.9
    }
    score = score * confidence_multiplier.get(confidence_level, 1.0)
    
    # 5. Clamp to 0-100
    score = max(0, min(int(score), 100))
    
    return score


# ============================================================================
# STEP 7: Generate Interpretation
# ============================================================================

def generate_interpretation(
    entity_name: str,
    pattern_type: str,
    health_score: int,
    outcome_signals: OutcomeSignals
) -> str:
    """
    Generate honest interpretation based on pattern and score.
    """
    # Score range interpretation
    if health_score >= 80:
        momentum = "strong research momentum"
    elif health_score >= 60:
        momentum = "promising and active research"
    elif health_score >= 40:
        momentum = "exploratory research"
    elif health_score >= 20:
        momentum = "stalled or uncertain research"
    else:
        momentum = "declining research attention"
    
    # Pattern-specific language
    pattern_desc = {
        "convergence": "with convergence around consistent methods",
        "escalation": "with increasing validation efforts",
        "stagnation": "encountering persistent technical barriers",
        "abandonment": "with declining research interest",
        "fragmentation": "remaining methodologically diverse"
    }
    
    # Outcome signal summary
    if outcome_signals.positive > outcome_signals.negative:
        signal_desc = "and predominantly positive outcome language"
    elif outcome_signals.negative > outcome_signals.positive:
        signal_desc = "and predominantly negative outcome language"
    else:
        signal_desc = "and mixed outcome language"
    
    # Combine
    interpretation = f"{entity_name} shows {momentum} {pattern_desc.get(pattern_type, '')} {signal_desc}."
    
    return interpretation


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_patterns(top_n: int = 20) -> List[PatternAnalysis]:
    """
    Analyze patterns for top N entities in the database.
    
    Returns list of PatternAnalysis objects sorted by health score.
    """
    print("="*70)
    print("PATTERN INTELLIGENCE ANALYSIS")
    print("="*70)
    
    # Load outcome signals
    print("\n📊 Loading outcome signals...")
    signal_seeds = _get_outcome_signals()
    print(f"   Loaded {sum(len(v) for v in signal_seeds.values())} signal phrases")
    
    # Check if database exists before connecting
    if not DB_PATH.exists():
        print(f"[ERROR] Database file not found: {DB_PATH}")
        print("[ERROR] Pattern analysis aborted. Please run the scraper/export to generate the database.")
        return []

    print(f"\n📂 Connecting to database: {DB_PATH}")
    with connect_with_foreign_keys(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        # Get top entities by event count
        print(f"\n🔍 Analyzing top {top_n} entities...")
        top_entities = cur.execute("""
            SELECT e.entity_name, e.entity_type, COUNT(ee.event_id) as event_count
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            GROUP BY e.entity_id
            ORDER BY event_count DESC
            LIMIT ?
        """, (top_n,)).fetchall()

        # Calculate average event count for momentum detection
        all_counts = [row["event_count"] for row in top_entities]
        avg_event_count = sum(all_counts) / len(all_counts) if all_counts else 1
        
        # Analyze each entity
        results = []
        
        for row in top_entities:
            entity_name = row["entity_name"]
            entity_type = row["entity_type"]
            event_count = row["event_count"]
            
            # Get events for this entity (filter by BOTH name AND type to avoid cross-contamination)
            events = cur.execute("""
                SELECT re.evidence_snippet, re.confidence
                FROM research_events re
                JOIN event_entities ee ON re.event_id = ee.event_id
                JOIN entities e ON ee.entity_id = e.entity_id
                WHERE e.entity_name = ? AND e.entity_type = ?
            """, (entity_name, entity_type)).fetchall()
            
            events_data = [dict(event) for event in events]
            
            # Detect outcome signals across all events (safely handle None snippets)
            all_text = " ".join(
                event.get("evidence_snippet") or ""
                for event in events_data
            )
            outcome_signals = detect_outcome_signals(all_text, signal_seeds)
            
            # Detect pattern type
            entity_counts = {row["entity_name"]: row["event_count"] for row in top_entities}
            pattern_type = detect_pattern_type(entity_name, event_count, events_data, entity_counts)
            
            # Determine time momentum
            time_momentum = determine_time_momentum(event_count, avg_event_count)
            
            # Determine confidence level
            confidence_level = determine_confidence_level(events_data)
            
            # Calculate health score
            health_score = calculate_health_score(
                pattern_type,
                outcome_signals,
                time_momentum,
                confidence_level
            )
            
            # Generate interpretation
            interpretation = generate_interpretation(
                entity_name,
                pattern_type,
                health_score,
                outcome_signals
            )
            
            # Create analysis object
            analysis = PatternAnalysis(
                entity_name=entity_name,
                entity_type=entity_type,
                pattern_type=pattern_type,
                outcome_signals=outcome_signals,
                event_count=event_count,
                time_momentum=time_momentum,
                confidence_level=confidence_level,
                health_score=health_score,
                interpretation=interpretation
            )
            
            results.append(analysis)
    
    # Sort by health score
    results.sort(key=lambda x: x.health_score, reverse=True)
    
    return results


# ============================================================================
# DISPLAY RESULTS
# ============================================================================

def display_results(results: List[PatternAnalysis]):
    """Display pattern analysis results"""
    print("\n" + "="*70)
    print("PATTERN ANALYSIS RESULTS")
    print("="*70)
    
    for i, analysis in enumerate(results, 1):
        print(f"\n{i}. {analysis.entity_name} ({analysis.entity_type})")
        print(f"   Pattern Type: {analysis.pattern_type.upper()}")
        print(f"   Health Score: {analysis.health_score}/100")
        print(f"   Events: {analysis.event_count}")
        print(f"   Signals: +{analysis.outcome_signals.positive} pos, "
              f"-{analysis.outcome_signals.negative} neg, "
              f"↻{analysis.outcome_signals.replication} rep, "
              f"○{analysis.outcome_signals.neutral} neu")
        print(f"   Momentum: {analysis.time_momentum}")
        print(f"   Confidence: {analysis.confidence_level}")
        print(f"   Interpretation: {analysis.interpretation}")
    
    # Summary statistics
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    
    pattern_counts = Counter(a.pattern_type for a in results)
    print("\n📊 Pattern Distribution:")
    for pattern, count in pattern_counts.most_common():
        print(f"   {pattern}: {count}")
    
    avg_score = sum(a.health_score for a in results) / len(results) if results else 0
    print(f"\n📈 Average Health Score: {avg_score:.1f}/100")
    
    high_momentum = [a for a in results if a.health_score >= 80]
    print(f"\n🚀 High Momentum Entities ({len(high_momentum)}):")
    for a in high_momentum[:5]:
        print(f"   - {a.entity_name}: {a.health_score}/100")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    results = analyze_patterns(top_n=20)
    display_results(results)
    
    print("\n✅ Pattern intelligence analysis complete!")
    print("\nNext steps:")
    print("  - Review pattern classifications")
    print("  - Adjust scoring weights if needed")
    print("  - Export results to CSV for dashboard integration")
