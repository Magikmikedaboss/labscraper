from utils.overlay_scorer import OverlayScorer


def test_construction_overlay_scores_construction_terms():
    scorer = OverlayScorer({"dual_lens": True, "overlays": ["construction_research_v1"]})

    scores = scorer.apply_event_scores(
        {
            "evidence_snippet": "sound insulation performance depends on thermal conductivity and freeze-thaw cycles",
            "event_type": "decision_point",
        }
    )

    assert "construction_research_v1" in scores
    assert scores["construction_research_v1"] > 0


def test_construction_overlay_stays_zero_for_unrelated_text():
    scorer = OverlayScorer({"dual_lens": True, "overlays": ["construction_research_v1"]})

    scores = scorer.apply_event_scores(
        {
            "evidence_snippet": "fluorescence recovery in cilia was monitored with microscopy",
            "event_type": "method_evaluation",
        }
    )

    assert scores["construction_research_v1"] == 0
