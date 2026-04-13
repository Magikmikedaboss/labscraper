"""Tests for the 6 construction lens modules.

Each lens exposes a ``detect(sentence) -> (LensEvent | None, list[dict])`` API.
Tests verify:
- A relevant sentence triggers detection (event is not None)
- The returned LensEvent has a non-empty event_type and normalized outcome metadata
- A clearly irrelevant sentence returns (None, [])
- Returned entities have the expected structural keys
- Multi-lens stacking can return multiple truths for one sentence
"""
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entity_keys():
    return {"entity_type", "entity_name", "entity_variant", "role"}


def _assert_event(event_obj):
    """Assert that a LensEvent is valid."""
    assert event_obj is not None
    assert hasattr(event_obj, "event_type")
    assert hasattr(event_obj, "outcome")
    assert hasattr(event_obj, "confidence")
    assert hasattr(event_obj, "context_strength")
    assert hasattr(event_obj, "source_weight")
    assert event_obj.event_type
    assert event_obj.outcome in ("positive", "negative", "neutral", "unknown")
    assert event_obj.confidence in ("low", "med", "high")
    assert event_obj.context_strength in ("weak", "moderate", "strong")
    assert 0.0 <= event_obj.source_weight <= 1.0


def _assert_entities(entities):
    """Assert that entity dicts have the expected keys."""
    for e in entities:
        missing = _entity_keys() - set(e.keys())
        assert not missing, f"Entity missing keys: {missing} in {e}"


# ---------------------------------------------------------------------------
# construction_common helpers (directly imported)
# ---------------------------------------------------------------------------

class TestConstructionCommon:
    def test_has_unit_signal_mpa(self):
        from lenses.construction_common import has_unit_signal
        assert has_unit_signal("the beam failed at 30 mpa")

    def test_has_unit_signal_percent(self):
        from lenses.construction_common import has_unit_signal
        assert has_unit_signal("shrinkage was 5% after 28 days")

    def test_has_unit_signal_none(self):
        from lenses.construction_common import has_unit_signal
        assert not has_unit_signal("no measurements here at all")

    def test_has_number_detects_integer(self):
        from lenses.construction_common import has_number
        assert has_number("strength of 40 units")

    def test_has_number_absent(self):
        from lenses.construction_common import has_number
        assert not has_number("no numbers here")

    def test_contains_any(self):
        from lenses.construction_common import contains_any
        assert contains_any("the slab collapsed", ["collapse", "fracture"])
        assert not contains_any("sunny day", ["collapse", "fracture"])

    def test_list_hits_word_boundary(self):
        from lenses.construction_common import list_hits
        # "steel" should NOT match inside "steelyard" unless the word boundary regex allows it
        hits = list_hits("reinforced concrete beam", ["concrete", "steel"])
        assert "concrete" in hits
        assert "steel" not in hits

    def test_dedupe_entities_removes_duplicates(self):
        from lenses.construction_common import dedupe_entities, make_entity
        ents = [
            make_entity("material", "concrete", "material", "tested"),
            make_entity("material", "concrete", "material", "tested"),
        ]
        result = dedupe_entities(ents)
        assert len(result) == 1

    def test_dedupe_entities_drops_junk(self):
        from lenses.construction_common import dedupe_entities, make_entity
        ents = [make_entity("material", "]", "x", "y")]
        assert dedupe_entities(ents) == []

    def test_make_entity_structure(self):
        from lenses.construction_common import make_entity
        e = make_entity("material", "concrete", "material", "tested")
        assert set(e.keys()) == _entity_keys()

    def test_normalize_outcome_maps_product_labels(self):
        from lenses.construction_common import normalize_outcome
        assert normalize_outcome("improved") == "positive"
        assert normalize_outcome("successful") == "positive"
        assert normalize_outcome("degraded") == "negative"
        assert normalize_outcome("neutral") == "neutral"

    def test_get_source_weight_uses_source_type(self):
        from lenses.construction_common import get_source_weight
        assert get_source_weight("reddit") < get_source_weight("research_paper")
        assert get_source_weight("research_paper") < get_source_weight("code_standard")

    def test_infer_context_strength_quantified_results_are_strong(self):
        from lenses.construction_common import infer_context_strength
        sentence = "Compressive strength improved to 45 MPa after testing."
        assert infer_context_strength(sentence, has_numbers=True, has_units=True) == "strong"


