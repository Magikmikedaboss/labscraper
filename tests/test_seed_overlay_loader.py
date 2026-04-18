import pytest
import json
from utils import seed_overlay_loader

def test_load_json_valid(tmp_path):
    data = {"a": 1}
    f = tmp_path / "test.json"
    f.write_text(json.dumps(data))
    assert seed_overlay_loader.load_json(str(f)) == data

def test_load_json_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        seed_overlay_loader.load_json(str(tmp_path / "missing.json"))

def test_load_json_invalid(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json")
    with pytest.raises(ValueError):
        seed_overlay_loader.load_json(str(f))

def test_merge_seed_dict_lists():
    base = {"x": [1, 2]}
    overlay = {"x": [2, 3]}
    merged = seed_overlay_loader.merge_seed_dict(base, overlay)
    assert sorted(merged["x"]) == [1, 2, 3]

def test_merge_seed_dict_nested():
    base = {"a": {"b": [1]}}
    overlay = {"a": {"b": [2], "c": [3]}}
    merged = seed_overlay_loader.merge_seed_dict(base, overlay)
    assert sorted(merged["a"]["b"]) == [1, 2]
    assert merged["a"]["c"] == [3]

def test_load_core_seeds(tmp_path, monkeypatch):
    # Create fake seeds dir with one json and one txt
    (tmp_path / "assays.json").write_text(json.dumps(["a"]))
    (tmp_path / "compounds.txt").write_text("x\ny\n")
    monkeypatch.chdir(tmp_path)
    seeds = seed_overlay_loader.load_core_seeds("")
    assert "assays" in seeds and "compounds" in seeds
    assert seeds["assays"] == ["a"]
    assert seeds["compounds"] == ["x", "y"]

def test_load_overlay(tmp_path):
    overlay_data = {"entities": {"foo": ["bar"]}, "overlay_id": "id", "domain": "d"}
    overlays_dir = tmp_path / "overlays"
    overlays_dir.mkdir()
    f = overlays_dir / "stem_cells_overlay_v1.json"
    f.write_text(json.dumps(overlay_data))
    result = seed_overlay_loader.load_overlay("stem_cells_regen", str(overlays_dir))
    assert result["entities"]["foo"] == ["bar"]
    assert result["overlay_id"] == "id"

def test_load_seeds_with_overlay(tmp_path):
    # Core
    (tmp_path / "assays.json").write_text(json.dumps(["a"]))
    # Overlay
    overlays_dir = tmp_path / "overlays"
    overlays_dir.mkdir()
    overlay_data = {"entities": {"assays": ["b"]}, "overlay_id": "id", "domain": "d"}
    (overlays_dir / "stem_cells_overlay_v1.json").write_text(json.dumps(overlay_data))
    seeds = seed_overlay_loader.load_seeds_with_overlay("stem_cells_regen", str(tmp_path), str(overlays_dir))
    assert "assays" in seeds
    assert "b" in seeds["assays"]
    assert seeds["_overlay_id"] == "id"
    assert seeds["_overlay_domain"] == "d"

def test_get_overlay_info(tmp_path):
    overlays_dir = tmp_path / "overlays"
    overlays_dir.mkdir()
    overlay_data = {"entities": {"foo": ["bar"]}, "overlay_id": "id", "domain": "d", "notes": "n", "exclusions": {"x": 1}}
    (overlays_dir / "stem_cells_overlay_v1.json").write_text(json.dumps(overlay_data))
    info = seed_overlay_loader.get_overlay_info("stem_cells_regen", str(overlays_dir))
    assert info["overlay_id"] == "id"
    assert info["domain"] == "d"
    assert info["notes"] == "n"
    assert info["exclusions"] == {"x": 1}
    assert "foo" in info["entity_categories"]
