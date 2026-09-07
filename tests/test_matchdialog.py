"""Tests fuer den 'Treffer waehlen'-Dialog - vor allem den Tab 'Von Hand
eintragen' (fuer Titel, die keine Online-Quelle findet)."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from bookdesk.library import STATUS_MATCHED, LibraryIndex
from bookdesk.matcher import MatchConfig
from bookdesk.matchdialog import TAB_MANUAL, TAB_SEARCH, MatchDialog
from bookdesk.thumbs import CoverLoader

_app = QApplication.instance() or QApplication([])


def make_dialog(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    library = LibraryIndex(tmp_path / "library.sqlite")
    path = tmp_path / "book.epub"
    path.write_bytes(b"")
    library.mark_scanned(path, tmp_path, title="Die letzte Chance",
                         authors=["M. R. Forbes"], series="Raumschiff zu Verkaufen",
                         series_index="10.0")
    item = library.get(path)
    config = MatchConfig(providers=[])  # keine Online-Quelle noetig fuer diese Tests
    loader = CoverLoader()
    dialog = MatchDialog(item, config, library, loader)
    return dialog, library, path


def test_manual_tab_prefills_from_existing_item(tmp_path, monkeypatch):
    dialog, library, path = make_dialog(tmp_path, monkeypatch)
    assert dialog.manual_title.text() == "Die letzte Chance"
    assert dialog.manual_authors.text() == "M. R. Forbes"
    assert dialog.manual_series.text() == "Raumschiff zu Verkaufen"
    assert dialog.manual_series_index.text() == "10.0"
    library.close()


def test_apply_button_disabled_without_selection_on_search_tab(tmp_path, monkeypatch):
    dialog, library, path = make_dialog(tmp_path, monkeypatch)
    dialog.tabs.setCurrentIndex(TAB_SEARCH)
    assert dialog.apply_button.isEnabled() is False
    library.close()


def test_apply_button_enabled_on_manual_tab_with_title(tmp_path, monkeypatch):
    dialog, library, path = make_dialog(tmp_path, monkeypatch)
    dialog.tabs.setCurrentIndex(TAB_MANUAL)
    assert dialog.apply_button.isEnabled() is True
    library.close()


def test_apply_button_disabled_on_manual_tab_with_empty_title(tmp_path, monkeypatch):
    dialog, library, path = make_dialog(tmp_path, monkeypatch)
    dialog.tabs.setCurrentIndex(TAB_MANUAL)
    dialog.manual_title.setText("")
    assert dialog.apply_button.isEnabled() is False
    library.close()


def test_manual_apply_writes_item_to_library(tmp_path, monkeypatch):
    dialog, library, path = make_dialog(tmp_path, monkeypatch)
    dialog.tabs.setCurrentIndex(TAB_MANUAL)
    dialog.manual_title.setText("Last Licks")
    dialog.manual_authors.setText("M. R. Forbes")
    dialog.manual_series.setText("Raumschiff zu Verkaufen")
    dialog.manual_series_index.setText("10")
    dialog.manual_year.setText("2023")
    dialog.manual_description.setPlainText("Ein Raumschiff-Abenteuer.")
    dialog.manual_cover_url.setText("https://example.invalid/cover.jpg")

    dialog._apply()

    item = library.get(path)
    assert item.title == "Last Licks"
    assert item.authors == ["M. R. Forbes"]
    assert item.series == "Raumschiff zu Verkaufen"
    assert item.series_index == "10"
    assert item.year == 2023
    assert item.description == "Ein Raumschiff-Abenteuer."
    assert item.cover_url == "https://example.invalid/cover.jpg"
    assert item.status == STATUS_MATCHED
    assert item.note == "von Hand eingetragen"
    assert item.source == ""
    library.close()


def test_manual_apply_without_year_leaves_it_none(tmp_path, monkeypatch):
    dialog, library, path = make_dialog(tmp_path, monkeypatch)
    dialog.tabs.setCurrentIndex(TAB_MANUAL)
    dialog.manual_year.setText("")

    dialog._apply()

    item = library.get(path)
    assert item.year is None
    library.close()


def test_manual_apply_does_nothing_with_blank_title(tmp_path, monkeypatch):
    dialog, library, path = make_dialog(tmp_path, monkeypatch)
    dialog.tabs.setCurrentIndex(TAB_MANUAL)
    dialog.manual_title.setText("   ")

    before = library.get(path)
    dialog._apply_manual()
    after = library.get(path)

    assert after.title == before.title
    assert after.status == before.status
    library.close()
