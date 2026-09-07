"""Tests fuer seriesdialog.py: Serie (und bei einem Buch: Band) fuer eine
Auswahl von Buechern zuweisen, unabhaengig vom Metadaten-Abgleich."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from bookdesk.library import STATUS_MATCHED, LibraryIndex
from bookdesk.seriesdialog import SeriesDialog

_app = QApplication.instance() or QApplication([])


def make_library(tmp_path) -> LibraryIndex:
    return LibraryIndex(tmp_path / "library.sqlite")


def add_book(library, tmp_path, name, **overrides):
    path = tmp_path / name
    path.write_bytes(b"")
    kwargs = dict(title=name, authors=["Autor"])
    kwargs.update(overrides)
    library.mark_scanned(path, tmp_path, **kwargs)
    return path


def test_single_book_prefills_existing_series_and_index(tmp_path):
    library = make_library(tmp_path)
    path = add_book(library, tmp_path, "a.epub", series="Testserie",
                    series_index="3")
    item = library.get(path)
    dialog = SeriesDialog([item], library)
    assert dialog.series_edit.text() == "Testserie"
    assert dialog.index_edit.text() == "3"
    library.close()


def test_single_book_sets_series_and_index_without_touching_other_fields(tmp_path):
    library = make_library(tmp_path)
    path = add_book(library, tmp_path, "a.epub")
    library.set_match(path, "Titel", ["Autor"], "", "", 2020, "Beschreibung",
                      None, "openlibrary", "x1", 95, STATUS_MATCHED)

    item = library.get(path)
    dialog = SeriesDialog([item], library)
    dialog.series_edit.setText("Neue Serie")
    dialog.index_edit.setText("5")
    dialog._accept()

    updated = library.get(path)
    assert updated.series == "Neue Serie"
    assert updated.series_index == "5"
    # Unveraendert:
    assert updated.title == "Titel"
    assert updated.description == "Beschreibung"
    assert updated.status == STATUS_MATCHED
    assert updated.source == "openlibrary"
    library.close()


def test_multiple_books_auto_numbers_in_selection_order(tmp_path):
    library = make_library(tmp_path)
    paths = [add_book(library, tmp_path, f"{i}.epub") for i in range(3)]
    items = [library.get(p) for p in paths]

    dialog = SeriesDialog(items, library)
    assert dialog.index_edit is None
    dialog.series_edit.setText("Serie")
    dialog.auto_number.setChecked(True)
    dialog.start_number.setValue(1)
    dialog._accept()

    updated = [library.get(p) for p in paths]
    assert [i.series for i in updated] == ["Serie"] * 3
    assert [i.series_index for i in updated] == ["1", "2", "3"]
    library.close()


def test_multiple_books_auto_numbering_can_start_elsewhere(tmp_path):
    library = make_library(tmp_path)
    paths = [add_book(library, tmp_path, f"{i}.epub") for i in range(2)]
    items = [library.get(p) for p in paths]

    dialog = SeriesDialog(items, library)
    dialog.series_edit.setText("Serie")
    dialog.start_number.setValue(10)
    dialog._accept()

    updated = [library.get(p) for p in paths]
    assert [i.series_index for i in updated] == ["10", "11"]
    library.close()


def test_multiple_books_without_auto_numbering_keeps_existing_index(tmp_path):
    library = make_library(tmp_path)
    p1 = add_book(library, tmp_path, "a.epub", series_index="1")
    p2 = add_book(library, tmp_path, "b.epub", series_index="9")
    items = [library.get(p1), library.get(p2)]

    dialog = SeriesDialog(items, library)
    dialog.series_edit.setText("Serie")
    dialog.auto_number.setChecked(False)
    dialog._accept()

    assert library.get(p1).series_index == "1"
    assert library.get(p2).series_index == "9"
    assert library.get(p1).series == "Serie"
    library.close()


def test_prefills_series_only_when_selection_shares_one(tmp_path):
    library = make_library(tmp_path)
    p1 = add_book(library, tmp_path, "a.epub", series="X")
    p2 = add_book(library, tmp_path, "b.epub", series="Y")
    items = [library.get(p1), library.get(p2)]

    dialog = SeriesDialog(items, library)
    assert dialog.series_edit.text() == ""
    library.close()


def test_blank_series_does_not_apply(tmp_path):
    library = make_library(tmp_path)
    path = add_book(library, tmp_path, "a.epub", series="Bestehend")
    item = library.get(path)

    dialog = SeriesDialog([item], library)
    dialog.series_edit.setText("   ")
    dialog._accept()

    assert library.get(path).series == "Bestehend"
    library.close()


def test_library_set_series_updates_only_series_fields(tmp_path):
    library = make_library(tmp_path)
    path = add_book(library, tmp_path, "a.epub")
    library.set_match(path, "Titel", ["Autor"], "", "", 2020, "", None,
                      "openlibrary", "x1", 95, STATUS_MATCHED)
    library.set_series(Path(path), "Serie", "2")
    item = library.get(path)
    assert item.series == "Serie"
    assert item.series_index == "2"
    assert item.title == "Titel"
    assert item.status == STATUS_MATCHED
    library.close()
