"""Suchfeld im Hauptfenster: sucht ueber Titel, Autor UND Serienname - siehe
_fill_books(). Ohne den Serien-Abgleich findet eine Suche nach dem
Serientitel nur den einen Band, dessen eigener Titel zufaellig genauso
heisst wie die Serie, nicht die uebrigen Baende (realer Fall: eine
Episodenreihe, bei der jeder Band einen eigenen Titel traegt und nur ueber
`series` zusammengehalten wird).

MainWindow() baut ohne Pfad eine LibraryIndex() an der Standard-XDG-
Position auf - deshalb hier immer mit isolierten XDG_*-Verzeichnissen
arbeiten, niemals mit der echten Bibliothek des Nutzers (siehe
CLAUDE.md-Historie / vorherige Session)."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

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


def _seed_series(library, root: Path) -> None:
    episodes = [
        ("Raumschiff Zu Verkaufen", "1.0", ["M.R. Forbes"]),
        ("Kopfschmerzen", "2.0", ["Andreas Straube"]),
        ("Die letzte Chance", "10.0", ["Jean-Paul Sartre"]),
    ]
    for i, (title, series_index, authors) in enumerate(episodes):
        path = root / f"{i:02d} {title}.epub"
        path.write_bytes(b"")
        library.mark_scanned(path, root, title, authors,
                             "Raumschiff zu Verkaufen", series_index, None, "")


def test_search_by_series_name_finds_all_episodes(isolated_mainwindow, tmp_path):
    win = isolated_mainwindow
    _seed_series(win.library, tmp_path)
    win.search_edit.setText("raumschiff zu verkaufen")
    titles = {win.book_list.item(i).text() for i in range(win.book_list.count())}
    assert titles == {"Raumschiff Zu Verkaufen", "Kopfschmerzen", "Die letzte Chance"}


def test_search_by_own_title_still_narrows_to_one_episode(isolated_mainwindow, tmp_path):
    win = isolated_mainwindow
    _seed_series(win.library, tmp_path)
    win.search_edit.setText("letzte chance")
    titles = {win.book_list.item(i).text() for i in range(win.book_list.count())}
    assert titles == {"Die letzte Chance"}
