import sys
from pathlib import Path

from utils.source_triage import classify_triage, main, write_triage_csv


def test_classify_triage_keep_construction():
    result = classify_triage(
        file_path=Path("input/pdfs/building.pdf"),
        title="Building envelope moisture control for roof assemblies",
        metadata_text="NIST | Building Science Corporation",
        sample_text="This report examines insulation, vapor control, thermal performance, and foundation details for construction science.",
    )

    assert result.keep_skip_review == "keep"
    assert result.detected_domain == "construction_science"
    assert "building envelope" in result.construction_signals
    assert "NIST" not in result.contamination_signals


def test_classify_triage_skip_biomedical():
    result = classify_triage(
        file_path=Path("input/pdfs/biomed.pdf"),
        title="Stem cell assay for protein receptor response",
        metadata_text="clinical trial | serum | plasma",
        sample_text="This paper evaluates peptide kinase activity in mouse model systems and drug discovery workflows.",
    )

    assert result.keep_skip_review == "skip"
    assert result.detected_domain == "biomedical"
    assert "stem cell" in result.contamination_signals
    assert "protein" in result.contamination_signals


def test_classify_triage_review_mixed_signals(tmp_path):
    result = classify_triage(
        file_path=Path("input/pdfs/mixed.pdf"),
        title="Building materials study with stem cell contamination",
        metadata_text="DOE | research note",
        sample_text="The paper mentions building envelope details alongside assay and protein references.",
    )

    assert result.keep_skip_review == "review"
    assert result.detected_domain == "construction_science"

    csv_path = tmp_path / "triage.csv"
    written = write_triage_csv([result], csv_path)
    assert written == csv_path
    assert csv_path.exists()


def test_classify_triage_moderate_biomedical_contamination_skips() -> None:
    result = classify_triage(
        file_path=Path("input/pdfs/bio.pdf"),
        title="Arachidonic acid availability controls neutrophil swarm initiation and scaling",
        metadata_text="bioRxiv | preprint",
        sample_text="This study uses mouse models, cells, and proteins to study immune response.",
    )

    assert result.keep_skip_review == "skip"
    assert result.detected_domain == "biomedical"


def test_classify_triage_review_climate_normals_boilerplate():
    result = classify_triage(
        file_path=Path("input/pdfs/climate_normals.pdf"),
        title="Canadian climate normals 1951-1980",
        metadata_text="Environment Canada | Atmospheric Service",
        sample_text="Canadian Climate Normals. Volume 8: Pressure, Temperature and Humidity. Building code tables are listed for reference only.",
    )

    assert result.keep_skip_review == "review"
    assert result.detected_domain == "construction_science"
    assert result.construction_signals == "code"


def test_classify_triage_review_does_not_keep_on_substring_matches():
    result = classify_triage(
        file_path=Path("input/pdfs/generic_science.pdf"),
        title="Encoded activity scheduling for neural systems",
        metadata_text="LLM-based AI systems | computational biology",
        sample_text="The paper studies structural representations in cellular networks without any building context.",
    )

    assert result.keep_skip_review == "review"
    assert "code" not in result.construction_signals
    assert "attic" not in result.construction_signals


def test_classify_triage_review_when_no_building_context_is_present():
    result = classify_triage(
        file_path=Path("input/pdfs/materials_only.pdf"),
        title="Advanced materials and structural analysis of photonic crystals",
        metadata_text="journal article | computational modeling",
        sample_text="The study reports materials properties, structural dynamics, and thermal transport in photonic crystals.",
    )

    assert result.keep_skip_review == "review"
    assert result.detected_domain in {"materials_science", "physics", "unknown", "mixed"}


def test_classify_triage_review_does_not_treat_generic_building_usage_as_context():
    result = classify_triage(
        file_path=Path("input/pdfs/modeling.pdf"),
        title="Building a protein model with neural representations",
        metadata_text="computational biology | machine learning",
        sample_text="The paper discusses building a predictor for cellular signaling pathways without any construction-science content.",
    )

    assert result.keep_skip_review == "review"
    assert result.detected_domain in {"unknown", "biomedical", "mixed"}


def test_classify_triage_review_physics_bucket():
    result = classify_triage(
        file_path=Path("input/pdfs/physics.pdf"),
        title="Quantum Landscape of Superconducting Diodes",
        metadata_text="photonic transport | electronic states",
        sample_text="The paper studies optical modulation and topological transport in a semiconductor device.",
    )

    assert result.keep_skip_review == "review"
    assert result.detected_domain == "physics"


def test_main_rejects_invalid_domain(monkeypatch, capsys, tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    (input_dir / "paper.pdf").write_bytes(b"pdf")

    monkeypatch.setattr(
        sys,
        "argv",
        ["source_triage.py", "--input-dir", str(input_dir), "--domain", "bad/domain"],
    )

    assert main() == 1
    captured = capsys.readouterr()
    assert "Invalid domain value:" in captured.out