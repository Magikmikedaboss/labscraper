
"""Tests for the 6 construction lens modules.

Each lens exposes a ``detect(sentence) -> (LensEvent | None, list[dict])`` API.
Tests verify:
- A relevant sentence triggers detection (event is not None)
- The returned LensEvent has a non-empty event_type and normalized outcome metadata
- A clearly irrelevant sentence returns (None, [])
- Returned entities have the expected structural keys
- Multi-lens stacking can return multiple truths for one sentence
"""
import logging

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


def test_detect_multi_lens_uses_configurable_rankings(monkeypatch):
    import lenses

    class _Event:
        def __init__(self, event_type, confidence, context_strength):
            self._payload = {
                "event_type": event_type,
                "outcome": "neutral",
                "confidence": confidence,
                "context_strength": context_strength,
                "source_weight": 1.0,
            }

        def as_dict(self):
            return dict(self._payload)

    def detector_a(_sentence, source_type="research_paper"):
        return _Event("a", "med", "weak"), []

    def detector_b(_sentence, source_type="research_paper"):
        return _Event("b", "high", "weak"), []

    monkeypatch.setattr(
        lenses,
        "LENS_REGISTRY",
        {"a": detector_a, "b": detector_b},
    )

    # Default ranking favors high > med.
    out_default = lenses.detect_multi_lens("x", enabled_lenses=["a", "b"])
    assert out_default[0]["event_type"] == "b"

    # Injected ranking flips priority for this call only.
    out_injected = lenses.detect_multi_lens(
        "x",
        enabled_lenses=["a", "b"],
        confidence_rank={"low": 1, "med": 10, "medium": 10, "high": 3},
    )
    assert out_injected[0]["event_type"] == "a"

    # set_rankings returns explicit maps that callers can pass through.
    confidence_rank, context_rank = lenses.set_rankings(
        confidence_rank={"low": 1, "med": 9, "medium": 9, "high": 3}
    )
    out_global = lenses.detect_multi_lens(
        "x",
        enabled_lenses=["a", "b"],
        confidence_rank=confidence_rank,
        context_rank=context_rank,
    )
    assert out_global[0]["event_type"] == "a"


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
        # "steel" should not match when only present as a substring.
        hits = list_hits("reinforced concrete steelyard beam", ["concrete", "steel"])
        assert "concrete" in hits
        assert "steel" not in hits

        # But standalone token should match.
        hits2 = list_hits("reinforced concrete and steel beam", ["concrete", "steel"])
        assert "steel" in hits2

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
        assert normalize_outcome("mixed_hazard") == "neutral"

    def test_get_source_weight_uses_source_type(self):
        from lenses.construction_common import get_source_weight
        assert get_source_weight("reddit") < get_source_weight("research_paper")
        assert get_source_weight("research_paper") < get_source_weight("code_standard")

    def test_infer_context_strength_quantified_results_are_strong(self):
        from lenses.construction_common import infer_context_strength
        sentence = "Compressive strength improved to 45 MPa after testing."
        assert infer_context_strength(sentence, has_numbers=True, has_units=True) == "strong"

    def test_has_construction_context_supports_env_override(self, monkeypatch):
        from lenses.construction_common import has_construction_context

        monkeypatch.setenv("LABSCRAPER_CONSTRUCTION_CONTEXT_TERMS", "megastructure")
        assert has_construction_context("The megastructure failed during testing.")


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
        sentence = "A forensic investigation identified collapse of the steel beam as the primary failure."
        event, _ = detect(sentence)
        assert event is not None

    def test_investigation_only_does_not_trigger(self):
        from lenses.construction_failure_v1 import detect
        sentence = "Structural investigation of the proton-coupled secondary transporters was performed."
        event, entities = detect(sentence)
        assert event is None
        assert entities == []

    def test_corrosion_resistant_does_not_trigger_failure_mode(self):
        from lenses.construction_failure_v1 import detect
        sentence = "Metal joists are corrosion resistant and lightweight."
        event, entities = detect(sentence)
        assert event is None
        assert entities == []

    def test_corrosion_damage_triggers_detection(self):
        from lenses.construction_failure_v1 import detect

        sentence = "Corrosion damage and rust were observed on the steel beam after years of exposure."
        event, entities = detect(sentence)
        _assert_event(event)
        failure_modes = [e.get("entity_name", "") for e in entities if e.get("entity_type") == "failure_mode"]
        assert any(mode == "corrosion" for mode in failure_modes)

    def test_moisture_damage_triggers_detection(self):
        from lenses.construction_failure_v1 import detect
        sentence = "Moisture damage and water intrusion were observed in the wall assembly."
        event, entities = detect(sentence)
        _assert_event(event)
        failure_modes = [e.get("entity_name", "") for e in entities if e.get("entity_type") == "failure_mode"]
        assert any("moisture damage" in mode for mode in failure_modes)

    def test_failure_vocabulary_includes_freeze_thaw_and_seismic(self):
        from lenses.construction_failure_v1 import MATERIAL_FAILURE_MODES, STRUCTURAL_FAILURE_MODES

        assert "freeze-thaw" in MATERIAL_FAILURE_MODES
        assert "seismic" in STRUCTURAL_FAILURE_MODES

    def test_beam_only_physics_sentence_returns_none(self):
        from lenses.construction_failure_v1 import detect
        sentence = "Probe beam photoelastic effect was measured in the optical setup."
        event, entities = detect(sentence)
        assert event is None
        assert entities == []

    def test_non_construction_chemistry_sentence_returns_none(self):
        from lenses.construction_failure_v1 import detect
        sentence = "Surfactant-driven transport processes were analyzed in an interfacial chemistry study."
        event, entities = detect(sentence)
        assert event is None
        assert entities == []


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

    def test_material_degradation_terms_detected(self):
        from lenses.construction_materials_v1 import detect

        sentence = "Concrete durability declined after freeze-thaw cycling, carbonation, and chloride ingress."
        event, entities = detect(sentence)
        _assert_event(event)
        assert any(e["entity_type"] == "mechanism" for e in entities)

    def test_materials_v2_terms_detected(self):
        from lenses.construction_materials_v1 import detect

        sentence = "Rebar yield strength and fatigue resistance improved in fiber reinforced polymer coatings."
        event, entities = detect(sentence)
        _assert_event(event)
        assert event.event_type == "material_performance"
        assert any(e["entity_type"] == "material" for e in entities)

    def test_materials_structural_bucket_tags(self):
        from lenses.construction_materials_v1 import detect

        sentence = "Steel rebar showed improved yield strength in the concrete beam after curing."
        event, _ = detect(sentence)
        _assert_event(event)
        assert "structural_material" in event.tags
        assert "material_property" in event.tags

    def test_materials_degradation_bucket_tags(self):
        from lenses.construction_materials_v1 import detect

        sentence = "Concrete durability declined after chloride ingress, carbonation, and spalling."
        event, _ = detect(sentence)
        _assert_event(event)
        assert "material_degradation" in event.tags

    def test_irrelevant_sentence_returns_none(self):
        from lenses.construction_materials_v1 import detect
        event, entities = detect("The annual budget meeting was held in January.")
        assert event is None
        assert entities == []

    def test_materials_ignores_marker_only_sentence(self):
        from lenses.construction_materials_v1 import detect

        sentence = "Specimens were tested to characterize long-term behaviour."
        result = detect(sentence)
        assert result == (None, [])

    def test_materials_ignores_methods_noise_without_materials(self):
        from lenses.construction_materials_v1 import detect

        sentence = "The test results showed improved permeability of the sample."
        result = detect(sentence)
        assert result == (None, [])


