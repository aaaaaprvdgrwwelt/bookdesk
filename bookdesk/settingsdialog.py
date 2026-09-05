"""API-Quellen, Schwellwert, Umbenennen-Vorlage und Bibliotheksordner."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QSlider, QTabWidget, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from deskkit.widgets import RootList

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
        layout.addWidget(self.book_roots)
        return widget

    def _sources_tab(self, settings: Settings) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        ol_box = QGroupBox("OpenLibrary")
        self.use_openlibrary = QCheckBox(_("Aktiv (kein API-Key noetig)"))
        self.use_openlibrary.setChecked(settings.use_openlibrary)
        form = QFormLayout(ol_box)
        form.addRow(self.use_openlibrary)

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
            threshold=self.threshold.value(),
            rename_template=self.rename_template.text().strip(),
            language=self.language.currentData(),
        )
        self.accept()
