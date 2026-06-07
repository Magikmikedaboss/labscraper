from utils import entity_utils

def test_count_entities_by_role_basic():
    s = "protein:TP53; cell:HeLa"
    norm_map = {}
    primary_count, context_count, primary_str, context_str, all_str = entity_utils.count_entities_by_role(s, norm_map)
    assert primary_count == 1
    assert context_count == 1
    assert primary_str == "protein:TP53"
    assert context_str == "cell:HeLa"

def test_count_entities_by_role_empty():
    result = entity_utils.count_entities_by_role("", {})
    assert len(result) == 5
    primary_count, context_count, primary_str, context_str, all_str = result
    assert primary_count == 0
    assert context_count == 0
    assert primary_str == ""
    assert context_str == ""
    assert all_str == ""

def test_count_entities_by_role_process_word(monkeypatch):
    # Patch is_process_word to always True
    monkeypatch.setattr(entity_utils, "is_process_word", lambda x: True)
    s = "assay:run"
    norm_map = {}
    _, context_count, _, _, _ = entity_utils.count_entities_by_role(s, norm_map)
    assert context_count == 1

def test_load_overlay_aliases_safe_none():
    assert entity_utils.load_overlay_aliases_safe() == {}

def test_load_overlay_aliases_safe_importerror(monkeypatch):
    import sys
    monkeypatch.delitem(sys.modules, "utils.entity_normalizer", raising=False)
    # Should not raise, should return {}
    assert entity_utils.load_overlay_aliases_safe("foo") == {}
