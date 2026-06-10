import json

from utils.export.aggregation import (
    build_entity_event_map,
    build_entity_models_map,
    build_entity_scores,
    build_event_models,
    build_event_overlay_scores,
    load_events_and_entities,
)
from utils.export.filters import (
    DEFAULT_KNOWN_PEPTIDES,
    is_valid_export_peptide,
    get_known_peptides,
    load_known_peptides,
    should_skip_entity,
    should_suppress_entity_for_csv,
)


class DummyScorer:
    def apply_event_scores(self, event_dict):
        return {"overlay_a": 1.0}

    def calculate_entity_score(self, entity_dict, event_scores_list, overlay_id, entity_models=None):
        model_bonus = 1.0 if entity_models else 0.0
        return sum(event_scores_list) + model_bonus

    def bucket_score(self, score, max_score):
        self.last_max_score = max_score
        return "strong" if score >= max_score else "exploratory"


def test_filters_basic_behavior():
    assert is_valid_export_peptide("ACDEFGHIK")
    assert is_valid_export_peptide("octreotide")
    assert not is_valid_export_peptide("noise123")

    assert should_skip_entity("compound", "ASPIRIN", "context")
    assert should_skip_entity("peptide", "bad-token", "primary")
    assert not should_skip_entity("compound", "ASPIRIN", "primary")


def test_load_known_peptides_from_json_config(tmp_path):
    config_path = tmp_path / "peptides.json"
    config_path.write_text(
        json.dumps([" octreotide ", "lanreotide", "Lanreotide", 123, None]),
        encoding="utf-8",
    )

    loaded = load_known_peptides(config_path=config_path, env={})

    assert loaded == {"OCTREOTIDE", "LANREOTIDE"}


def test_load_known_peptides_env_and_fallback(tmp_path):
    loaded = load_known_peptides(env={"LABSCRAPER_KNOWN_PEPTIDES": "etelcalcetide,  teriparatide\n"})
    assert loaded == {"ETELCALCETIDE", "TERIPARATIDE"}

    malformed_path = tmp_path / "peptides.json"
    malformed_path.write_text("{not-json", encoding="utf-8")

    assert load_known_peptides(config_path=malformed_path, env={}) == set(DEFAULT_KNOWN_PEPTIDES)


def test_get_known_peptides_caches_loaded_values(monkeypatch):
    import utils.export.filters as filters

    filters._KNOWN_PEPTIDES = None
    calls = []

    def fake_load_known_peptides():
        calls.append("load")
        return {"OCTREOTIDE"}

    monkeypatch.setattr(filters, "load_known_peptides", fake_load_known_peptides)

    assert get_known_peptides() == {"OCTREOTIDE"}
    assert get_known_peptides() == {"OCTREOTIDE"}
    assert calls == ["load"]


def test_get_known_peptides_falls_back_on_value_error(monkeypatch):
    import utils.export.filters as filters

    filters._KNOWN_PEPTIDES = None

    def fake_load_known_peptides():
        raise ValueError("bad peptide config")

    monkeypatch.setattr(filters, "load_known_peptides", fake_load_known_peptides)

    assert get_known_peptides() == set(DEFAULT_KNOWN_PEPTIDES)
    assert get_known_peptides() == set(DEFAULT_KNOWN_PEPTIDES)


def test_should_suppress_entity_for_csv_threshold_and_none_events():
    entity = {"entity_type": "peptide", "entity_id": "p1"}

    # None should behave like an empty mapping
    assert should_suppress_entity_for_csv(entity, None)

    low_events = {"p1": ["e1"]}
    enough_events = {"p1": ["e1", "e2"]}

    assert should_suppress_entity_for_csv(entity, low_events)
    assert not should_suppress_entity_for_csv(entity, enough_events)


def test_build_event_overlay_scores_skips_missing_event_id(caplog):
    scorer = DummyScorer()
    events = [
        {"event_id": "evt-1", "event_type": "x"},
        {"event_type": "missing_id"},
    ]

    with caplog.at_level("WARNING"):
        scores = build_event_overlay_scores(events, scorer)

    assert "evt-1" in scores
    assert len(scores) == 1
    assert any("Skipping event without valid event_id" in m for m in caplog.messages)


