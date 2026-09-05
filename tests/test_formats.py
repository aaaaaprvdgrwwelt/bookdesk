import pymupdf

from bookdesk.formats import base as formats
from bookdesk.formats.pdf import find_pages


def make_pdf(tmp_path, texts: list[str]):
    doc = pymupdf.open()
    for text in texts:
        page = doc.new_page()
        page.insert_text((50, 50), text)
    path = tmp_path / "test.pdf"
    doc.save(str(path))
    doc.close()
    return path


def test_find_pages_returns_matching_page_indices(tmp_path):
    path = make_pdf(tmp_path, ["The quick brown fox", "A hidden treasure map"])
    assert find_pages(path, "hidden treasure") == [1]


def test_find_pages_is_case_insensitive(tmp_path):
    path = make_pdf(tmp_path, ["The Quick Brown Fox"])
    assert find_pages(path, "quick brown") == [0]


def test_find_pages_empty_query_returns_nothing(tmp_path):
    path = make_pdf(tmp_path, ["Some text"])
    assert find_pages(path, "") == []


def test_find_pages_no_match_returns_empty_list(tmp_path):
    path = make_pdf(tmp_path, ["Some text"])
    assert find_pages(path, "nonexistent phrase") == []


def test_base_find_pages_dispatches_only_for_pdf(tmp_path):
    path = make_pdf(tmp_path, ["Findable text"])
    assert formats.find_pages(path, "findable") == [0]
    assert formats.find_pages(tmp_path / "book.epub", "anything") == []
