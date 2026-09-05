"""Lese-Fenster: EPUB kapitelweise (Text, mit Schriftgroesse und
Volltextsuche ueber alle Kapitel), PDF seitenweise (Bild, mit Zoom und
Seitensuche ueber PyMuPDFs Textsuche).

Bewusst schlank fuer v1 - keine Lesezeichen, kein Doppelseiten-Modus wie
beim comicdesk-Reader, keine Textmarkierung bei der PDF-Suche (nur Sprung
zur Fundstelle-Seite). Die letzte Position (Kapitel-Index bzw. Seitenzahl)
wird in `library.last_position` gemerkt.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPixmap, QTextDocument
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QTextBrowser, QVBoxLayout,
)

from .formats import base as formats
from .i18n import _
from .library import Item, LibraryIndex

#: Grenzen fuer die EPUB-Schriftgroessen-Anpassung (QTextEdit.zoomIn-Schritte).
MAX_ZOOM_STEPS = 12
MIN_ZOOM_STEPS = -6
#: Grenzen fuer den PDF-Zoom, als Faktor auf die Basisbreite (formats.page_image).
PDF_BASE_WIDTH = 1400
MIN_PDF_ZOOM = 0.5
MAX_PDF_ZOOM = 2.5


class ReaderWindow(QDialog):
    def __init__(self, item: Item, library: LibraryIndex, parent=None):
        super().__init__(parent)
        self.setWindowTitle(item.title or Path(item.path).name)
        self.resize(820, 900)
        self.item = item
        self.library = library
        self.path = Path(item.path)
        self.is_pdf = self.path.suffix.lower() in formats.PDF_EXTENSIONS
        self._zoom_steps = 0
        self._pdf_zoom = 1.0

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

        # --- Zoom -------------------------------------------------------
        zoom_out = QPushButton("A-")
        zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out.setToolTip(_("Kleiner"))
        zoom_out.clicked.connect(self._zoom_out)
        zoom_reset = QPushButton("100%")
        zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        zoom_reset.setToolTip(_("Schriftgroesse zuruecksetzen"))
        zoom_reset.clicked.connect(self._zoom_reset)
        zoom_in = QPushButton("A+")
        zoom_in.setShortcut(QKeySequence("Ctrl+="))
        zoom_in.setToolTip(_("Groesser"))
        zoom_in.clicked.connect(self._zoom_in)

        # --- Suche --------------------------------------------------------
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(_("Im Buch suchen …"))
        self.search_box.returnPressed.connect(lambda: self._search(forward=True))
        search_prev = QPushButton("◀")
        search_prev.setToolTip(_("Vorheriger Treffer"))
        search_prev.clicked.connect(lambda: self._search(forward=False))
        search_next = QPushButton("▶")
        search_next.setToolTip(_("Naechster Treffer"))
        search_next.clicked.connect(lambda: self._search(forward=True))
        self.search_status = QLabel()

        tools = QHBoxLayout()
        tools.addWidget(zoom_out)
        tools.addWidget(zoom_reset)
        tools.addWidget(zoom_in)
        tools.addSpacing(16)
        tools.addWidget(self.search_box, 1)
        tools.addWidget(search_prev)
        tools.addWidget(search_next)
        tools.addWidget(self.search_status)

        layout = QVBoxLayout(self)
        layout.addLayout(tools)
        layout.addWidget(content, 1)
        layout.addLayout(nav)
        self._show_current()

    # --- Zoom ------------------------------------------------------------
    def _zoom_in(self) -> None:
        if self.is_pdf:
            self._pdf_zoom = min(MAX_PDF_ZOOM, round(self._pdf_zoom + 0.1, 2))
            self._show_current()
        elif self._zoom_steps < MAX_ZOOM_STEPS:
            self.viewer.zoomIn(1)
            self._zoom_steps += 1

    def _zoom_out(self) -> None:
        if self.is_pdf:
            self._pdf_zoom = max(MIN_PDF_ZOOM, round(self._pdf_zoom - 0.1, 2))
            self._show_current()
        elif self._zoom_steps > MIN_ZOOM_STEPS:
            self.viewer.zoomOut(1)
            self._zoom_steps -= 1

    def _zoom_reset(self) -> None:
        if self.is_pdf:
            self._pdf_zoom = 1.0
            self._show_current()
        else:
            if self._zoom_steps > 0:
                self.viewer.zoomOut(self._zoom_steps)
            elif self._zoom_steps < 0:
                self.viewer.zoomIn(-self._zoom_steps)
            self._zoom_steps = 0

    # --- Suche -----------------------------------------------------------
    def _chapter_plain_text(self, index: int) -> str:
        doc = QTextDocument()
        doc.setHtml(self.chapters[index].html.decode("utf-8", errors="replace"))
        return doc.toPlainText()

    def _search(self, forward: bool = True) -> None:
        query = self.search_box.text().strip()
        if not query or self.total == 0:
            return
        if self.is_pdf:
            self._search_pdf(query, forward)
        else:
            self._search_epub(query, forward)

    def _search_pdf(self, query: str, forward: bool) -> None:
        pages = formats.find_pages(self.path, query)
        if not pages:
            self.search_status.setText(_("Nicht gefunden."))
            return
        after = [p for p in pages if p > self.index]
        before = [p for p in pages if p < self.index]
        if forward:
            target = after[0] if after else pages[0]
        else:
            target = before[-1] if before else pages[-1]
        self.index = target
        self._show_current()
        self.search_status.setText(
            _("Treffer auf {n} Seite(n).").format(n=len(pages)))

    def _search_epub(self, query: str, forward: bool) -> None:
        find_flags = QTextDocument.FindFlag(0) if forward \
            else QTextDocument.FindBackward
        if self.viewer.find(query, find_flags):
            self.search_status.setText("")
            return
        # Nicht (mehr) im aktuellen Kapitel ab der Cursorposition - der
        # Reihe nach durch die anderen Kapitel, beim letzten/ersten wieder
        # von vorn (wie eine uebliche "naechster Treffer"-Suche).
        steps = range(1, self.total + 1) if forward else range(-1, -self.total - 1, -1)
        for step in steps:
            index = (self.index + step) % self.total
            if query.lower() in self._chapter_plain_text(index).lower():
                self.index = index
                self._show_current()
                cursor = self.viewer.textCursor()
                cursor.movePosition(
                    cursor.MoveOperation.Start if forward
                    else cursor.MoveOperation.End)
                self.viewer.setTextCursor(cursor)
                self.viewer.find(query, find_flags)
                self.search_status.setText("")
                return
        self.search_status.setText(_("Nicht gefunden."))

    # --- Anzeige -----------------------------------------------------------
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
            width = round(PDF_BASE_WIDTH * self._pdf_zoom)
            data = formats.page_image(self.path, self.index, max_width=width)
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