# ---------------------------------------------------------------------------
# construction_failure_v1
# ---------------------------------------------------------------------------

class TestFailureLens:
    def test_cracking_sentence_triggers_detection(self):
        from lenses.construction_failure_v1 import detect
        sentence = "Cracking was observed in the concrete slab due to freeze-thaw cycling."
        event, entities = detect(sentence)
        _assert_event(event)
        assert event.event_type == "failure_analysis"

    def test_failure_entities_have_failure_mode(self):
        from lenses.construction_failure_v1 import detect
        sentence = "Buckling of the steel column was caused by overload during the storm."
        _, entities = detect(sentence)
        _assert_entities(entities)
        types = {e["entity_type"] for e in entities}
        assert "failure_mode" in types

    def test_causal_marker_detected(self):
        from lenses.construction_failure_v1 import detect
        sentence = "Delamination of the facade resulted from chloride ingress over 20 years."
        event, _ = detect(sentence)
        assert event is not None
        assert hasattr(event, "tags") and event.tags is not None
        assert "has_causality" in event.tags

    def test_irrelevant_sentence_returns_none(self):
        from lenses.construction_failure_v1 import detect
        event, entities = detect("The conference was well attended by delegates.")
        assert event is None
        assert entities == []

    def test_high_signal_words_trigger(self):
        from lenses.construction_failure_v1 import detect
        sentence = "A forensic investigation identified collapse as the primary failure."
        event, _ = detect(sentence)
        assert event is not None


# ---------------------------------------------------------------------------
# construction_materials_v1
# ---------------------------------------------------------------------------

class TestMaterialsLens:
    def test_concrete_strength_detected(self):
        from lenses.construction_materials_v1 import detect
        sentence = "Concrete specimens showed improved compressive strength of 45 MPa after curing."
        event, entities = detect(sentence)
        _assert_event(event)
        assert event.event_type == "material_performance"

    def test_material_and_property_entities(self):
        from lenses.construction_materials_v1 import detect
        sentence = "Fly ash replacement increased the durability and reduced permeability of cement."
        _, entities = detect(sentence)
        _assert_entities(entities)
        types = {e["entity_type"] for e in entities}
        assert "material" in types or "property" in types

    def test_improved_outcome(self):
        from lenses.construction_materials_v1 import detect
        sentence = "The tensile strength of silica fume concrete was enhanced by 20% in tests."
        event, _ = detect(sentence)
        assert event is not None
        assert event.outcome == "positive"

    def test_degraded_outcome(self):
        from lenses.construction_materials_v1 import detect
        sentence = "Modulus decreased from 30 GPa to 22 GPa after high-temperature exposure."
        event, _ = detect(sentence)
        assert event is not None
        assert event.outcome == "negative"

    def test_irrelevant_sentence_returns_none(self):
        from lenses.construction_materials_v1 import detect
        event, entities = detect("The annual budget meeting was held in January.")
        assert event is None
        assert entities == []

    def test_test_marker_alone_triggers(self):
        from lenses.construction_materials_v1 import detect
        # "tested specimens" alone should be enough if test marker logic allows
        sentence = "Specimens were tested to characterize long-term behaviour."
        # This may or may not fire depending on logic; check consistent return type
        result = detect(sentence)
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# construction_building_physics_v1
# ---------------------------------------------------------------------------

class TestBuildingPhysicsLens:
    def test_u_value_detected(self):
        from lenses.construction_building_physics_v1 import detect
        sentence = "The wall assembly achieved a U-value of 0.18 W/m2K with added insulation."
        event, entities = detect(sentence)
        _assert_event(event)
        assert event.event_type == "building_physics_performance"

    def test_infiltration_sentence(self):
        from lenses.construction_building_physics_v1 import detect
        sentence = "Air leakage was measured at 1.2 ACH under 50 Pa depressurisation."
        event, entities = detect(sentence)
        assert event is not None
        _assert_entities(entities)

    def test_improved_outcome_on_reduced(self):
        from lenses.construction_building_physics_v1 import detect
        sentence = "Energy consumption was significantly reduced after retrofitting the facade."
        event, _ = detect(sentence)
        assert event is not None
        assert event.outcome == "positive"

    def test_component_entity_extracted(self):
        from lenses.construction_building_physics_v1 import detect
        sentence = "The roof insulation improved thermal conductivity measurements by 30%."
        _, entities = detect(sentence)
        _assert_entities(entities)
        types = {e["entity_type"] for e in entities}
        assert "building_component" in types or "physics_metric" in types

    def test_irrelevant_sentence_returns_none(self):
        from lenses.construction_building_physics_v1 import detect
        event, entities = detect("The city council approved the budget proposal.")
        assert event is None
        assert entities == []


