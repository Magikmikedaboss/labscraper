from pathlib import Path

from pdfplumber.utils.exceptions import PdfminerException

from utils.organize_pdfs import _destination_path, organize_pdfs, write_organization_index
from utils.source_triage import TriagedSource, classify_triage


def raise_pdfminer_error(pdf_path, first_pages=2, max_chars=1600):
    raise PdfminerException("No /Root object! - Is this really a PDF?")


def test_destination_path_groups_by_domain_and_status():
    output_root = Path("organized_pdfs")
    input_root = Path("cache/rss")
    pdf_path = input_root / "nested" / "paper.pdf"
    triage = TriagedSource(
        file_path=str(pdf_path),
        title="Paper",
        detected_domain="construction_science",
        keep_skip_review="review",
        confidence="low",
        construction_signals="",
        contamination_signals="",
        reason="mixed or weak signals",
    )

    destination = _destination_path(output_root, input_root, pdf_path, triage)

    assert destination == output_root / "construction_science" / "review" / "rss" / "nested" / "paper.pdf"


def test_organize_pdfs_copies_files_and_writes_index(tmp_path, monkeypatch):
    cache_root = tmp_path / "cache" / "rss"
    pdfs_root = tmp_path / "input" / "pdfs" / "biohacking_longevity"
    cache_root.mkdir(parents=True)
    pdfs_root.mkdir(parents=True)

    cache_pdf = cache_root / "a.pdf"
    input_pdf = pdfs_root / "b.pdf"
    cache_pdf.write_bytes(b"%PDF-1.4 cache")
    input_pdf.write_bytes(b"%PDF-1.4 input")

    output_root = tmp_path / "organized_pdfs"

    triage_map = {
        cache_pdf: TriagedSource(
            file_path=str(cache_pdf),
            title="Cache Paper",
            detected_domain="physics",
            keep_skip_review="review",
            confidence="low",
            construction_signals="",
            contamination_signals="",
            reason="mixed",
        ),
        input_pdf: TriagedSource(
            file_path=str(input_pdf),
            title="Input Paper",
            detected_domain="construction_science",
            keep_skip_review="keep",
            confidence="high",
            construction_signals="wall",
            contamination_signals="",
            reason="construction",
        ),
    }

    monkeypatch.setattr(
        "utils.organize_pdfs.scan_pdf",
        lambda pdf_path, first_pages=2, max_chars=1600: triage_map[pdf_path],
    )

    rows = organize_pdfs(
        input_roots=[cache_root, tmp_path / "input" / "pdfs"],
        output_root=output_root,
        dry_run=False,
        action="copy",
    )

    assert len(rows) == 2
    assert all(not row.is_duplicate for row in rows)
    assert (output_root / "physics" / "review" / "rss" / "a.pdf").exists()
    assert (output_root / "construction_science" / "keep" / "pdfs" / "biohacking_longevity" / "b.pdf").exists()

    index_path = write_organization_index(rows, output_root)
    content = index_path.read_text(encoding="utf-8")
    assert (
        "source_path,destination_path,detected_domain,keep_skip_review,confidence,title,reason,content_hash,is_duplicate,duplicate_of"
        in content
    )
    assert str(output_root / "physics" / "review" / "rss" / "a.pdf") in content
    assert str(output_root / "construction_science" / "keep" / "pdfs" / "biohacking_longevity" / "b.pdf") in content


def test_organize_pdfs_skips_unreadable_pdfs(tmp_path, monkeypatch):
    cache_root = tmp_path / "cache" / "rss"
    cache_root.mkdir(parents=True)

    bad_pdf = cache_root / "broken.pdf"
    bad_pdf.write_bytes(b"not a pdf")

    monkeypatch.setattr(
        "utils.organize_pdfs.scan_pdf",
        raise_pdfminer_error,
    )

    rows = organize_pdfs(
        input_roots=[cache_root],
        output_root=tmp_path / "organized_pdfs",
        dry_run=False,
        action="copy",
    )

    assert len(rows) == 1
    assert rows[0].keep_skip_review == "review"
    assert rows[0].detected_domain == "unknown"
    assert (tmp_path / "organized_pdfs" / "unknown" / "review" / "rss" / "broken.pdf").exists()


def test_organize_pdfs_skips_duplicate_content(tmp_path, monkeypatch):
    cache_root = tmp_path / "cache" / "rss"
    input_root = tmp_path / "input" / "pdfs" / "biohacking_longevity"
    cache_root.mkdir(parents=True)
    input_root.mkdir(parents=True)

    pdf_a = cache_root / "paper-a.pdf"
    pdf_b = input_root / "paper-b.pdf"
    payload = b"%PDF-1.4 duplicate content"
    pdf_a.write_bytes(payload)
    pdf_b.write_bytes(payload)

    monkeypatch.setattr(
        "utils.organize_pdfs.scan_pdf",
        lambda pdf_path, first_pages=2, max_chars=1600: TriagedSource(
            file_path=str(pdf_path),
            title="Shared Paper",
            detected_domain="physics",
            keep_skip_review="review",
            confidence="low",
            construction_signals="",
            contamination_signals="",
            reason="mixed",
        ),
    )

    output_root = tmp_path / "organized_pdfs"
    rows = organize_pdfs(
        input_roots=[cache_root, tmp_path / "input" / "pdfs"],
        output_root=output_root,
        dry_run=False,
        action="copy",
    )

    assert len(rows) == 2
    assert rows[0].is_duplicate is False
    assert rows[1].is_duplicate is True
    assert rows[1].duplicate_of == str(rows[0].destination_path)
    assert (output_root / "physics" / "review" / "rss" / "paper-a.pdf").exists()
    assert not (output_root / "physics" / "review" / "pdfs" / "biohacking_longevity" / "paper-b.pdf").exists()


def test_organize_pdfs_move_fallback_continues_when_remove_fails(tmp_path, monkeypatch):
    input_root = tmp_path / "input" / "pdfs"
    input_root.mkdir(parents=True)

    pdf_path = input_root / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fallback")

    output_root = tmp_path / "organized_pdfs"

    monkeypatch.setattr(
        "utils.organize_pdfs.scan_pdf",
        lambda pdf_path, first_pages=2, max_chars=1600: TriagedSource(
            file_path=str(pdf_path),
            title="Fallback Paper",
            detected_domain="physics",
            keep_skip_review="review",
            confidence="low",
            construction_signals="",
            contamination_signals="",
            reason="mixed",
        ),
    )
    monkeypatch.setattr("utils.organize_pdfs.shutil.move", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("move failed")))
    monkeypatch.setattr("utils.organize_pdfs.os.remove", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("remove failed")))

    rows = organize_pdfs(
        input_roots=[input_root],
        output_root=output_root,
        dry_run=False,
        action="move",
    )

    assert len(rows) == 1
    assert rows[0].source_path == pdf_path
    assert (output_root / "physics" / "review" / "pdfs" / "paper.pdf").exists()


def test_classify_triage_does_not_promote_generic_material_words_to_materials_science(tmp_path):
    triage = classify_triage(
        file_path=tmp_path / "Bat-flight_curbio.pdf",
        title="Bat flight",
        metadata_text="",
        sample_text="",
    )

    assert triage.detected_domain == "unknown"
