from unittest.mock import patch

from utils.abstract_collectors import extract_abstract_text_from_html, extract_abstract_text_from_url, find_abstract_links


def test_find_abstract_links_collects_doi_and_asce_links():
    entry = {
        "link": "https://example.com/article",
        "summary": "See https://doi.org/10.1234/example for details",
        "links": [
            {"href": "https://ascelibrary.org/doi/abs/10.1115/1.1234567", "title": "abstract"},
          {"href": "https://notdoi.org/abs/10.9999/fake", "title": "fake abstract"},
          {"href": "https://ascelibrary.org.evil.com/doi/abs/10.1115/1.9999999", "title": "fake asce"},
          {"href": "https://arxiv.org/abs/1234.5678", "title": "arxiv abstract"},
            {"href": "https://example.com/doc.pdf", "title": "pdf"},
        ],
        "content": [{"value": "More text with https://doi.org/10.5678/other"}],
    }

    links = find_abstract_links(entry)

    assert "https://example.com/article" in links
    assert "https://doi.org/10.1234/example" in links
    assert "https://ascelibrary.org/doi/abs/10.1115/1.1234567" in links
    assert "https://arxiv.org/abs/1234.5678" in links
    assert "https://doi.org/10.5678/other" in links
    assert "https://notdoi.org/abs/10.9999/fake" not in links
    assert "https://ascelibrary.org.evil.com/doi/abs/10.1115/1.9999999" not in links


def test_extract_abstract_text_from_html():
    html = """
    <html>
      <body>
        <div id="abstract">
          <p>This paper reports <b>moisture failure</b>, repair strategy, and observed performance in building assemblies.</p>
        </div>
      </body>
    </html>
    """

    abstract = extract_abstract_text_from_html(html)

    assert abstract is not None
    assert "moisture failure" in abstract
    assert "repair strategy" in abstract
    assert "observed performance" in abstract


@patch("utils.abstract_collectors.requests.get")
def test_extract_abstract_text_from_url_rejects_invalid_url(mock_get):
    assert extract_abstract_text_from_url("ftp://example.com/article") is None
    assert extract_abstract_text_from_url("https:///missing-host") is None
    mock_get.assert_not_called()