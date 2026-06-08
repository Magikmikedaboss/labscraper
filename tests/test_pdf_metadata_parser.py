from utils import pdf_metadata_parser


def test_extract_year_from_creation_date():
    assert pdf_metadata_parser.extract_year_from_creation_date("D:20240102120000") == 2024
    assert pdf_metadata_parser.extract_year_from_creation_date("invalid") is None
    assert pdf_metadata_parser.extract_year_from_creation_date(None) is None


def test_parse_first_page_text_title_authors_doi_and_year():
    text = """
Journal of Examples
An interesting study of widgets
Alice Smith and Bob Jones
DOI: 10.1234/abcd.efg
Published 2023
"""
    meta = pdf_metadata_parser.parse_first_page_text(text)
    assert meta["title"] == "An interesting study of widgets"
    assert meta["authors"] == "Alice Smith and Bob Jones"
    assert meta["doi"] == "10.1234/abcd.efg"
    assert meta["year"] == 2023


def test_parse_first_page_text_fallbacks():
    text = """

    Short
    No DOI here
    """
    meta = pdf_metadata_parser.parse_first_page_text(text)
    assert meta["title"] == "Short"
    assert meta["authors"] is None
    assert meta["doi"] is None
    assert meta["year"] is None
