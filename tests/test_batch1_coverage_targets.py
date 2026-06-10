import copy
import sqlite3
from typing import Any, Callable

import pytest

from utils.confidence_utils import normalize_confidence, safe_confidence_boost
from utils.domain_enforcement import (
    filter_entities_for_domain,
    get_contaminated_entity_types,
    is_entity_type_allowed_for_domain,
)
from utils.export.normalization import build_canonical_entities, normalize_entity_type


@pytest.fixture(scope="module")
def fake_normalize_entity():
    def _fake_normalize_entity(entity, norm_map, overlay_aliases):
        out = copy.deepcopy(entity)
        out["entity_name"] = str(entity["entity_name"]).strip()
        return out

    return _fake_normalize_entity


@pytest.fixture(scope="module")
def fake_get_entity_role():
    def _fake_get_entity_role(entity, norm_map):
        return "primary"

    return _fake_get_entity_role


@pytest.fixture(scope="module")
def fake_should_skip():
    def _fake_should_skip(entity_type, canonical_name, role):
        return canonical_name.lower() == "skipme"

    return _fake_should_skip


def test_normalize_confidence_unknown_to_low() -> None:
    assert normalize_confidence("unknown") == "low"
    assert normalize_confidence("med") == "med"


def test_safe_confidence_boost_high_is_sticky() -> None:
    assert safe_confidence_boost("material:concrete", "high") == "high"


def test_safe_confidence_boost_domain_context_to_high() -> None:
    entities = "material:concrete; test_method:load test"
    boosted = safe_confidence_boost(
        entities,
        "low",
        domain_id="construction_science",
        sentence_l="field trial with load test under environmental exposure",
    )
    assert boosted == "high"


def test_safe_confidence_boost_malformed_entity_logs_warning(caplog) -> None:
    boosted = safe_confidence_boost("bad-entry", "low", domain_id="construction_science")
    assert boosted == "low"
    assert "Malformed entity entry" in caplog.text


def test_safe_confidence_boost_high_value_without_assay_to_med() -> None:
    boosted = safe_confidence_boost("material:steel", "low", domain_id="construction_science")
    assert boosted == "med"


def test_domain_enforcement_known_and_unknown_domains() -> None:
    assert is_entity_type_allowed_for_domain("material", "construction_science") is True
    assert is_entity_type_allowed_for_domain("pathway", "construction_science") is False
    assert is_entity_type_allowed_for_domain("anything", "unknown_domain") is True


def test_filter_entities_for_domain_filters_only_disallowed(capsys) -> None:
    entities = [
        {"entity_type": "material", "entity_name": "concrete"},
        {"entity_type": "pathway", "entity_name": "wnt"},
    ]
    filtered = filter_entities_for_domain(entities, "construction_science")
    assert filtered == [{"entity_type": "material", "entity_name": "concrete"}]
    captured = capsys.readouterr()
    assert "Filtering out entity type 'pathway'" in captured.out


def test_get_contaminated_entity_types_for_unknown_domain_is_empty() -> None:
    assert get_contaminated_entity_types("unknown_domain") == set()


def test_normalize_entity_type_global_and_domain_mappings() -> None:
    assert normalize_entity_type("neuron", "target", "drug_discovery") == "neural_cell"
    assert normalize_entity_type("concrete", "target", "construction_science") == "material"
    assert normalize_entity_type("unmapped", "target", "construction_science") == "target"


def test_build_canonical_entities_dedupes_and_maps_ids(
    fake_normalize_entity,
    fake_get_entity_role,
    fake_should_skip,
) -> None:
    entities = [
        {"entity_id": "a", "entity_type": "target", "entity_name": "Neuron"},
        {"entity_id": "b", "entity_type": "target", "entity_name": "neuron"},
        {"entity_id": "skip", "entity_type": "target", "entity_name": "skipme"},
        "not-a-dict",
        {"entity_id": "missing_type", "entity_name": "x"},
    ]

    canonical_entities, mapping = build_canonical_entities(
        entities,
        domain_id="drug_discovery",
        norm_map={},
        overlay_aliases={},
        normalize_entity=fake_normalize_entity,
        get_entity_role=fake_get_entity_role,
        should_skip_entity=fake_should_skip,
    )

    assert len(canonical_entities) == 1
    assert canonical_entities[0]["entity_type"] == "neural_cell"
    assert canonical_entities[0]["entity_name"] in {"Neuron", "neuron"}
    assert set(canonical_entities[0]["original_names"]) == {"Neuron", "neuron"}
    assert mapping == {"a": "neural_cell:neuron", "b": "neural_cell:neuron"}


