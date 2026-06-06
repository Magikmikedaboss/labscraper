import copy

from utils.confidence_utils import normalize_confidence, safe_confidence_boost
from utils.domain_enforcement import (
    filter_entities_for_domain,
    get_contaminated_entity_types,
    is_entity_type_allowed_for_domain,
)
from utils.export.normalization import build_canonical_entities, normalize_entity_type


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


def test_build_canonical_entities_dedupes_and_maps_ids() -> None:
    entities = [
        {"entity_id": "a", "entity_type": "target", "entity_name": "Neuron"},
        {"entity_id": "b", "entity_type": "target", "entity_name": "neuron"},
        {"entity_id": "skip", "entity_type": "target", "entity_name": "skipme"},
        "not-a-dict",
        {"entity_id": "missing_type", "entity_name": "x"},
    ]

    def fake_normalize_entity(entity, norm_map, overlay_aliases):
        out = copy.deepcopy(entity)
        out["entity_name"] = str(entity["entity_name"]).strip()
        return out

    def fake_get_entity_role(entity, norm_map):
        return "primary"

    def fake_should_skip(entity_type, canonical_name, role):
        return canonical_name.lower() == "skipme"

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
