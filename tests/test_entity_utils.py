from utils import entity_utils

def test_count_entities_by_role_basic():
    s = "protein:TP53; cell:HeLa"
    norm_map = {}
    result = entity_utils.count_entities_by_role(s, norm_map)
    # Explicitly check each result element and both entity identifiers regardless of order
    assert result[0] == 1  # primary count
    assert result[1] == 1  # context count
    # result[2] is primary_str, result[3] is context_str
    assert result[2] == "protein:TP53"
    assert result[3] == "cell:HeLa"

def test_count_entities_by_role_empty():
    result = entity_utils.count_entities_by_role("", {})
    assert result == (0, 0, "", "", "")

def test_count_entities_by_role_process_word(monkeypatch):
    # Patch is_process_word to always True
    monkeypatch.setattr(entity_utils, "is_process_word", lambda x: True)
    s = "assay:run"
    norm_map = {}
    result = entity_utils.count_entities_by_role(s, norm_map)
    assert result[1] == 1  # context count

def test_load_overlay_aliases_safe_none():
    assert entity_utils.load_overlay_aliases_safe() == {}

def test_load_overlay_aliases_safe_importerror(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "utils.entity_normalizer", None)
    # Should not raise, should return {}
    assert entity_utils.load_overlay_aliases_safe("foo") == {}
