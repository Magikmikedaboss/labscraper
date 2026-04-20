from utils import confidence_utils, entity_utils, reporting_utils

def test_safe_confidence_boost_basic():
    # Already high
    assert confidence_utils.safe_confidence_boost("protein:TP53", "high") == "high"
    # No entities
    assert confidence_utils.safe_confidence_boost("", "med") == "med"
    # Normalization
    assert confidence_utils.safe_confidence_boost("", "medium") == "med"
    # Unknown confidence
    assert confidence_utils.safe_confidence_boost("", "foo") == "other"

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
    # Create minimal normalization.json
    seeds_dir = tmp_path / "seeds"
    seeds_dir.mkdir()
    norm_path = seeds_dir / "normalization.json"
    norm_path.write_text("{}", encoding="utf-8")

    # Monkeypatch load_normalization_map to use our temp file
    import utils.entity_normalizer as entity_normalizer_mod
    orig_load_normalization_map = entity_normalizer_mod.load_normalization_map
    _sentinel = object()
    def wrapper(path=_sentinel):
        if path is _sentinel:
            return orig_load_normalization_map(str(norm_path))
        return orig_load_normalization_map(path)
    monkeypatch.setattr(entity_normalizer_mod, "load_normalization_map", wrapper)

    confidence_changes = {"high": 1, "med": 0, "low": 0, "other": 0}
    canonical_entities = {("protein", "TP53"): {"event_count": 1, "paper_ids": {1}, "original_names": {"TP53"}, "entity_name": "TP53", "role": "primary"}}
    reporting_utils.write_run_meta(confidence_changes, canonical_entities, domain_id=None, output_dir=tmp_path)    # Should create a file in tmp_path


    # Assert the exact expected output path
    expected_path = tmp_path / "output" / "run_meta.json"
    assert expected_path.exists()


