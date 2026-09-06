from pathlib import Path

from bookdesk.library import STATUS_MATCHED, LibraryIndex


def make_index(tmp_path) -> LibraryIndex:
    return LibraryIndex(tmp_path / "library.sqlite")


def test_mark_scanned_inserts_new_item(tmp_path):
    index = make_index(tmp_path)
    index.mark_scanned(Path("/books/Hobbit.epub"), Path("/books"),
                       title="The Hobbit", authors=["J.R.R. Tolkien"])
    items = index.list_books()
    assert len(items) == 1
    assert items[0].title == "The Hobbit"
    assert items[0].authors == ["J.R.R. Tolkien"]


def test_backup_to_copies_all_items(tmp_path):
    index = make_index(tmp_path)
    index.mark_scanned(Path("/books/Test.epub"), Path("/books"), title="Test")
    destination = tmp_path / "backup" / "copy.sqlite"
    index.backup_to(destination)
    assert destination.exists()

    restored = LibraryIndex(destination)
    assert [b.title for b in restored.list_books()] == ["Test"]


def test_mark_scanned_keeps_existing_match_on_rescan(tmp_path):
    index = make_index(tmp_path)
    path = Path("/books/Hobbit.epub")
    index.mark_scanned(path, Path("/books"), title="The Hobbit")
    index.set_match(path, "The Hobbit", ["J.R.R. Tolkien"], "", "", 1937,
                    "", None, "openlibrary", "OL1", 95, STATUS_MATCHED)
    index.mark_scanned(path, Path("/books"), title="The Hobbit")
    items = index.list_books()
    assert len(items) == 1
    assert items[0].status == STATUS_MATCHED
    assert items[0].authors == ["J.R.R. Tolkien"]


def test_forget_missing_removes_gone_files(tmp_path):
    index = make_index(tmp_path)
    root = Path("/books")
    index.mark_scanned(root / "a.epub", root, title="A")
    index.mark_scanned(root / "b.epub", root, title="B")
    removed = index.forget_missing(root, {str(root / "a.epub")})
    assert removed == 1
    remaining = [i.title for i in index.list_books()]
    assert remaining == ["A"]


def test_forget_missing_under_only_touches_given_folder(tmp_path):
    index = make_index(tmp_path)
    root = Path("/books")
    index.mark_scanned(root / "AuthorA" / "1.epub", root, title="A1")
    index.mark_scanned(root / "AuthorB" / "1.epub", root, title="B1")
    removed = index.forget_missing_under(root / "AuthorA", set())
    assert removed == 1
    remaining_titles = {i.title for i in index.list_books()}
    assert remaining_titles == {"B1"}


def test_remove_under_deletes_only_matching_prefix(tmp_path):
    index = make_index(tmp_path)
    root = Path("/books")
    index.mark_scanned(root / "seriesA" / "1.epub", root, title="A1")
    index.mark_scanned(root / "seriesB" / "1.epub", root, title="B1")
    index.remove_under(root / "seriesA")
    remaining = {i.title for i in index.list_books()}
    assert remaining == {"B1"}


def test_series_groups_are_case_insensitive(tmp_path):
    index = make_index(tmp_path)
    root = Path("/books")
    index.mark_scanned(root / "1.epub", root, title="Book 1", series="lotr")
    index.mark_scanned(root / "2.epub", root, title="Book 2", series="LOTR")
    groups = index.series_groups()
    assert len(groups) == 1
    assert len(groups[0][1]) == 2


def test_series_groups_excludes_books_without_series(tmp_path):
    index = make_index(tmp_path)
    root = Path("/books")
    index.mark_scanned(root / "standalone.epub", root, title="Standalone")
    assert index.series_groups() == []


def test_series_groups_prefers_matched_series_name(tmp_path):
    # Grouping ist case-insensitiv (siehe test_series_groups_are_case_insensitive),
    # aber der Anzeigename kommt vom bereits zugeordneten Eintrag - hier "LOTR"
    # statt der rohen Kleinschreibung "lotr" des unmatched Eintrags.
    index = make_index(tmp_path)
    root = Path("/books")
    p1 = root / "1.epub"
    p2 = root / "2.epub"
    index.mark_scanned(p1, root, title="Book 1", series="lotr")
    index.mark_scanned(p2, root, title="Book 2", series="lotr")
    index.set_match(p2, "Book 2", [], "LOTR", "2", 1954,
                    "", None, "openlibrary", "OL2", 90, STATUS_MATCHED)
    groups = index.series_groups()
    assert groups[0][0] == "LOTR"
