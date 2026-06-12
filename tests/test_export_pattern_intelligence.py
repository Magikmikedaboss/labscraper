import csv
import io
from utils import export_pattern_intelligence

ENTITY_NAME_IDX = 0
ENTITY_TYPE_IDX = 1
PATTERN_TYPE_IDX = 2
HEALTH_SCORE_IDX = 3
EVENT_COUNT_IDX = 4
POSITIVE_SIGNALS_IDX = 5
NEUTRAL_SIGNALS_IDX = 6
NEGATIVE_SIGNALS_IDX = 7
REPLICATION_SIGNALS_IDX = 8
TOTAL_SIGNALS_IDX = 9
TIME_MOMENTUM_IDX = 10
CONFIDENCE_LEVEL_IDX = 11
INTERPRETATION_IDX = 12

class DummySignals:
    def __init__(self, p=0, n=0, neu=0, rep=0):
        self.positive = p
        self.negative = n
        self.neutral = neu
        self.replication = rep
    def total(self):
        return self.positive + self.negative + self.neutral + self.replication

class DummyAnalysis:
    def __init__(self, i):
        self.entity_name = f"entity_{i}"
        self.entity_type = "protein"
        self.pattern_type = "convergence"
        self.health_score = 90
        self.event_count = 5
        self.outcome_signals = DummySignals(2, 0, 0, 1)
        self.time_momentum = "increasing"
        self.confidence_level = "high"
        self.interpretation = f"Interpretation {i}"


def test_export_to_csv(tmp_path):
    # Create dummy results
    results = [DummyAnalysis(i) for i in range(3)]
    out_file = tmp_path / "test_export.csv"
    export_pattern_intelligence.export_to_csv(results, out_file)
    # Check file exists and has correct columns
    csv_text = out_file.read_text()
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0][0:3] == ["entity_name", "entity_type", "pattern_type"]
    assert len(rows) == 4  # header + 3 rows
    # Check that the first data row matches DummyAnalysis(0)
    row0 = rows[1]
    assert row0[ENTITY_NAME_IDX] == "entity_0"
    assert row0[ENTITY_TYPE_IDX] == "protein"
    assert row0[PATTERN_TYPE_IDX] == "convergence"
    assert row0[HEALTH_SCORE_IDX] == "90"
    assert row0[EVENT_COUNT_IDX] == "5"
    assert row0[POSITIVE_SIGNALS_IDX] == "2"  # positive_signals
    assert row0[NEUTRAL_SIGNALS_IDX] == "0"  # neutral_signals
    assert row0[NEGATIVE_SIGNALS_IDX] == "0"  # negative_signals
    assert row0[REPLICATION_SIGNALS_IDX] == "1"  # replication_signals
    assert row0[TOTAL_SIGNALS_IDX] == "3"  # total_signals
    assert row0[TIME_MOMENTUM_IDX] == "increasing"
    assert row0[CONFIDENCE_LEVEL_IDX] == "high"
    assert row0[INTERPRETATION_IDX] == "Interpretation 0"

def test_main_runs(monkeypatch, tmp_path):
    dummy_results = [DummyAnalysis(0)]

    called = {}

    def fake_analyze_patterns(top_n):
        called["top_n"] = top_n
        return dummy_results

    monkeypatch.setattr(export_pattern_intelligence, "analyze_patterns", fake_analyze_patterns)
    output_file = tmp_path / "pattern_intelligence_export.csv"
    monkeypatch.setattr(export_pattern_intelligence, "OUTPUT_FILE", output_file)
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    export_pattern_intelligence.main()

    assert called["top_n"] == 50
    assert output_file.exists()

    csv_text = output_file.read_text(encoding="utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0][0:4] == ["entity_name", "entity_type", "pattern_type", "health_score"]
    assert rows[1][ENTITY_NAME_IDX] == "entity_0"
    assert rows[1][PATTERN_TYPE_IDX] == "convergence"

