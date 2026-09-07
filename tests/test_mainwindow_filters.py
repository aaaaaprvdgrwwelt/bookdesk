"""Zusatzfilter in der Serien-Liste: "Nicht zugeordnet" und "Ohne Serie" -
siehe _fill_series()/_fill_books() in mainwindow.py.

MainWindow() baut ohne Pfad eine LibraryIndex() an der Standard-XDG-
Position auf - deshalb hier immer mit isolierten XDG_*-Verzeichnissen
arbeiten, niemals mit der echten Bibliothek des Nutzers."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from bookdesk.library import STATUS_MATCHED, STATUS_UNSURE

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def isolated_mainwindow(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    from bookdesk.mainwindow import MainWindow
    win = MainWindow()
    yield win
    win.close()


def _seed(library, root: Path) -> None:
    # matched, mit Serie
    p1 = root / "1.epub"
    p1.write_bytes(b"")
    library.mark_scanned(p1, root, "Serie", ["Autor"], "Testserie", "1")
    library.set_match(p1, "Serie", ["Autor"], "Testserie", "1", 2020, "", None,
                      "openlibrary", "x1", 95, STATUS_MATCHED)

    # unsure, ohne Serie
    p2 = root / "2.epub"
    p2.write_bytes(b"")
    library.mark_scanned(p2, root, "Einzelband", ["Autor"])
    library.set_status(p2, STATUS_UNSURE, "kein Treffer")

    # unmatched (nie zugeordnet), ohne Serie
    p3 = root / "3.epub"
    p3.write_bytes(b"")
    library.mark_scanned(p3, root, "Noch nicht zugeordnet", ["Autor"])


def test_unmatched_and_no_series_filters_are_always_shown(isolated_mainwindow, tmp_path):
    win = isolated_mainwindow
    _seed(win.library, tmp_path)
    win.refresh_view()
    labels = [win.series_list.item(i).text() for i in range(win.series_list.count())]
    assert any(label.startswith("Nicht zugeordnet") for label in labels)
    assert any(label.startswith("Ohne Serie") for label in labels)


def test_unmatched_filter_shows_only_non_matched_items(isolated_mainwindow, tmp_path):
    win = isolated_mainwindow
    _seed(win.library, tmp_path)
    win.refresh_view()

    from PySide6.QtCore import Qt

    from bookdesk.mainwindow import FILTER_UNMATCHED
    target = next(win.series_list.item(i) for i in range(win.series_list.count())
                 if win.series_list.item(i).data(Qt.UserRole) is FILTER_UNMATCHED)
    win.series_list.setCurrentItem(target)
    target.setSelected(True)
    win._on_series_selected()

    titles = {win.book_list.item(i).text() for i in range(win.book_list.count())}
    assert titles == {"Einzelband", "Noch nicht zugeordnet"}


def test_no_series_filter_shows_only_items_without_series(isolated_mainwindow, tmp_path):
    win = isolated_mainwindow
    _seed(win.library, tmp_path)
    win.refresh_view()

    from PySide6.QtCore import Qt

    from bookdesk.mainwindow import FILTER_NO_SERIES
    target = next(win.series_list.item(i) for i in range(win.series_list.count())
                 if win.series_list.item(i).data(Qt.UserRole) is FILTER_NO_SERIES)
    win.series_list.setCurrentItem(target)
    target.setSelected(True)
    win._on_series_selected()

    titles = {win.book_list.item(i).text() for i in range(win.book_list.count())}
    assert titles == {"Einzelband", "Noch nicht zugeordnet"}


def test_unmatched_counter_updates_after_matching(isolated_mainwindow, tmp_path):
    win = isolated_mainwindow
    _seed(win.library, tmp_path)
    win.refresh_view()
    labels_before = [win.series_list.item(i).text() for i in range(win.series_list.count())]
    unmatched_before = next(label for label in labels_before if label.startswith("Nicht zugeordnet"))
    assert "(2)" in unmatched_before

    win.library.set_match(tmp_path / "2.epub", "Einzelband", ["Autor"], "", "",
                          2021, "", None, "openlibrary", "y1", 95, STATUS_MATCHED)
    win.refresh_view()
    labels_after = [win.series_list.item(i).text() for i in range(win.series_list.count())]
    unmatched_after = next(label for label in labels_after if label.startswith("Nicht zugeordnet"))
    assert "(1)" in unmatched_after
