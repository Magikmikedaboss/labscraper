from __future__ import annotations

def test_collect_candidate_pdfs_includes_review_bucket(tmp_path, monkeypatch):
    from tools import evaluate_construction_lenses as evaluator

    root = tmp_path
    review_dir = root / "cache" / "rss_organized" / "construction_science" / "review"
    review_dir.mkdir(parents=True)
    review_pdf = review_dir / "review-paper.pdf"
    review_pdf.write_bytes(b"%PDF-1.4\n%EOF")

    monkeypatch.setattr(evaluator, "ROOT", root)
    monkeypatch.setattr(evaluator, "scan_pdfs", lambda *args, **kwargs: [])

    result = evaluator._collect_candidate_pdfs(root / "cache" / "rss", set(), limit=5, triage_limit=None)

    assert result == [review_pdf]
    assert evaluator._is_review_bucket_pdf(review_pdf)
    assert not evaluator._is_review_bucket_pdf(root / "cache" / "rss" / "other.pdf")