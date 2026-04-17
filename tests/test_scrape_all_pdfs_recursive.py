from utils import scrape_all_pdfs_recursive

def test_find_all_pdfs_empty(tmp_path):
    # Should return empty list if no PDFs
    result = scrape_all_pdfs_recursive.find_all_pdfs([tmp_path])
    assert result == []

def test_find_all_pdfs_nested(tmp_path):
    # Create nested folders and PDFs
    d1 = tmp_path / "a"
    d1.mkdir()
    d2 = d1 / "b"
    d2.mkdir()
    pdf1 = d1 / "file1.pdf"
    pdf1.write_bytes(b"%PDF-1.4 test")
    pdf2 = d2 / "file2.PDF"
    pdf2.write_bytes(b"%PDF-1.4 test")
    result = scrape_all_pdfs_recursive.find_all_pdfs([tmp_path])
    found = set(str(p.name).lower() for p in result)
    assert "file1.pdf" in found
    assert "file2.pdf" in found
    assert len(result) == 2
