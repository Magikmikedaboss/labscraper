from utils.fallback_entity_classifier import (
    CandidateEntity,
    FallbackEntityClassifier,
    apply_fallback_classification,
)


def test_normalize_domain_variants() -> None:
    clf = FallbackEntityClassifier(domain="construction_science")
    assert clf.normalize_domain() == "construction"
    assert clf.normalize_domain("biomedical_science") == "biomedical"
    assert clf.normalize_domain("methods_tooling") == "methodstooling"


def test_extract_candidate_entities_contains_pattern_and_code() -> None:
    clf = FallbackEntityClassifier(domain="construction_science")
    text = "The high-strength concrete beam with code ABC123 failed."

    candidates = clf.extract_candidate_entities(text)

    texts = {c.text.lower() for c in candidates}
    sources = {c.source for c in candidates}
    assert any("high-strength concrete" in t for t in texts)
    assert "abc123" in texts
    assert "alphanumeric_code" in sources


def test_extract_capitalized_phrase_filters_non_entity() -> None:
    clf = FallbackEntityClassifier(domain="construction")
    text = "The Study Analysis result and New York"
    candidates = clf._extract_capitalized_phrases(text)
    extracted = [c.text for c in candidates]
    assert "New York" in extracted
    assert "Study Analysis" not in extracted


def test_classify_entity_type_none_for_unknown_domain() -> None:
    clf = FallbackEntityClassifier(domain="unknown_domain")
    assert clf._classify_entity_type("concrete", "concrete in beam") is None


def test_classify_entity_type_by_context_and_patterns() -> None:
    clf = FallbackEntityClassifier(domain="construction_science")
    context = "concrete beam in structure with load"
    # Context-based rules can return whichever category reaches the threshold first.
    assert clf._classify_entity_type("concrete", context) in {
        "material_keywords",
        "system_keywords",
    }
    assert clf._classify_entity_type("structural failure", context) is not None


def test_classify_candidates_maps_positions() -> None:
    clf = FallbackEntityClassifier(domain="construction_science")
    cands = [
        CandidateEntity(text="structural failure", start_pos=2, end_pos=20, confidence=0.6, source="x"),
        CandidateEntity(text="nonsense", start_pos=11, end_pos=19, confidence=0.3, source="x"),
    ]
    classified = clf.classify_candidates(cands, "structural failure in concrete beam")
    assert len(classified) == 1
    assert classified[0]["entity_name"] == "structural failure"
    assert classified[0]["position"] == (2, 20)


def test_apply_fallback_classification_dedupes_and_sorts() -> None:
    clf = FallbackEntityClassifier(domain="construction_science")
    text = "high-strength concrete beam and ABC123"
    existing = [{"entity_name": "ABC123", "entity_type": "code", "confidence": 0.95}]

    out = clf.apply_fallback_classification(text, existing)

    assert out[0]["confidence"] >= out[-1]["confidence"]
    names_lower = [e["entity_name"].lower() for e in out]
    assert names_lower.count("abc123") == 1


def test_get_coverage_improvement_metrics() -> None:
    clf = FallbackEntityClassifier()
    original = [{"entity_type": "material", "entity_name": "concrete"}]
    enhanced = [
        {"entity_type": "material", "entity_name": "concrete"},
        {"entity_type": "system", "entity_name": "beam"},
    ]
    metrics = clf.get_coverage_improvement(original, enhanced)
    assert metrics["original_count"] == 1
    assert metrics["enhanced_count"] == 2
    assert metrics["new_entities"] == 1
    assert metrics["coverage_improvement"] == 100.0
    assert "system" in metrics["new_types"]


def test_backward_compat_apply_function(monkeypatch) -> None:
    class DummyClassifier:
        def __init__(self, domain):
            self.domain = domain

        def apply_fallback_classification(self, text, existing_entities):
            return [{"entity_name": "ok", "entity_type": "material", "confidence": 0.5}]

    import utils.fallback_entity_classifier as mod

    monkeypatch.setattr(mod, "FallbackEntityClassifier", DummyClassifier)
    out = apply_fallback_classification("text", [], domain="construction_science")
    assert out[0]["entity_name"] == "ok"


def test_init_loads_seed_containers() -> None:
    clf = FallbackEntityClassifier(domain="construction_science")
    assert isinstance(clf.seeds, dict)
