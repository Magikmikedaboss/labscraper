from utils import site_collectors


def test_collect_documents_respects_path_prefix_and_depth(monkeypatch):
    pages = {
        "https://example.com/section/index": """
            <html><head><title>Index</title></head><body>
                <a href="/section/page-1">One</a>
                <a href="/other/page-x">Other</a>
                <a href="mailto:test@example.com">Mail</a>
            </body></html>
        """,
        "https://example.com/section/page-1": """
            <html><head><title>Page 1</title></head><body>
                <a href="/section/page-2">Two</a>
            </body></html>
        """,
        "https://example.com/section/page-2": """
            <html><head><title>Page 2</title></head><body>
                <a href="/section/page-3">Three</a>
            </body></html>
        """,
        "https://example.com/section/page-3": """
            <html><head><title>Page 3</title></head><body>
                <p>Should not be reached at depth 2.</p>
            </body></html>
        """,
    }

    def fake_fetch_page(url: str, timeout: int = 20) -> str:
        return pages[url]

    monkeypatch.setattr(site_collectors, "fetch_page", fake_fetch_page)

    docs = site_collectors.collect_documents(
        "https://example.com/section/index",
        max_pages=10,
        same_domain_only=True,
        same_path_prefix="/section",
        max_depth=2,
        request_timeout=20,
        max_seconds=30,
    )

    assert [doc.url for doc in docs] == [
        "https://example.com/section/index",
        "https://example.com/section/page-1",
        "https://example.com/section/page-2",
    ]
    assert all("/other/" not in doc.url for doc in docs)
    assert all(doc.title for doc in docs)


def test_extract_pdf_links_from_page_accepts_path_and_query_pdf_links(monkeypatch):
    html = """
        <html><body>
            <a href="/files/report.pdf">Direct PDF</a>
            <a href="/viewer?file=doc.pdf">Query PDF</a>
            <a href="/viewer?file=doc.txt">Not a PDF</a>
        </body></html>
    """

    monkeypatch.setattr(site_collectors, "fetch_page", lambda url, timeout=20: html)

    pdf_links = site_collectors.extract_pdf_links_from_page("https://example.com/page")

    assert "https://example.com/files/report.pdf" in pdf_links
    assert "https://example.com/viewer?file=doc.pdf" in pdf_links
    assert "https://example.com/viewer?file=doc.txt" not in pdf_links