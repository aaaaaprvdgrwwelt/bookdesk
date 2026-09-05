from pathlib import Path

from bookdesk.library import LibraryIndex
from bookdesk.scanner import find_books, scan_folder


def make_index(tmp_path) -> LibraryIndex:
    return LibraryIndex(tmp_path / "library.sqlite")


def test_find_books_only_lists_known_extensions(tmp_path):
    (tmp_path / "book.epub").write_bytes(b"")
    (tmp_path / "book.pdf").write_bytes(b"")
    (tmp_path / "notes.txt").write_bytes(b"")
    found = find_books(tmp_path)
    names = {p.name for p in found}
    assert names == {"book.epub", "book.pdf"}


def test_scan_folder_falls_back_to_filename_when_metadata_is_empty(tmp_path):
    root = tmp_path / "library"
    folder = root / "Author Name"
    folder.mkdir(parents=True)
    (folder / "Some Book Title.epub").write_bytes(b"")

    index = make_index(tmp_path)
    scan_folder(folder, root, index)

    items = index.list_books()
    assert len(items) == 1
    assert items[0].title == "Some Book Title"


def test_scan_folder_only_touches_given_subfolder(tmp_path):
    root = tmp_path / "library"
    folder_a = root / "AuthorA"
    folder_b = root / "AuthorB"
    folder_a.mkdir(parents=True)
    folder_b.mkdir(parents=True)
    (folder_a / "A.epub").write_bytes(b"")
    (folder_b / "B.epub").write_bytes(b"")

    index = make_index(tmp_path)
    index.mark_scanned(folder_a / "A.epub", root, title="A")
    index.mark_scanned(folder_b / "B.epub", root, title="B")

    # B.epub aus dem Dateisystem entfernen, aber nur AuthorA neu scannen -
    # B darf trotzdem in der Bibliothek bleiben.
    (folder_b / "B.epub").unlink()
    scan_folder(folder_a, root, index)

    remaining_titles = {i.title for i in index.list_books()}
    assert remaining_titles == {"A", "B"}
