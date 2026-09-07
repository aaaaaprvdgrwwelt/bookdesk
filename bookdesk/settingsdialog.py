"""API-Quellen, Schwellwert, Umbenennen-Vorlage und Bibliotheksordner."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QTabWidget, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from deskkit.widgets import RootList

from . import coverstore
from .config import Settings
from .i18n import LANGUAGES, _


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Einstellungen …"))
        self.resize(560, 460)
        self.result_settings: Settings | None = None

        tabs = QTabWidget()
        tabs.addTab(self._library_tab(settings), _("Bibliothek"))
        tabs.addTab(self._sources_tab(settings), _("Quellen"))
        tabs.addTab(self._rename_tab(settings), _("Umbenennen"))
        tabs.addTab(self._general_tab(settings), _("Allgemein"))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    def _library_tab(self, settings: Settings) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(_("Ebook-Ordner")))
        self.book_roots = RootList(settings.book_roots, _)
        layout.addWidget(self.book_roots, 1)

        cover_box = QGroupBox(_("Cover dauerhaft speichern"))
        cover_form = QFormLayout(cover_box)
        self.cover_storage = QComboBox()
        self.cover_storage.addItem(
            _("Nicht speichern (nur fluechtiger Cache)"), coverstore.STORAGE_NONE)
        self.cover_storage.addItem(
            _("Neben der Buchdatei (gleicher Name, .jpg)"),
            coverstore.STORAGE_NEXT_TO_BOOK)
        self.cover_storage.addItem(
            _("In einem eigenen Ordner"), coverstore.STORAGE_DIRECTORY)
        index = self.cover_storage.findData(settings.cover_storage)
        if index >= 0:
            self.cover_storage.setCurrentIndex(index)
        cover_form.addRow(self.cover_storage)

        self.cover_directory = QLineEdit(settings.cover_directory)
        browse_button = QPushButton(_("Durchsuchen …"))
        browse_button.clicked.connect(self._pick_cover_directory)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.cover_directory, 1)
        dir_row.addWidget(browse_button)
        cover_form.addRow(_("Ordner"), dir_row)

        cover_hint = QLabel(_(
            "Wird beim Zuordnen automatisch heruntergeladen und dauerhaft "
            "gespeichert - unabhaengig vom fluechtigen Thumbnail-Cache, "
            "der beim Leeren erneut aus dem Netz laden wuerde."))
        cover_hint.setWordWrap(True)
        cover_form.addRow(cover_hint)

        self._update_cover_directory_enabled()
        self.cover_storage.currentIndexChanged.connect(
            self._update_cover_directory_enabled)

        layout.addWidget(cover_box)
        return widget

    def _update_cover_directory_enabled(self) -> None:
        enabled = self.cover_storage.currentData() == coverstore.STORAGE_DIRECTORY
        self.cover_directory.setEnabled(enabled)

    def _pick_cover_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, _("Ordner fuer Cover waehlen"), self.cover_directory.text())
        if directory:
            self.cover_directory.setText(directory)

    def _sources_tab(self, settings: Settings) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        ol_box = QGroupBox("OpenLibrary")
        self.use_openlibrary = QCheckBox(_("Aktiv (kein API-Key noetig)"))
        self.use_openlibrary.setChecked(settings.use_openlibrary)
        form = QFormLayout(ol_box)
        form.addRow(self.use_openlibrary)

        gb_box = QGroupBox("Google Books")
        self.use_googlebooks = QCheckBox(_("Aktiv (kein API-Key noetig)"))
        self.use_googlebooks.setChecked(settings.use_googlebooks)
        gb_form = QFormLayout(gb_box)
        gb_form.addRow(self.use_googlebooks)
        gb_hint = QLabel(_(
            "Deckt oft Self-Publishing-/Kindle-Titel ab, die OpenLibrary "
            "nicht kennt."))
        gb_hint.setWordWrap(True)
        gb_form.addRow(gb_hint)

        threshold_box = QGroupBox(_("Schwellwert fuer automatische Zuordnung"))
        self.threshold = QSlider(Qt.Horizontal)
        self.threshold.setRange(0, 100)
        self.threshold.setValue(settings.threshold)
        self.threshold_label = QLabel(str(settings.threshold))
        self.threshold.valueChanged.connect(
            lambda v: self.threshold_label.setText(str(v)))
        row = QHBoxLayout(threshold_box)
        row.addWidget(self.threshold, 1)
        row.addWidget(self.threshold_label)

        layout.addWidget(ol_box)
        layout.addWidget(gb_box)
        layout.addWidget(threshold_box)
        layout.addStretch(1)
        return widget

    def _rename_tab(self, settings: Settings) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(
            _("Platzhalter: {author} {series} {series_index} {title} {year} {ext}")))
        self.rename_template = QLineEdit(settings.rename_template)
        layout.addWidget(self.rename_template)
        layout.addStretch(1)
        return widget

    def _general_tab(self, settings: Settings) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.language = QComboBox()
        for code, label in LANGUAGES.items():
            self.language.addItem(label, code)
        index = self.language.findData(settings.language)
        if index >= 0:
            self.language.setCurrentIndex(index)
        form.addRow(_("Sprache"), self.language)
        return widget

    # ------------------------------------------------------------------
    def _accept(self) -> None:
        self.result_settings = Settings(
            book_roots=self.book_roots.roots(),
            use_openlibrary=self.use_openlibrary.isChecked(),
            use_googlebooks=self.use_googlebooks.isChecked(),
            threshold=self.threshold.value(),
            rename_template=self.rename_template.text().strip(),
            language=self.language.currentData(),
            cover_storage=self.cover_storage.currentData(),
            cover_directory=self.cover_directory.text().strip(),
        )
        self.accept()
