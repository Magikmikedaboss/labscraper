import csv
import io
import pytest
from utils import export_pattern_intelligence

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
    assert row0[0] == "entity_0"
    assert row0[1] == "protein"
    assert row0[2] == "convergence"
    assert row0[3] == "90"
    assert row0[4] == "5"
    assert row0[5] == "2"  # positive_signals
    assert row0[6] == "0"  # neutral_signals
    assert row0[7] == "0"  # negative_signals
    assert row0[8] == "1"  # replication_signals
    assert row0[9] == "3"  # total_signals
    assert row0[10] == "increasing"
    assert row0[11] == "high"
    assert row0[12] == "Interpretation 0"

# Optionally, test main() just for coverage (does not assert output)
def test_main_runs(monkeypatch):
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)
    try:
        result = export_pattern_intelligence.main()
    except Exception as e:
        pytest.fail(f"main() raised an exception: {e}")
    assert result is None