class TestMethodsLens:
    def test_methods_marker_alone_triggers(self):
        from lenses.construction_methods_tooling_v1 import detect

        sentence = "Specimens were tested to characterize long-term behaviour."
        event, entities = detect(sentence)
        _assert_event(event)
        assert event.event_type == "experimental_methods"
        assert any(e["entity_type"] == "method_term" for e in entities)

    def test_route_methods_sentence_keep_and_skip(self):
        from lenses.construction_methods_tooling_v1 import route_methods_tooling_sentence

        keep_decision = route_methods_tooling_sentence("Specimens were tested to characterize long-term behaviour.")
        skip_decision = route_methods_tooling_sentence("The annual budget meeting was held in January.")

        assert keep_decision.decision == "keep"
        assert keep_decision.reason == "methods signal present"
        assert skip_decision.decision == "skip"
        assert skip_decision.reason == "no methods signal present"


class TestRoutingHelpers:
    def test_route_materials_sentence_keep_and_skip(self):
        from lenses.construction_materials_v1 import route_materials_sentence

        keep_decision = route_materials_sentence("Concrete specimens showed improved compressive strength.")
        skip_decision = route_materials_sentence("The annual budget meeting was held in January.")

        assert keep_decision.decision == "keep"
        assert keep_decision.reason == "materials signal present"
        assert skip_decision.decision == "skip"
        assert skip_decision.reason == "no materials signal present"

    def test_route_climate_sentence_keep_and_skip(self):
        from lenses.construction_climate_v1 import route_climate_sentence

        keep_decision = route_climate_sentence("Flood risk to building foundations increased under projections.")
        skip_decision = route_climate_sentence("Flood risk increased under projections.")

        assert keep_decision.decision == "keep"
        assert keep_decision.reason == "climate signal in construction context"
        assert skip_decision.decision == "skip"
        assert skip_decision.reason == "no climate signal in construction context"


