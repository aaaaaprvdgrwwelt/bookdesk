"""Cover-Speicherort-Einstellungen im Einstellungen-Dialog."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from bookdesk import coverstore
from bookdesk.config import Settings
from bookdesk.settingsdialog import SettingsDialog

_app = QApplication.instance() or QApplication([])


def test_defaults_to_none_and_directory_field_disabled():
    dialog = SettingsDialog(Settings())
    assert dialog.cover_storage.currentData() == coverstore.STORAGE_NONE
    assert dialog.cover_directory.isEnabled() is False


def test_directory_field_enables_when_directory_mode_selected():
    dialog = SettingsDialog(Settings())
    index = dialog.cover_storage.findData(coverstore.STORAGE_DIRECTORY)
    dialog.cover_storage.setCurrentIndex(index)
    assert dialog.cover_directory.isEnabled() is True


def test_accept_carries_cover_settings_into_result(tmp_path):
    dialog = SettingsDialog(Settings())
    index = dialog.cover_storage.findData(coverstore.STORAGE_DIRECTORY)
    dialog.cover_storage.setCurrentIndex(index)
    dialog.cover_directory.setText(str(tmp_path))
    dialog._accept()
    assert dialog.result_settings.cover_storage == coverstore.STORAGE_DIRECTORY
    assert dialog.result_settings.cover_directory == str(tmp_path)


def test_existing_settings_are_prefilled():
    settings = Settings(cover_storage=coverstore.STORAGE_NEXT_TO_BOOK)
    dialog = SettingsDialog(settings)
    assert dialog.cover_storage.currentData() == coverstore.STORAGE_NEXT_TO_BOOK