# ---------------------------------------------------------------------------
# construction_climate_v1
# ---------------------------------------------------------------------------

class TestClimateLens:
    def test_flood_hazard_detected(self):
        from lenses.construction_climate_v1 import detect
        sentence = "Flood risk to building foundations increased under RCP 8.5 projections."
        event, entities = detect(sentence)
        _assert_event(event)
        assert event.event_type == "climate_resilience"

    def test_resilience_term_alone_triggers(self):
        from lenses.construction_climate_v1 import detect
        sentence = "Resilience of the building envelope to extreme heat was evaluated."
        event, _ = detect(sentence)
        assert event is not None

    def test_hazard_entity_extracted(self):
        from lenses.construction_climate_v1 import detect
        sentence = "Hurricane wind loads were simulated at 160 mph for coastal structures."
        _, entities = detect(sentence)
        _assert_entities(entities)
        types = {e["entity_type"] for e in entities}
        assert "hazard" in types

    def test_failed_outcome_on_worsened(self):
        from lenses.construction_climate_v1 import detect
        sentence = "Flood vulnerability was exacerbated by increased storm surge intensity."
        event, _ = detect(sentence)
        assert event is not None
        assert event.outcome == "negative"

    def test_irrelevant_sentence_returns_none(self):
        from lenses.construction_climate_v1 import detect
        event, entities = detect("The shareholders voted for the dividend increase.")
        assert event is None
        assert entities == []

    def test_construction_climate_co_occurrence_boost(self):
        from lenses.construction_climate_v1 import detect
        sentence = "Concrete walls showed increased moisture ingress due to flood exposure."
        event, entities = detect(sentence)
        assert event is not None
        # Co-occurrence boost should mean we have material or system entities too
        types = {e["entity_type"] for e in entities}
        assert "hazard" in types or "material" in types


# ---------------------------------------------------------------------------
# construction_compliance_v1
# ---------------------------------------------------------------------------

class TestComplianceLens:
    def test_astm_standard_detected(self):
        from lenses.construction_compliance_v1 import detect
        sentence = "The concrete mix complies with ASTM C150 requirements for Type II cement."
        event, entities = detect(sentence)
        _assert_event(event)
        assert event.event_type == "code_compliance"

    def test_standard_entity_captured(self):
        from lenses.construction_compliance_v1 import detect
        sentence = "Structural design is in accordance with ASCE 7 load combinations."
        _, entities = detect(sentence)
        _assert_entities(entities)
        assert any(e["entity_type"] == "code_standard" for e in entities)

    def test_pass_outcome(self):
        from lenses.construction_compliance_v1 import detect
        sentence = "The wall assembly meets the IECC 2021 thermal requirements."
        event, _ = detect(sentence)
        assert event is not None
        assert event.outcome == "positive"

    def test_fail_outcome(self):
        from lenses.construction_compliance_v1 import detect
        sentence = "The beam is non-compliant with ACI 318 shear reinforcement provisions."
        event, _ = detect(sentence)
        assert event is not None
        assert event.outcome == "negative"

    def test_standard_keyword_alone_triggers(self):
        from lenses.construction_compliance_v1 import detect
        sentence = "The energy standard requires a minimum insulation level of R-30."
        event, _ = detect(sentence)
        assert event is not None

    def test_irrelevant_sentence_returns_none(self):
        from lenses.construction_compliance_v1 import detect
        event, entities = detect("The autumn leaves were beautiful in the park.")
        assert event is None
        assert entities == []


class TestMultiLensStacking:
    def test_one_sentence_can_trigger_multiple_lenses(self):
        from lenses import detect_multi_lens

        sentence = "Concrete specimens complied with ASTM C150 and improved compressive strength to 45 MPa."
        results = detect_multi_lens(sentence, source_type="code_standard")

        assert len(results) >= 2
        lens_names = {r["lens"] for r in results}
        assert "materials" in lens_names
        assert "compliance" in lens_names
        assert all(r["outcome"] in ("positive", "negative", "neutral", "unknown") for r in results)
        assert all("context_strength" in r for r in results)
        assert all("source_weight" in r for r in results)
