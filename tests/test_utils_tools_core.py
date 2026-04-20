
from utils import common, text_utils, event_classification, data_extractors
from utils.event_classification import ConfidenceInput

def test_sha16_and_sha64():
    s = "test string"
    h16 = common.sha16(s)
    h64 = common.sha64(s)
    assert isinstance(h16, str) and len(h16) == 16
    assert isinstance(h64, str) and len(h64) == 64
    assert h64.startswith(h16)

def test_chunk_sentences():
    text = "Sentence one. Sentence two! Sentence three?"
    chunks = text_utils.chunk_sentences(text)
    assert chunks == ["Sentence one.", "Sentence two!", "Sentence three?"]

def test_guess_stage():
    assert text_utils.guess_stage("This was done in vivo in a mouse.") == "in_vivo"
    assert text_utils.guess_stage("Patient samples in clinical trial.") == "clinical"
    assert text_utils.guess_stage("Cells were cultured in vitro.") == "in_vitro"
    assert text_utils.guess_stage("No context.") == "unknown"

def test_guess_section():
    assert text_utils.guess_section("methods and results") == "mixed"
    assert text_utils.guess_section("methods only") == "methods"
    assert text_utils.guess_section("results only") == "results"
    assert text_utils.guess_section("discussion here") == "discussion"
    assert text_utils.guess_section("intro") == "unknown"

def test_detect_method_tags():
    s = "The sample was analyzed by mass spectrometry and fluorescence."
    tags = event_classification.detect_method_tags(s.lower())
    # Accept any mass spectrometry synonym and fluorescence
    ms_synonyms = {"lc-ms/ms", "mass_spec", "mass-spectrometry", "ms"}
    assert any(tag in tags for tag in ms_synonyms), f"Expected a mass spectrometry tag in {tags}"
    assert any("fluoresc" in tag for tag in tags), f"Expected a fluorescence tag in {tags}"

def test_detect_failure_reason():
    s = "The compound was unstable and showed poor stability."
    reason = event_classification.detect_failure_reason(s.lower())
    assert reason == "stability_failure"

def test_detect_decision():
    s = "The project was abandoned."
    decision, _ = event_classification.detect_decision(s.lower())
    assert decision == "abandoned"

def test_detect_outcome():
    s = "The results were significant and improved."
    outcome = event_classification.detect_outcome(s.lower())
    assert outcome == "positive"

def test_classify_event_type():
    s = "The sample was toxic and showed corrosion."
    tags = []
    event_type = event_classification.classify_event_type(s.lower(), tags, "toxicity_flag", "unknown")
    assert event_type == "toxicity_flag"

def test_evidence_strength():
    assert event_classification.evidence_strength("This is significant and robust.") == "strong"
    assert event_classification.evidence_strength("This may be a trend.") == "weak"
    assert event_classification.evidence_strength("No special words.") == "moderate"

def test_confidence_score():
    score = event_classification.confidence_score(
        ConfidenceInput(
            has_entity=True,
            method_tags=["lc-ms/ms"],
            failure_reason="stability_failure",
            decision_taken="abandoned",
            has_measurements=True,
            sentence_l="lc-ms in vivo degraded"
        )
    )
    assert score == "high"
    score = event_classification.confidence_score(
        ConfidenceInput(
            has_entity=False,
            method_tags=[],
            failure_reason="unknown",
            decision_taken="unknown",
            has_measurements=False,
            sentence_l=""
        )
    )
    assert score == "low"

def test_suggested_keep():
    assert event_classification.suggested_keep("high", "toxicity_flag", "toxicity_flag", "abandoned", ["lc-ms/ms"]) == 1
    assert event_classification.suggested_keep("low", "other", "unknown", "unknown", []) == 0

def test_extract_quantitative_data():
    s = "IC50 was 50nm. Half-life was 2 hours."
    results = data_extractors.extract_quantitative_data(s)
    assert any(r["measurement_type"] == "ic50" and r["value"] == 50 for r in results)
    assert any(r["measurement_type"] == "half_life" and r["value"] == 2 for r in results)