def test_build_canonical_entities_skips_invalid_normalized_payload() -> None:
    entities = [{"entity_id": "x", "entity_type": "target", "entity_name": "good"}]

    def bad_normalize_entity(entity, norm_map, overlay_aliases):
        return None

    canonical_entities, mapping = build_canonical_entities(
        entities,
        domain_id="drug_discovery",
        norm_map={},
        overlay_aliases={},
        normalize_entity=bad_normalize_entity,
        get_entity_role=lambda e, n: None,
        should_skip_entity=lambda t, n, r: False,
    )

    assert canonical_entities == []
    assert mapping == {}


def test_build_canonical_entities_handles_sqlite_rows(
    fake_normalize_entity: Callable[..., Any],
    fake_get_entity_role: Callable[..., Any],
    fake_should_skip: Callable[..., Any],
) -> None:
    with sqlite3.connect(":memory:") as con:
        con.row_factory = sqlite3.Row
        con.execute(
            "CREATE TABLE entities (entity_id TEXT, entity_type TEXT, entity_name TEXT, entity_variant TEXT)"
        )
        con.execute(
            "INSERT INTO entities VALUES (?, ?, ?, ?)",
            ("a", "target", "Neuron", None),
        )
        row = con.execute("SELECT * FROM entities").fetchone()

    canonical_entities, mapping = build_canonical_entities(
        [row],
        domain_id="drug_discovery",
        norm_map={},
        overlay_aliases={},
        normalize_entity=fake_normalize_entity,
        get_entity_role=fake_get_entity_role,
        should_skip_entity=fake_should_skip,
    )

    assert len(canonical_entities) == 1
    assert mapping == {"a": "neural_cell:neuron"}


def test_build_canonical_entities_filters_fragment_like_names(
    fake_get_entity_role: Callable[..., Any],
    fake_should_skip: Callable[..., Any],
) -> None:
    entities = [
        {"entity_id": "x1", "entity_type": "target", "entity_name": "a failure"},
        {"entity_id": "x2", "entity_type": "target", "entity_name": "explain failure"},
        {"entity_id": "x3", "entity_type": "target", "entity_name": "structural collapse"},
        {"entity_id": "x4", "entity_type": "target", "entity_name": "the collapse"},
    ]

    canonical_entities, mapping = build_canonical_entities(
        entities,
        domain_id="drug_discovery",
        norm_map={},
        overlay_aliases={},
        normalize_entity=lambda entity, norm_map, overlay_aliases: {**entity, "entity_name": entity["entity_name"].strip()},
        get_entity_role=fake_get_entity_role,
        should_skip_entity=fake_should_skip,
    )

    assert len(canonical_entities) == 1
    assert canonical_entities[0]["entity_name"] == "structural collapse"
    assert mapping == {"x3": "target:structural collapse"}


def test_build_canonical_entities_skips_punctuation_only_names(
    fake_get_entity_role: Callable[..., Any],
    fake_should_skip: Callable[..., Any],
) -> None:
    entities = [
        {"entity_id": "x1", "entity_type": "target", "entity_name": "]"},
        {"entity_id": "x2", "entity_type": "target", "entity_name": "!!!"},
    ]

    canonical_entities, mapping = build_canonical_entities(
        entities,
        domain_id="drug_discovery",
        norm_map={},
        overlay_aliases={},
        normalize_entity=lambda entity, norm_map, overlay_aliases: {**entity, "entity_name": entity["entity_name"].strip()},
        get_entity_role=fake_get_entity_role,
        should_skip_entity=fake_should_skip,
    )

    assert canonical_entities == []
    assert mapping == {}


def test_build_canonical_entities_skips_construction_model_noise(
    fake_normalize_entity,
    fake_get_entity_role: Callable[..., Any],
    fake_should_skip: Callable[..., Any],
) -> None:
    entities = [
        {"entity_id": "m1", "entity_type": "model", "entity_name": "human"},
        {"entity_id": "m2", "entity_type": "model", "entity_name": "mouse"},
        {"entity_id": "m3", "entity_type": "model", "entity_name": "building model"},
    ]

    canonical_entities, mapping = build_canonical_entities(
        entities,
        domain_id="construction_science",
        norm_map={},
        overlay_aliases={},
        normalize_entity=fake_normalize_entity,
        get_entity_role=fake_get_entity_role,
        should_skip_entity=fake_should_skip,
    )

    assert len(canonical_entities) == 1
    assert canonical_entities[0]["entity_name"] == "building model"
    assert mapping == {"m3": "model:building model"}