class TestMaterialsRouter:
    def test_route_materials_sentence_keeps_material_signal(self):
        from lenses.construction_materials_v1 import route_materials_sentence

        decision = route_materials_sentence("The concrete mix improved compressive strength.")

        assert decision.decision == "keep"
        assert "materials signal present" in decision.reason

    def test_route_materials_sentence_skips_without_signal(self):
        from lenses.construction_materials_v1 import route_materials_sentence

        decision = route_materials_sentence("The meeting agenda covered general project updates.")

        assert decision.decision == "skip"
        assert "no materials signal" in decision.reason


class TestClimateRouter:
    def test_route_climate_sentence_keeps_climate_signal(self):
        from lenses.construction_climate_v1 import route_climate_sentence

        decision = route_climate_sentence("The building envelope improved resilience against flooding.")

        assert decision.decision == "keep"
        assert decision.reason == "climate signal in construction context"

    def test_route_climate_sentence_skips_without_signal(self):
        from lenses.construction_climate_v1 import route_climate_sentence

        decision = route_climate_sentence("The committee reviewed unrelated logistics.")

        assert decision.decision == "skip"
        assert "no climate signal" in decision.reason


# ---------------------------------------------------------------------------
# construction_insurance_risk_v1
# ---------------------------------------------------------------------------

