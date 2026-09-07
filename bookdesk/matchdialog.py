"""Treffer von Hand auswaehlen, wenn die Automatik unsicher war oder nichts
fand - oder, wenn auch keine Online-Quelle etwas findet (z. B. bei sehr
kleinen Self-Publishing-Reihen, die weder OpenLibrary noch Google Books
kennen), die Angaben direkt selbst eintragen."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QTabWidget,
    QVBoxLayout, QWidget,
)

from .i18n import _
from .library import Item, LibraryIndex, STATUS_MATCHED
from .matcher import MatchConfig, collect_candidates
from .providers.base import BookInfo, Candidate, SearchQuery
from .thumbs import CoverLoader

TAB_SEARCH = 0
TAB_MANUAL = 1


class MatchDialog(QDialog):
    def __init__(self, item: Item, config: MatchConfig, library: LibraryIndex,
                loader: CoverLoader, parent=None):
        super().__init__(parent)
        self.item = item
        self.config = config
        self.library = library
        self.loader = loader
        self.loader.ready.connect(self._on_cover)
        self._candidates: list[Candidate] = []

        self.setWindowTitle(_("Treffer waehlen") + f" - {item.title}")
        self.resize(560, 560)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_search_tab(), _("Suche"))
        self.tabs.addTab(self._build_manual_tab(), _("Von Hand eintragen"))
        self.tabs.currentChanged.connect(self._update_apply_enabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.apply_button = buttons.addButton(
            _("Uebernehmen"), QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(buttons)

        self._search()
        self._update_apply_enabled()

    # -- Tab 1: Online-Suche ------------------------------------------
    def _build_search_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.query_edit = QLineEdit(self.item.title)
        self.query_edit.returnPressed.connect(self._search)
        search_button = QPushButton(_("Suchen"))
        search_button.clicked.connect(self._search)
        search_row = QHBoxLayout()
        search_row.addWidget(self.query_edit, 1)
        search_row.addWidget(search_button)

        self.results = QListWidget()
        self.results.itemSelectionChanged.connect(self._update_apply_enabled)

        layout.addLayout(search_row)
        layout.addWidget(self.results, 1)
        return widget

    def _search(self) -> None:
        self.results.clear()
        query = SearchQuery(
            title=self.query_edit.text().strip(), authors=self.item.authors)
        self._candidates = collect_candidates(query, self.config)
        for candidate in self._candidates:
            authors = ", ".join(candidate.authors)
            year = f" ({candidate.year})" if candidate.year else ""
            text = f"{candidate.title}{year}  ·  {authors}  ·  {candidate.score}%"
            list_item = QListWidgetItem(text)
            list_item.setData(Qt.UserRole, candidate)
            if candidate.cover_url:
                pm = self.loader.get(candidate.cover_url)
                if pm and not pm.isNull():
                    list_item.setIcon(QIcon(pm))
            self.results.addItem(list_item)
        self._update_apply_enabled()

    def _on_cover(self, key: str, pixmap) -> None:
        if pixmap.isNull():
            return
        for row in range(self.results.count()):
            list_item = self.results.item(row)
            candidate: Candidate = list_item.data(Qt.UserRole)
            if candidate.cover_url == key:
                list_item.setIcon(QIcon(pixmap))

    # -- Tab 2: von Hand eintragen --------------------------------------
    def _build_manual_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.manual_title = QLineEdit(self.item.title)
        self.manual_title.textChanged.connect(self._update_apply_enabled)
        form.addRow(_("Titel"), self.manual_title)

        self.manual_authors = QLineEdit(", ".join(self.item.authors))
        form.addRow(_("Autor(en), durch Komma getrennt"), self.manual_authors)

        self.manual_series = QLineEdit(self.item.series)
        form.addRow(_("Serie"), self.manual_series)

        self.manual_series_index = QLineEdit(self.item.series_index)
        form.addRow(_("Band"), self.manual_series_index)

        self.manual_year = QLineEdit(str(self.item.year) if self.item.year else "")
        form.addRow(_("Jahr"), self.manual_year)

        self.manual_description = QPlainTextEdit(self.item.description)
        self.manual_description.setMaximumHeight(120)
        form.addRow(_("Beschreibung"), self.manual_description)

        self.manual_cover_url = QLineEdit(self.item.cover_url or "")
        self.manual_cover_url.setPlaceholderText(_("optional, https://…"))
        form.addRow(_("Cover-URL"), self.manual_cover_url)

        return widget

    def _manual_year(self) -> int | None:
        text = self.manual_year.text().strip()
        return int(text) if text.isdigit() else None

    # --------------------------------------------------------------------
    def _update_apply_enabled(self) -> None:
        if self.tabs.currentIndex() == TAB_MANUAL:
            enabled = bool(self.manual_title.text().strip())
        else:
            enabled = bool(self.results.selectedItems())
        self.apply_button.setEnabled(enabled)

    def _apply(self) -> None:
        if self.tabs.currentIndex() == TAB_MANUAL:
            self._apply_manual()
        else:
            self._apply_search()

    def _apply_search(self) -> None:
        items = self.results.selectedItems()
        if not items:
            return
        candidate: Candidate = items[0].data(Qt.UserRole)
        provider = next(
            (p for p in self.config.providers if p.name == candidate.source), None)
        info = provider.details(candidate) if provider else BookInfo(
            title=candidate.title, authors=candidate.authors, year=candidate.year,
            cover_url=candidate.cover_url, source=candidate.source,
            external_id=candidate.external_id)
        self.library.set_match(
            Path(self.item.path), info.title, info.authors, self.item.series,
            self.item.series_index, info.year, info.description, info.cover_url,
            info.source, info.external_id, 100, STATUS_MATCHED,
            _("von Hand gewaehlt"))
        self.accept()

    def _apply_manual(self) -> None:
        title = self.manual_title.text().strip()
        if not title:
            return
        authors = [a.strip() for a in self.manual_authors.text().split(",") if a.strip()]
        self.library.set_match(
            Path(self.item.path), title, authors,
            self.manual_series.text().strip(),
            self.manual_series_index.text().strip(), self._manual_year(),
            self.manual_description.toPlainText().strip(),
            self.manual_cover_url.text().strip() or None,
            "", "", 100, STATUS_MATCHED, _("von Hand eingetragen"))
        self.accept()
