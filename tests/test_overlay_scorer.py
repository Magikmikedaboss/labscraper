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


def test_construction_overlay_ignores_laser_beam_context():
    scorer = OverlayScorer({"dual_lens": True, "overlays": ["construction_research_v1"]})

    scores = scorer.apply_event_scores(
        {
            "evidence_snippet": "The laser beam was split into probe and reference beams in the interferometer.",
            "event_type": "method_evaluation",
        }
    )

    assert scores["construction_research_v1"] == 0


def test_construction_overlay_ignores_cell_and_domain_wall_context():
    scorer = OverlayScorer({"dual_lens": True, "overlays": ["construction_research_v1"]})

    scores = scorer.apply_event_scores(
        {
            "evidence_snippet": "Cell wall mechanics and magnetic domain wall motion were measured by microscopy.",
            "event_type": "method_evaluation",
        }
    )

    assert scores["construction_research_v1"] == 0


def test_construction_overlay_ignores_foundation_model_context():
    scorer = OverlayScorer({"dual_lens": True, "overlays": ["construction_research_v1"]})

    scores = scorer.apply_event_scores(
        {
            "evidence_snippet": "The foundation model was fine-tuned on biomedical text for downstream tasks.",
            "event_type": "method_evaluation",
        }
    )

    assert scores["construction_research_v1"] == 0


def test_construction_overlay_scores_structural_beam_context():
    scorer = OverlayScorer({"dual_lens": True, "overlays": ["construction_research_v1"]})

    scores = scorer.apply_event_scores(
        {
            "evidence_snippet": "The structural beam carries load across the roof assembly and foundation wall.",
            "event_type": "decision_point",
        }
    )

    assert scores["construction_research_v1"] > 0
