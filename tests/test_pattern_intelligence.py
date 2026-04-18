
from utils import pattern_intelligence
import pytest

def test_detect_outcome_signals_basic():
    seeds = {
        "positive": ["improved", "success"],
        "neutral": ["no change"],
        "negative": ["failure"],
        "replication": ["replicated"]
    }
    text = "The experiment showed improved results and was replicated."
    signals = pattern_intelligence.detect_outcome_signals(text, seeds)
    assert signals.positive == 1
    assert signals.replication == 1
    assert signals.neutral == 0
    assert signals.negative == 0


@pytest.mark.parametrize(
    "event_count,expected",
    [
        (12, "convergence"),
        (2, "abandonment"),
    ]
)
def test_detect_pattern_type_param(event_count, expected):
    entity_name = "protein"
    events_data = []
    all_entity_counts = {}
    result = pattern_intelligence.detect_pattern_type(entity_name, event_count, events_data, all_entity_counts)    # If event_count (12) exceeds HIGH_RECURRENCE threshold (10) in detect_pattern_type,
    # the expected classification is "convergence"; empty events_data and all_entity_counts are valid for this test.
    assert result == expected


def test_determine_time_momentum():
    assert pattern_intelligence.determine_time_momentum(15, 5) == "increasing"
    assert pattern_intelligence.determine_time_momentum(2, 10) == "decreasing"
    assert pattern_intelligence.determine_time_momentum(10, 10) == "stable"


def test_determine_confidence_level():
    # No events
    assert pattern_intelligence.determine_confidence_level([]) == "low"
    # Majority high
    events = [{"confidence": "high"}] * 3 + [{"confidence": "low"}]
    assert pattern_intelligence.determine_confidence_level(events) == "high"
    # Majority med/high
    events = [{"confidence": "med"}] * 2 + [{"confidence": "high"}] + [{"confidence": "low"}]
    assert pattern_intelligence.determine_confidence_level(events) == "med"
    # Otherwise low
    events = [{"confidence": "low"}] * 3 + [{"confidence": "med"}]
    assert pattern_intelligence.determine_confidence_level(events) == "low"


def test_calculate_health_score():
    OutcomeSignals = pattern_intelligence.OutcomeSignals
    # High score
    score = pattern_intelligence.calculate_health_score(
        "convergence", OutcomeSignals(positive=3, neutral=2, negative=0, replication=1), "increasing", "high"
    )
    assert 0 <= score <= 100
    # Low score
    score = pattern_intelligence.calculate_health_score(
        "abandonment", OutcomeSignals(positive=0, neutral=0, negative=2, replication=0), "decreasing", "low"
    )
    assert 0 <= score <= 100


def test_generate_interpretation():
    OutcomeSignals = pattern_intelligence.OutcomeSignals
    interp = pattern_intelligence.generate_interpretation(
        "proteinX", "convergence", 85, OutcomeSignals(positive=2, neutral=0, negative=0, replication=0)
    )
    assert "proteinX" in interp and "strong research momentum" in interp
    interp = pattern_intelligence.generate_interpretation(
        "proteinY", "abandonment", 10, OutcomeSignals(positive=0, neutral=0, negative=2, replication=0)
    )
    assert "declining research attention" in interp
