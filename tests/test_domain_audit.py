import pytest
from types import SimpleNamespace

from utils.domain_audit import _resolve_seed_file, audit_domains, audit_feeds
from utils.domain_audit import audit_domain
from utils.entities import extract_entities
from utils.run_engine import main as run_engine_main


def test_construction_science_does_not_emit_biomedical_entity_types():
    sentence = "Concrete wall moisture failure and vapor control were discussed alongside aspirin and EGFR."

    entity_types = {entity["entity_type"] for entity in extract_entities(sentence, "construction_science")}

    assert entity_types.isdisjoint({"peptide", "compound", "target", "stem_cell"})


def test_drug_discovery_can_emit_compound_and_target(monkeypatch):
    monkeypatch.setattr("utils.entities.get_compound_seeds", lambda _seeds_dir=None: {"ASPIRIN"})
    monkeypatch.setattr("utils.entities.get_target_seeds", lambda _seeds_dir=None: {"EGFR"})
    monkeypatch.setattr("utils.entities.get_model_seeds", lambda _seeds_dir=None: set())

    entities = extract_entities("Aspirin binds EGFR.", "drug_discovery")
    entity_types = {entity["entity_type"] for entity in entities}

    assert {"compound", "target"}.issubset(entity_types)


def test_audit_domains_reports_current_domain_and_lens_layout():
    report = audit_domains()
    domain_ids = {entry.domain_id for entry in report.domains}

    assert domain_ids == {
        "biohacking_longevity",
        "construction_science",
        "drug_discovery",
        "methods_tooling",
        "neuroscience_cognition",
        "stem_cells_regen",
    }

    construction = next(entry for entry in report.domains if entry.domain_id == "construction_science")
    assert set(construction.construction_lenses) == {"building_physics", "climate", "compliance", "failure", "materials"}
    assert construction.preferred_types_not_allowed == []
    assert construction.biomedical_leakage == []
    assert report.issues == []


def test_invalid_domain_fails_clearly(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    output_db = tmp_path / "test_output.sqlite"

    with pytest.raises(SystemExit, match=r"Unknown domain 'not_a_real_domain'"):
        run_engine_main(domain="not_a_real_domain", input_dir=str(input_dir), db_path=str(output_db))


def test_feeds_reference_valid_domains():
    feeds = audit_feeds()
    assert feeds
    assert all(feed.domain_config_exists for feed in feeds)


def test_audit_domain_uses_custom_banned_entity_map(tmp_path, monkeypatch):
    domains_dir = tmp_path / "domains"
    overlays_dir = tmp_path / "overlays"
    seeds_dir = tmp_path / "seeds"
    domains_dir.mkdir()
    overlays_dir.mkdir()
    seeds_dir.mkdir()
    (domains_dir / "custom_domain.json").write_text(
        '{"id": "custom_domain", "name": "Custom", "description": "Test"}',
        encoding="utf-8",
    )

    profile = SimpleNamespace(
        name="Custom",
        overlays=[],
        get_preferred_entity_types=lambda: ["compound", "material"],
        get_seed_files=lambda: [],
    )
    monkeypatch.setattr("utils.domain_audit.load_domain_profile", lambda _path: profile)

    entry = audit_domain(
        "custom_domain",
        domains_dir=domains_dir,
        overlays_dir=overlays_dir,
        seeds_dir=seeds_dir,
        domain_banned_entity_map={"custom_domain": {"compound"}},
    )

    assert entry.biomedical_leakage == ["compound"]


def test_resolve_seed_file_prefers_exact_candidate(tmp_path):
    seeds_dir = tmp_path / "seeds"
    seeds_dir.mkdir()
    exact = seeds_dir / "seed.json"
    exact.write_text("{}", encoding="utf-8")

    assert _resolve_seed_file("seed.json", seeds_dir, "custom_domain") == exact


def test_resolve_seed_file_falls_back_to_domain_base(tmp_path):
    seeds_dir = tmp_path / "seeds"
    target = seeds_dir / "base" / "custom_domain" / "seed.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")

    assert _resolve_seed_file("seed.json", seeds_dir, "custom_domain") == target


def test_resolve_seed_file_falls_back_to_life_sciences_base(tmp_path):
    seeds_dir = tmp_path / "seeds"
    target = seeds_dir / "base" / "life_sciences" / "seed.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")

    assert _resolve_seed_file("seed.json", seeds_dir, "custom_domain") == target


def test_resolve_seed_file_supports_alternate_extensions(tmp_path):
    seeds_dir = tmp_path / "seeds"
    top_level_json = seeds_dir / "seed.json"
    top_level_json.parent.mkdir(parents=True)
    top_level_json.write_text("{}", encoding="utf-8")

    base_txt = seeds_dir / "base" / "custom_domain" / "other.txt"
    base_txt.parent.mkdir(parents=True)
    base_txt.write_text("[]", encoding="utf-8")

    assert _resolve_seed_file("seed.txt", seeds_dir, "custom_domain") == top_level_json
    assert _resolve_seed_file("other.json", seeds_dir, "custom_domain") == base_txt


def test_resolve_seed_file_skips_base_fallback_when_seed_file_contains_base_path(tmp_path):
    seeds_dir = tmp_path / "seeds"
    fallback = seeds_dir / "base" / "custom_domain" / "seed.json"
    fallback.parent.mkdir(parents=True)
    fallback.write_text("{}", encoding="utf-8")

    assert _resolve_seed_file("base/seed.txt", seeds_dir, "custom_domain") is None


def test_resolve_seed_file_returns_none_and_logs_attempts(tmp_path, caplog):
    seeds_dir = tmp_path / "seeds"
    seeds_dir.mkdir()

    with caplog.at_level("WARNING"):
        resolved = _resolve_seed_file("missing.json", seeds_dir, "custom_domain")

    assert resolved is None
    assert any("attempted candidates" in record.message for record in caplog.records)
