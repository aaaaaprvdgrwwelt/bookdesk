from pathlib import Path

import pymupdf
import pytest
from ebooklib import epub
from PySide6.QtWidgets import QApplication

from bookdesk.library import LibraryIndex
from bookdesk.reader import ReaderWindow

# Eine QApplication pro Testlauf - Widgets lassen sich sonst nicht erzeugen.
_app = QApplication.instance() or QApplication([])


def make_epub(tmp_path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("id1")
    book.set_title("Test Book")
    book.set_language("en")
    c1 = epub.EpubHtml(title="Chapter 1", file_name="chap1.xhtml", lang="en")
    c1.content = "<html><body><p>The quick brown fox jumps.</p></body></html>"
    c2 = epub.EpubHtml(title="Chapter 2", file_name="chap2.xhtml", lang="en")
    c2.content = "<html><body><p>A hidden treasure lies beyond.</p></body></html>"
    book.add_item(c1)
    book.add_item(c2)
    book.spine = ["nav", c1, c2]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    path = tmp_path / "book.epub"
    epub.write_epub(str(path), book)
    return path


def make_pdf(tmp_path) -> Path:
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 50), "The quick brown fox.")
    doc.new_page().insert_text((50, 50), "A hidden treasure map.")
    path = tmp_path / "book.pdf"
    doc.save(str(path))
    doc.close()
    return path


def make_reader(tmp_path, path: Path) -> ReaderWindow:
    library = LibraryIndex(tmp_path / "library.sqlite")
    library.mark_scanned(path, tmp_path, title="Test")
    item = library.get(path)
    return ReaderWindow(item, library)


def test_epub_search_jumps_to_chapter_containing_query(tmp_path):
    reader = make_reader(tmp_path, make_epub(tmp_path))
    reader.search_box.setText("hidden treasure")
    reader._search(forward=True)
    assert reader.index == 1
    reader.close()


def test_epub_search_not_found_sets_status(tmp_path):
    reader = make_reader(tmp_path, make_epub(tmp_path))
    reader.search_box.setText("nonexistent phrase xyz")
    reader._search(forward=True)
    assert reader.search_status.text() == "Nicht gefunden."
    reader.close()


def test_epub_zoom_in_and_reset(tmp_path):
    reader = make_reader(tmp_path, make_epub(tmp_path))
    reader._zoom_in()
    reader._zoom_in()
    assert reader._zoom_steps == 2
    reader._zoom_reset()
    assert reader._zoom_steps == 0
    reader.close()


def test_epub_zoom_respects_upper_bound(tmp_path):
    reader = make_reader(tmp_path, make_epub(tmp_path))
    for _ in range(50):
        reader._zoom_in()
    assert reader._zoom_steps <= 12
    reader.close()


def test_pdf_search_jumps_to_page_containing_query(tmp_path):
    reader = make_reader(tmp_path, make_pdf(tmp_path))
    reader.search_box.setText("hidden treasure")
    reader._search(forward=True)
    assert reader.index == 1
    reader.close()


def test_pdf_zoom_in_and_reset_changes_zoom_factor(tmp_path):
    reader = make_reader(tmp_path, make_pdf(tmp_path))
    reader._zoom_in()
    assert reader._pdf_zoom == pytest.approx(1.1)
    reader._zoom_reset()
    assert reader._pdf_zoom == pytest.approx(1.0)
    reader.close()


def test_pdf_zoom_respects_bounds(tmp_path):
    reader = make_reader(tmp_path, make_pdf(tmp_path))
    for _ in range(50):
        reader._zoom_in()
    assert reader._pdf_zoom <= 2.5
    for _ in range(50):
        reader._zoom_out()
    assert reader._pdf_zoom >= 0.5
    reader.close()
