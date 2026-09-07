"""Treffer von Hand auswaehlen, wenn die Automatik unsicher war oder nichts fand."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout,
)

from .i18n import _
from .library import Item, LibraryIndex, STATUS_MATCHED
from .matcher import MatchConfig, collect_candidates
from .providers.base import BookInfo, Candidate, SearchQuery
from .thumbs import CoverLoader


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

        self.query_edit = QLineEdit(item.title)
        self.query_edit.returnPressed.connect(self._search)
        search_button = QPushButton(_("Suchen"))
        search_button.clicked.connect(self._search)
        search_row = QHBoxLayout()
        search_row.addWidget(self.query_edit, 1)
        search_row.addWidget(search_button)

        self.results = QListWidget()

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.apply_button = buttons.addButton(
            _("Uebernehmen"), QDialogButtonBox.AcceptRole)
        self.apply_button.setEnabled(False)
        self.results.itemSelectionChanged.connect(
            lambda: self.apply_button.setEnabled(bool(self.results.selectedItems())))
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(search_row)
        layout.addWidget(self.results, 1)
        layout.addWidget(buttons)
        self._search()

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

    def _on_cover(self, key: str, pixmap) -> None:
        if pixmap.isNull():
            return
        for row in range(self.results.count()):
            list_item = self.results.item(row)
            candidate: Candidate = list_item.data(Qt.UserRole)
            if candidate.cover_url == key:
                list_item.setIcon(QIcon(pixmap))

    def _apply(self) -> None:
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
