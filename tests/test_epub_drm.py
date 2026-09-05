import zipfile
from pathlib import Path

from ebooklib import epub

from bookdesk.formats import base as formats
from bookdesk.formats.epub import is_drm_protected
from bookdesk.library import STATUS_ERROR, LibraryIndex
from bookdesk.scanner import scan_folder


def make_epub(path: Path, *, drm: bool = False) -> Path:
    book = epub.EpubBook()
    book.set_identifier("id1")
    book.set_title("Some Book")
    book.set_language("en")
    c1 = epub.EpubHtml(title="Chapter 1", file_name="chap1.xhtml", lang="en")
    c1.content = "<html><body><p>content</p></body></html>"
    book.add_item(c1)
    book.spine = ["nav", c1]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)
    if drm:
        with zipfile.ZipFile(path, "a") as zf:
            zf.writestr("META-INF/encryption.xml", "<encryption/>")
    return path


def test_is_drm_protected_true_when_encryption_manifest_present(tmp_path):
    path = make_epub(tmp_path / "book.epub", drm=True)
    assert is_drm_protected(path) is True


def test_is_drm_protected_false_for_plain_epub(tmp_path):
    path = make_epub(tmp_path / "book.epub", drm=False)
    assert is_drm_protected(path) is False


def test_is_drm_protected_false_for_non_epub_file(tmp_path):
    path = tmp_path / "not-a-book.epub"
    path.write_bytes(b"not a zip at all")
    assert is_drm_protected(path) is False


def test_base_dispatch_only_checks_epub(tmp_path):
    epub_path = make_epub(tmp_path / "book.epub", drm=True)
    assert formats.is_drm_protected(epub_path) is True
    assert formats.is_drm_protected(tmp_path / "book.pdf") is False


def test_scan_folder_marks_drm_protected_epub_as_error(tmp_path):
    make_epub(tmp_path / "protected.epub", drm=True)
    index = LibraryIndex(tmp_path / "library.sqlite")
    scan_folder(tmp_path, tmp_path, index)
    items = index.list_books()
    assert len(items) == 1
    assert items[0].status == STATUS_ERROR
    assert "DRM" in items[0].note


def test_scan_folder_does_not_flag_plain_epub(tmp_path):
    make_epub(tmp_path / "plain.epub", drm=False)
    index = LibraryIndex(tmp_path / "library.sqlite")
    scan_folder(tmp_path, tmp_path, index)
    items = index.list_books()
    assert len(items) == 1
    assert items[0].status != STATUS_ERROR
