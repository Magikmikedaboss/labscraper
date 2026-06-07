import sqlite3

import pytest
from utils import pattern_intelligence


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
    result = pattern_intelligence.detect_pattern_type(
        entity_name,
        event_count,
        events_data,
        all_entity_counts
    )
    # Verify convergence when event_count > HIGH_RECURRENCE.
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
    # High score scenario
    high_score = pattern_intelligence.calculate_health_score(
        "convergence", OutcomeSignals(positive=3, neutral=2, negative=0, replication=1), "increasing", "high"
    )
    assert 0 <= high_score <= 100
    # Low score scenario
    low_score = pattern_intelligence.calculate_health_score(
        "abandonment", OutcomeSignals(positive=0, neutral=0, negative=2, replication=0), "decreasing", "low"
    )
    assert 0 <= low_score <= 100
    # Assert high scenario produces a higher score than low scenario
    assert high_score > low_score, f"Expected high_score ({high_score}) > low_score ({low_score})"


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


def test_analyze_patterns_missing_db_returns_empty(monkeypatch, tmp_path, capsys):
    missing_db = tmp_path / "missing.sqlite"
    monkeypatch.setattr(pattern_intelligence, "DB_PATH", missing_db)
    monkeypatch.setattr(
        pattern_intelligence,
        "_get_outcome_signals",
        lambda: {"positive": [], "neutral": [], "negative": [], "replication": []},
    )

    results = pattern_intelligence.analyze_patterns(top_n=3)
    output = capsys.readouterr().out

    assert results == []
    assert "Database file not found" in output


def test_analyze_patterns_and_display_results(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "patterns.sqlite"
    with sqlite3.connect(db_path) as con:
        con.executescript(
            """
            CREATE TABLE entities (entity_id TEXT PRIMARY KEY, entity_name TEXT, entity_type TEXT);
            CREATE TABLE research_events (event_id TEXT PRIMARY KEY, evidence_snippet TEXT, confidence TEXT);
            CREATE TABLE event_entities (event_id TEXT, entity_id TEXT);
            """
        )
        con.execute("INSERT INTO entities VALUES (?, ?, ?)", ("e1", "Protein A", "target"))
        con.execute("INSERT INTO entities VALUES (?, ?, ?)", ("e2", "Protein B", "target"))

        con.execute("INSERT INTO research_events VALUES (?, ?, ?)", ("ev1", "improved and replicated in vivo", "high"))
        con.execute("INSERT INTO research_events VALUES (?, ?, ?)", ("ev2", "improved outcomes", "med"))
        con.execute("INSERT INTO research_events VALUES (?, ?, ?)", ("ev3", "failure observed", "low"))

        con.execute("INSERT INTO event_entities VALUES (?, ?)", ("ev1", "e1"))
        con.execute("INSERT INTO event_entities VALUES (?, ?)", ("ev2", "e1"))
        con.execute("INSERT INTO event_entities VALUES (?, ?)", ("ev3", "e2"))

    monkeypatch.setattr(pattern_intelligence, "DB_PATH", db_path)
    monkeypatch.setattr(
        pattern_intelligence,
        "_get_outcome_signals",
        lambda: {
            "positive": ["improved"],
            "neutral": [],
            "negative": ["failure"],
            "replication": ["replicated"],
        },
    )

    results = pattern_intelligence.analyze_patterns(top_n=2)

    assert len(results) == 2
    assert results[0].health_score >= results[1].health_score
    assert {results[0].entity_name, results[1].entity_name} == {"Protein A", "Protein B"}

    pattern_intelligence.display_results(results)
    output = capsys.readouterr().out
    assert "PATTERN ANALYSIS RESULTS" in output
    assert "SUMMARY STATISTICS" in output
