
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
