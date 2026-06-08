from utils import entity_utils
from utils.entity_normalizer import normalize_entity

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
    import builtins

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "utils.entity_normalizer":
            raise ImportError("forced import failure")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert entity_utils.load_overlay_aliases_safe("foo") == {}


def test_normalize_entity_coerces_non_string_overlay_aliases():
    entity = {"entity_type": "assay", "entity_name": "ms", "entity_variant": "variant"}
    normalized = normalize_entity(
        entity,
        norm_map={},
        overlay_aliases={"ms": 123, "variant": None},
    )

    assert normalized["entity_name"] == "123"
    assert normalized["entity_variant"] == "none"