class TestInsuranceRiskLens:
    @pytest.mark.parametrize(
        "sentence, expected_event_type, expected_outcome",
        [
            (
                "Hail damage to asphalt shingles increased roof replacement claims after the storm.",
                "claim_driver",
                "negative",
            ),
            (
                "Hail damaged the roof covering and caused water intrusion behind the wall assembly.",
                "property_risk",
                "negative",
            ),
            (
                "Water intrusion behind stucco caused mold growth and interior wall damage.",
                "claim_driver",
                "negative",
            ),
            (
                "Installing impact-resistant roofing reduced expected wind and hail losses.",
                "risk_mitigation",
                "positive",
            ),
            (
                "The policy excluded flood damage below the elevated foundation.",
                "claim_driver",
                "negative",
            ),
        ],
    )
    def test_insurance_risk_sentence_triggers_detection(self, sentence, expected_event_type, expected_outcome):
        from lenses.construction_insurance_risk_v1 import detect

        event, entities = detect(sentence)

        _assert_event(event)
        _assert_entities(entities)
        assert event.event_type == expected_event_type
        assert event.outcome == expected_outcome
        assert event.lens == "insurance_risk"

    @pytest.mark.parametrize(
        "sentence",
        [
            "Stem cells showed improved survival after oxidative stress.",
            "The laser beam was focused through a glass lens.",
            "The foundation model was trained on clinical datasets.",
        ],
    )
    def test_irrelevant_sentences_do_not_fire(self, sentence):
        from lenses.construction_insurance_risk_v1 import detect

        event, entities = detect(sentence)

        assert event is None
        assert entities == []

    # Property terms alone should not fire unless systems, loss_causes, or insurance_terms provide support.
    def test_property_risk_terms_require_support_from_systems_or_loss_causes_or_insurance_terms(self):
        from lenses.construction_insurance_risk_v1 import detect

        event, entities = detect("The building envelope had moisture during testing.")

        assert event is None
        assert entities == []

    def test_insurance_risk_is_registered_in_multi_lens(self):
        from lenses import detect_multi_lens

        sentence = "Hail damage to asphalt shingles increased roof replacement claims after the storm."
        results = detect_multi_lens(sentence, enabled_lenses=["insurance_risk"])

        assert len(results) == 1
        assert results[0]["lens"] == "insurance_risk"
        assert results[0]["event_type"] == "claim_driver"
        assert results[0]["outcome"] == "negative"

    @pytest.mark.parametrize(
        "sentence",
        [
            "collapse of photon field",
            "wind and solar are intermittent",
            "pain mitigation",
        ],
    )
    def test_false_positive_sentences_do_not_fire(self, sentence):
        from lenses.construction_insurance_risk_v1 import detect

        event, entities = detect(sentence)

        assert event is None
        assert entities == []


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

    def test_biological_condensation_does_not_fire(self):
        from lenses.construction_building_physics_v1 import detect

        sentence = "The nucleolar number increased during mitotic condensation and chromosome segregation."
        event, entities = detect(sentence)

        assert event is None
        assert entities == []

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

    def test_negative_outcome_on_exacerbated(self):
        from lenses.construction_climate_v1 import detect
        sentence = "Flood vulnerability was exacerbated by increased storm surge intensity at the building foundation."
        event, _ = detect(sentence)
        assert event is not None
        assert event.outcome == "negative"

    def test_positive_outcome_ignores_no_inside_knowledge(self):
        from lenses.construction_climate_v1 import detect
        sentence = "The knowledge model reduced flood risk for the coastal wall."
        event, _ = detect(sentence)
        assert event is not None
        assert event.outcome == "positive"

    def test_non_construction_resilience_sentence_returns_none(self):
        from lenses.construction_climate_v1 import detect
        sentence = "Healthy primary cilia are essential for longevity and cellular resilience."
        event, entities = detect(sentence)
        assert event is None
        assert entities == []

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

    def test_non_construction_standard_sentence_returns_none(self):
        from lenses.construction_compliance_v1 import detect
        sentence = "Clinical islet isolation procedures followed a standard protocol for cell sorting."
        event, entities = detect(sentence)
        assert event is None
        assert entities == []

    def test_building_code_phrase_triggers(self):
        from lenses.construction_compliance_v1 import detect
        sentence = "The building code requires a minimum insulation level of R-30."
        event, entities = detect(sentence)
        _assert_event(event)
        assert event.event_type == "code_compliance"

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

    def test_standard_keyword_alone_does_not_trigger(self):
        from lenses.construction_compliance_v1 import detect
        sentence = "The energy standard requires a minimum insulation level of R-30."
        event, _ = detect(sentence)
        assert event is None

    def test_irrelevant_sentence_returns_none(self):
        from lenses.construction_compliance_v1 import detect
        event, entities = detect("The autumn leaves were beautiful in the park.")
        assert event is None
        assert entities == []