def test_build_event_map_models_and_scores_are_defensive():
    event_entities = [
        {"entity_id": "ent-1", "event_id": "evt-1"},
        {"entity_id": "ent-1", "event_id": None},
        {"entity_id": 99, "event_id": "evt-bad"},
    ]
    mapped = build_entity_event_map(event_entities, {"ent-1": "ent-canonical"})
    assert mapped["ent-canonical"] == ["evt-1"]

    model_rows = [
        {"event_id": "evt-1", "entity_name": "MODEL_A"},
        {"event_id": "evt-2"},
    ]
    event_models = build_event_models(model_rows)
    entity_models_map = build_entity_models_map(mapped, event_models)
    assert "MODEL_A" in entity_models_map["ent-canonical"]

    entities = [
        {"entity_id": "ent-canonical", "entity_name": "ENTITY", "entity_type": "compound"},
        {"entity_name": "MISSING_ID", "entity_type": "compound"},
        "not-a-dict",
    ]
    event_overlay_scores = {"evt-1": {"overlay_a": 2.0}}

    scores = build_entity_scores(
        entities=entities,
        overlay_ids=["overlay_a"],
        entity_events=mapped,
        entity_models_map=entity_models_map,
        event_overlay_scores=event_overlay_scores,
        scorer=DummyScorer(),
    )

    assert "ent-canonical" in scores
    assert "overlay_a" in scores["ent-canonical"]


def test_build_entity_scores_uses_construction_bucket_config():
    scorer = DummyScorer()

    scores = build_entity_scores(
        entities=[{"entity_id": "ent-1", "entity_name": "ENTITY", "entity_type": "compound"}],
        overlay_ids=["overlay_a"],
        entity_events={"ent-1": ["evt-1", "evt-2", "evt-3", "evt-4"]},
        entity_models_map={"ent-1": set()},
        event_overlay_scores={
            "evt-1": {"overlay_a": 1.0},
            "evt-2": {"overlay_a": 1.0},
            "evt-3": {"overlay_a": 1.0},
            "evt-4": {"overlay_a": 1.0},
        },
        scorer=scorer,
        domain_id="construction_science",
    )

    assert scores["ent-1"]["overlay_a"]["score"] == 4.0
    assert scorer.last_max_score == 8


def test_load_events_and_entities_supports_study_stage_schema(tmp_path):
    db_path = tmp_path / "study_stage.sqlite"
    import sqlite3

    con = sqlite3.connect(db_path)
    con.execute(
        """
        CREATE TABLE research_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT,
            study_stage TEXT,
            confidence TEXT,
            evidence_snippet TEXT,
            source_id TEXT,
            doc_id TEXT,
            chunk_id TEXT,
            page_number INTEGER,
            created_at TEXT
        )
        """
    )
    con.execute(
        """
        CREATE TABLE entities (
            entity_id TEXT PRIMARY KEY,
            entity_type TEXT,
            entity_name TEXT,
            entity_variant TEXT,
            organism TEXT,
            created_at TEXT
        )
        """
    )
    con.execute("CREATE TABLE event_entities (entity_id TEXT, event_id TEXT, role TEXT)")
    con.execute(
        "INSERT INTO research_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("ev1", "failure", "pilot", "high", "snippet", "src1", "doc1", "chunk1", 1, "2026-01-01"),
    )
    con.execute(
        "INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?)",
        ("ent1", "system", "Wall", "", "", "2026-01-01"),
    )
    con.execute("INSERT INTO event_entities VALUES (?, ?, ?)", ("ent1", "ev1", "primary"))
    con.commit()
    con.close()

    events, entities, event_entities, model_rows = load_events_and_entities(str(db_path))

    assert events[0]["stage"] == "pilot"
    assert entities[0]["entity_name"] == "Wall"
    assert event_entities[0]["event_id"] == "ev1"
    assert model_rows == []
