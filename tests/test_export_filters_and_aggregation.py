from utils.export.aggregation import (
    build_entity_event_map,
    build_entity_models_map,
    build_entity_scores,
    build_event_models,
    build_event_overlay_scores,
)
from utils.export.filters import (
    is_valid_export_peptide,
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
        return "strong" if score >= max_score else "exploratory"


def test_filters_basic_behavior():
    assert is_valid_export_peptide("ACDEFGHIK")
    assert is_valid_export_peptide("octreotide")
    assert not is_valid_export_peptide("noise123")

    assert should_skip_entity("compound", "ASPIRIN", "context")
    assert should_skip_entity("peptide", "bad-token", "primary")
    assert not should_skip_entity("compound", "ASPIRIN", "primary")


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