class TestMultiLensStacking:

    def test_building_physics_selected_lens_runs_without_construction_context(self):
        from lenses import detect_multi_lens

        sentence = "Thermal conductivity and dew point were measured in the material study."
        results = detect_multi_lens(sentence, enabled_lenses=["building_physics"])

        assert len(results) == 1
        assert results[0]["lens"] == "building_physics"

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

    def test_detect_multi_lens_raises_on_no_match(self):
        from lenses import detect_multi_lens_raise_on_no_match
        sentence = "This sentence is completely irrelevant to construction."
        with pytest.raises(RuntimeError) as excinfo:
            detect_multi_lens_raise_on_no_match(sentence, source_type="code_standard")
        assert "No detector produced results" in str(excinfo.value)

    def test_detect_multi_lens_detector_error_handling_modes(self, monkeypatch):
        import lenses
        from lenses import detect_multi_lens_raise_on_detector_errors, detect_multi_lens_return_errors

        class _FakeEvent:
            def as_dict(self):
                return {
                    "lens": "good",
                    "event_type": "test_event",
                    "outcome": "neutral",
                    "confidence": "med",
                    "context_strength": "moderate",
                    "source_weight": 0.5,
                    "tags": [],
                }

        def bad_detector(_sentence, source_type="research_paper"):
            raise ValueError("boom")

        def good_detector(_sentence, source_type="research_paper"):
            return _FakeEvent(), []

        def no_match_detector(_sentence, source_type="research_paper"):
            return None, []

        monkeypatch.setattr(
            lenses,
            "LENS_REGISTRY",
            {
                "bad": bad_detector,
                "none": no_match_detector,
            },
        )

        with pytest.raises(RuntimeError):
            detect_multi_lens_raise_on_detector_errors(
                "any sentence",
                enabled_lenses=["bad", "none"],
            )

        monkeypatch.setattr(
            lenses,
            "LENS_REGISTRY",
            {
                "bad": bad_detector,
                "good": good_detector,
            },
        )

        results, errors = detect_multi_lens_return_errors(
            "any sentence",
            enabled_lenses=["bad", "good"],
        )
        assert len(results) == 1
        assert results[0]["lens"] == "good"
        assert "bad" in errors
        assert "ValueError" in errors["bad"]

    def test_detect_multi_lens_warn_on_no_match_emits_warning(self, monkeypatch, caplog):
        import lenses
        from lenses import detect_multi_lens, detect_multi_lens_warn_on_no_match

        def no_match_detector(_sentence, source_type="research_paper"):
            return None, []

        monkeypatch.setattr(
            lenses,
            "LENS_REGISTRY",
            {
                "a": no_match_detector,
                "b": no_match_detector,
            },
        )

        with caplog.at_level(logging.WARNING):
            results = detect_multi_lens_warn_on_no_match("irrelevant")
        assert results == []
        assert any("No detectors matched and no errors reported." in m for m in caplog.messages)

        caplog.clear()
        with caplog.at_level(logging.WARNING):
            results_default = detect_multi_lens("irrelevant")
        assert results_default == []
        assert not any("No detectors matched and no errors reported." in m for m in caplog.messages)


# ---------------------------------------------------------------------------
# Direct tests for build_lens_event and LensEvent.as_dict

# ---------------------------------------------------------------------------
def test_build_lens_event_and_as_dict():
    from lenses.construction_common import build_lens_event, LensEvent

    lens_name = "materials"
    event_type = "strength_increase"
    raw_outcome = "improved"
    confidence = "high"
    tags = ["concrete", "test"]
    sentence = "The compressive strength improved to 45 MPa."
    source_type = "research_paper"


    event = build_lens_event(
        lens_name=lens_name,
        event_type=event_type,
        raw_outcome=raw_outcome,
        confidence=confidence,
        tags=tags,
        sentence=sentence,
        source_type=source_type,
    )
    # Check type and normalized fields
    assert isinstance(event, LensEvent)
    assert event.lens == lens_name
    assert event.event_type == event_type
    assert event.outcome == "positive"
    assert event.confidence == confidence
    assert event.context_strength in ("weak", "moderate", "strong")
    from lenses.construction_common import SOURCE_WEIGHTS
    assert event.source_weight == SOURCE_WEIGHTS["research_paper"]
    assert event.raw_outcome == "improved"
    assert set(event.tags) == set(tags)

    # Test as_dict output
    d = event.as_dict()
    assert d["lens"] == lens_name
    assert d["event_type"] == event_type
    assert d["outcome"] == "positive"
    assert d["raw_outcome"] == "improved"
    assert d["confidence"] == confidence
    assert d["context_strength"] == event.context_strength
    assert d["source_weight"] == SOURCE_WEIGHTS["research_paper"]
    assert set(d["tags"]) == set(tags)
