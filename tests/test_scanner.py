from pathlib import Path

from bookdesk.library import LibraryIndex
from bookdesk.scanner import ScanWorker, find_books, scan_folder


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


def make_books(root: Path, count: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (root / f"Book {i}.epub").write_bytes(b"")


def test_scan_worker_stop_halts_processing_mid_scan(tmp_path):
    root = tmp_path / "books"
    make_books(root, 20)
    library = make_index(tmp_path)
    worker = ScanWorker([str(root)], library)

    original = library.mark_scanned
    calls = []

    def counting(*args, **kwargs):
        calls.append(1)
        if len(calls) == 5:
            worker.stop()
        return original(*args, **kwargs)

    library.mark_scanned = counting
    worker.run()

    assert len(calls) == 5
    assert len(library.all_items()) == 5


def test_scan_worker_stop_does_not_wrongly_forget_existing_entries(tmp_path):
    root = tmp_path / "books"
    make_books(root, 10)
    library = make_index(tmp_path)
    ScanWorker([str(root)], library).run()
    assert len(library.all_items()) == 10

    worker = ScanWorker([str(root)], library)
    calls = []
    original = library.mark_scanned

    def counting(*args, **kwargs):
        calls.append(1)
        if len(calls) == 3:
            worker.stop()
        return original(*args, **kwargs)

    library.mark_scanned = counting
    worker.run()
    assert len(library.all_items()) == 10


def test_scan_folder_should_stop_halts_processing(tmp_path):
    root = tmp_path / "books"
    make_books(root, 10)
    library = make_index(tmp_path)
    calls = []

    def should_stop():
        calls.append(1)
        return len(calls) > 3

    scan_folder(root, root, library, should_stop=should_stop)
    assert len(library.all_items()) == 3
