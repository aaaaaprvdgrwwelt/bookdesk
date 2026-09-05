"""Lese-Fenster: EPUB kapitelweise (Text), PDF seitenweise (Bild).

Bewusst schlank fuer v1 - kein Zoom, keine Lesezeichen, kein Doppelseiten-
Modus wie beim comicdesk-Reader. Die letzte Position (Kapitel-Index bzw.
Seitenzahl) wird in `library.last_position` gemerkt.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QTextBrowser,
    QVBoxLayout,
)

from .formats import base as formats
from .i18n import _
from .library import Item, LibraryIndex


class ReaderWindow(QDialog):
    def __init__(self, item: Item, library: LibraryIndex, parent=None):
        super().__init__(parent)
        self.setWindowTitle(item.title or Path(item.path).name)
        self.resize(820, 900)
        self.item = item
        self.library = library
        self.path = Path(item.path)
        self.is_pdf = self.path.suffix.lower() in formats.PDF_EXTENSIONS

        if self.is_pdf:
            self.total = formats.page_count(self.path)
            self.viewer = QLabel()
            self.viewer.setAlignment(Qt.AlignCenter)
            scroll = QScrollArea()
            scroll.setWidget(self.viewer)
            scroll.setWidgetResizable(True)
            content = scroll
        else:
            self.chapters = formats.chapters(self.path)
            self.total = len(self.chapters)
            self.viewer = QTextBrowser()
            self.viewer.setOpenExternalLinks(False)
            content = self.viewer

        self.index = min(max(item.last_position, 0), max(self.total - 1, 0))

        self.prev_button = QPushButton(_("Zurueck"))
        self.prev_button.setShortcut(QKeySequence("Left"))
        self.prev_button.clicked.connect(self._prev)
        self.position_label = QLabel()
        self.next_button = QPushButton(_("Weiter"))
        self.next_button.setShortcut(QKeySequence("Right"))
        self.next_button.clicked.connect(self._next)

        nav = QHBoxLayout()
        nav.addWidget(self.prev_button)
        nav.addWidget(self.position_label, 1, Qt.AlignCenter)
        nav.addWidget(self.next_button)

        layout = QVBoxLayout(self)
        layout.addWidget(content, 1)
        layout.addLayout(nav)
        self._show_current()

    def _show_current(self) -> None:
        if self.total == 0:
            if self.is_pdf:
                self.viewer.setText(_("Keine lesbaren Seiten gefunden."))
            else:
                self.viewer.setPlainText(_("Keine lesbaren Kapitel gefunden."))
            self.position_label.setText("")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return

        if self.is_pdf:
            data = formats.page_image(self.path, self.index)
            pixmap = QPixmap()
            if data:
                pixmap.loadFromData(data)
            self.viewer.setPixmap(pixmap)
        else:
            html = self.chapters[self.index].html.decode("utf-8", errors="replace")
            self.viewer.setHtml(html)

        self.position_label.setText(f"{self.index + 1} / {self.total}")
        self.prev_button.setEnabled(self.index > 0)
        self.next_button.setEnabled(self.index < self.total - 1)
        self.library.set_last_position(self.path, self.index)

    def _prev(self) -> None:
        if self.index > 0:
            self.index -= 1
            self._show_current()

    def _next(self) -> None:
        if self.index < self.total - 1:
            self.index += 1
            self._show_current()
