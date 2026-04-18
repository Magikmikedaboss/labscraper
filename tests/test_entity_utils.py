from utils import entity_utils

def test_count_entities_by_role_basic():
    s = "protein:TP53; cell:HeLa"
    norm_map = {}
    result = entity_utils.count_entities_by_role(s, norm_map)
    assert result[0] + result[1] == 2
    assert "protein:TP53" in result[2] or "cell:HeLa" in result[2] or result[4]

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
    monkeypatch.setitem(__import__("sys").modules, "entity_normalizer", None)
    # Should not raise, should return {}
    assert entity_utils.load_overlay_aliases_safe("foo") == {}
