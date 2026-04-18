import json
import pytest
from utils import axon_domains

def make_profile(**kwargs):
    defaults = dict(
        id="testid",
        name="Test Domain",
        description="desc",
        claims_mode="observational_only",
        domain_profile_version="v1",
        seed_overlays={"prefer_types": ["gene"], "include_files": ["file1.json"]},
        exclusions={"terms": ["foo", "bar baz"]},
        pattern_emphasis={"convergence": 1.2},
        language={"allowed": ["en"], "forbidden": ["badword"]},
        output_allowed_phrases=["ok"]
    )
    defaults.update(kwargs)
    return axon_domains.DomainProfile(**defaults)

def test_get_output_allowed_phrases():
    prof = make_profile(output_allowed_phrases=["a", "b"])
    assert prof.get_output_allowed_phrases() == ["a", "b"]
    prof = make_profile(output_allowed_phrases=[])
    assert prof.get_output_allowed_phrases() == []

def test_is_excluded_text():
    prof = make_profile(exclusions={"terms": ["foo", "bar baz"]})
    assert prof.is_excluded_text("foo")
    assert prof.is_excluded_text("something bar baz here")
    assert not prof.is_excluded_text("nothing here")
    assert not prof.is_excluded_text("")

def test_emphasize_pattern():
    prof = make_profile(pattern_emphasis={"convergence": 2.0})
    assert prof.emphasize_pattern("convergence", 10) == 20
    assert prof.emphasize_pattern("other", 10) == 10

def test_is_forbidden_language():
    prof = make_profile(language={"forbidden": ["badword", "nasty"]})
    assert prof.is_forbidden_language("this is badword")
    assert prof.is_forbidden_language("nasty stuff")
    assert not prof.is_forbidden_language("clean text")

def test_get_preferred_entity_types():
    prof = make_profile(seed_overlays={"prefer_types": ["gene", "protein"]})
    assert prof.get_preferred_entity_types() == ["gene", "protein"]
    prof = make_profile(seed_overlays={})
    assert prof.get_preferred_entity_types() == []

def test_get_seed_files():
    prof = make_profile(seed_overlays={"include_files": ["f1.json", "f2.json"]})
    assert prof.get_seed_files() == ["f1.json", "f2.json"]
    prof = make_profile(seed_overlays={})
    assert prof.get_seed_files() == []

def test_load_domain_profile(tmp_path):
    data = {
        "id": "d1",
        "name": "Domain1",
        "description": "desc",
        "seed_overlays": {},
        "exclusions": {},
        "pattern_emphasis": {},
        "language": {"allowed": [], "forbidden": []},
        "output_allowed_phrases": []
    }
    f = tmp_path / "d1.json"
    f.write_text(json.dumps(data))
    prof = axon_domains.load_domain_profile(str(f))
    assert prof.id == "d1"
    assert prof.name == "Domain1"
    assert prof.description == "desc"
    # Missing required field
    data2 = dict(data)
    del data2["id"]
    f2 = tmp_path / "d2.json"
    f2.write_text(json.dumps(data2))
    with pytest.raises(ValueError):
        axon_domains.load_domain_profile(str(f2))

def test_load_all_domains(tmp_path):
    d1 = tmp_path / "d1.json"
    d2 = tmp_path / "d2.json"
    d1.write_text(json.dumps({"id": "d1", "name": "n1", "description": "desc"}))
    d2.write_text(json.dumps({"id": "d2", "name": "n2", "description": "desc"}))
    result = axon_domains.load_all_domains(str(tmp_path))
    assert set(result.keys()) == {"d1", "d2"}
    # Duplicate id
    d3 = tmp_path / "d3.json"
    d3.write_text(json.dumps({"id": "d1", "name": "n3", "description": "desc"}))
    with pytest.raises(ValueError):
        axon_domains.load_all_domains(str(tmp_path))

def test_get_domain_by_id(tmp_path, monkeypatch):
    d1 = tmp_path / "d1.json"
    d1.write_text(json.dumps({"id": "d1", "name": "n1", "description": "desc"}))
    # Patch search dirs to only tmp_path
    monkeypatch.setattr(axon_domains, "get_domain_by_id", lambda domain_id, domains_dir=None: axon_domains.load_domain_profile(str(d1)) if domain_id == "d1" else None)
    prof = axon_domains.get_domain_by_id("d1", str(tmp_path))
    assert prof.id == "d1"
    assert axon_domains.get_domain_by_id("badid", str(tmp_path)) is None
