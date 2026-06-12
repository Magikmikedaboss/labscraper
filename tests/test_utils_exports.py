import json
from utils import confidence_utils, entity_utils, reporting_utils

def test_safe_confidence_boost_basic():
    # Already high
    assert confidence_utils.safe_confidence_boost("protein:TP53", "high") == "high"
    # No entities
    assert confidence_utils.safe_confidence_boost("", "med") == "med"
    # Normalization
    assert confidence_utils.safe_confidence_boost("", "medium") == "med"
    # Unknown confidence
    assert confidence_utils.safe_confidence_boost("", "foo") == "low"

def test_count_entities_by_role_basic():
    norm_map = {}
    overlay_aliases = {}
    # No entities
    assert entity_utils.count_entities_by_role("", norm_map, overlay_aliases) == (0, 0, "", "", "")
    # One primary, one context
    s = "protein:TP53; assay:ELISA"
    primary, context, primary_str, context_str, all_str = entity_utils.count_entities_by_role(s, norm_map, overlay_aliases)
    assert primary + context == 2
    assert "protein:TP53" in all_str and "assay:ELISA" in all_str

def test_load_overlay_aliases_safe():
    # Should not raise, returns dict
    aliases = entity_utils.load_overlay_aliases_safe()
    assert isinstance(aliases, dict)

def test_write_run_meta(tmp_path, monkeypatch):
    # Minimal smoke test for write_run_meta
    # Monkeypatch load_normalization_map to a deterministic map
    import utils.entity_normalizer as entity_normalizer_mod
    deterministic_norm_map = {"your_normalized_key": "value"}
    monkeypatch.setattr(
        entity_normalizer_mod,
        "load_normalization_map",
        lambda path=None: deterministic_norm_map,
    )
    monkeypatch.setattr(
        reporting_utils,
        "load_normalization_map",
        lambda path=None: deterministic_norm_map,
    )

    confidence_changes = {"high": 1, "med": 0, "low": 0, "other": 0}
    canonical_entities = {("protein", "TP53"): {"event_count": 1, "paper_ids": {1}, "original_names": {"TP53"}, "entity_name": "TP53", "role": "primary"}}
    reporting_utils.write_run_meta(confidence_changes, canonical_entities, domain_id=None, output_dir=tmp_path)

    # Assert the exact expected output path
    expected_path = tmp_path / "run_meta.json"
    assert expected_path.exists()
    # Assert the written JSON has expected structure and normalization_map was used
    with expected_path.open(encoding="utf-8") as f:
        meta = json.load(f)
    assert "run_id" in meta
    assert "engine_version" in meta
    assert "timestamp" in meta
    assert "seeds_version" in meta
    assert "counts" in meta and isinstance(meta["counts"], dict)
    assert "confidence_distribution" in meta and isinstance(meta["confidence_distribution"], dict)
    assert "top_entities" in meta and isinstance(meta["top_entities"], list)
    assert meta["normalization_map"] == deterministic_norm_map


def test_get_overlay_version_branches():
    class Domain:
        pass

    assert reporting_utils.get_overlay_version(None) == "v1"

    domain = Domain()
    domain.overlay_version = "v2"
    assert reporting_utils.get_overlay_version(domain) == "v2"

    domain = Domain()
    domain.metadata = {"overlay_version": "v3"}
    assert reporting_utils.get_overlay_version(domain) == "v3"

    domain = Domain()
    domain.domain_profile_version = "v4"
    assert reporting_utils.get_overlay_version(domain) == "v4"


def test_get_overlay_version_precedence():
    class Domain:
        pass

    domain = Domain()
    domain.overlay_version = "overlay-v2"
    domain.metadata = {"overlay_version": "metadata-v3"}
    domain.domain_profile_version = "profile-v4"

    assert reporting_utils.get_overlay_version(domain) == "overlay-v2"

    del domain.overlay_version
    assert reporting_utils.get_overlay_version(domain) == "metadata-v3"

    domain.metadata = {}
    assert reporting_utils.get_overlay_version(domain) == "profile-v4"


