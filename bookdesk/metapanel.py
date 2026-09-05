"""Detailanzeige: Cover plus Metadaten des ausgewaehlten Buchs."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel, QPlainTextEdit, QSizePolicy, QVBoxLayout, QWidget,
)

from .i18n import _
from .library import Item
from .thumbs import CoverLoader

COVER_W = 220

SOURCE_NAMES = {"openlibrary": "OpenLibrary"}


class MetaPanel(QWidget):
    def __init__(self, loader: CoverLoader, parent=None):
        super().__init__(parent)
        self._loader = loader
        self._loader.ready.connect(self._on_cover)
        self._key = ""

        self.cover = QLabel()
        self.cover.setFixedWidth(COVER_W)
        self.cover.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.cover.setStyleSheet("border-radius: 6px;")

        self.title = QLabel()
        self.title.setWordWrap(True)
        font = self.title.font()
        font.setPointSize(font.pointSize() + 3)
        font.setBold(True)
        self.title.setFont(font)

        self.subtitle = QLabel()
        self.subtitle.setWordWrap(True)

        self.overview = QPlainTextEdit()
        self.overview.setReadOnly(True)
        self.overview.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.source_label = QLabel()
        self.source_label.setOpenExternalLinks(True)
        self.source_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.source_label.setStyleSheet("font-size: 90%;")

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.path_label.setStyleSheet("color: palette(mid); font-size: 90%;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.cover, 0, Qt.AlignHCenter)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.overview, 1)
        layout.addWidget(self.source_label)
        layout.addWidget(self.path_label)
        self.clear()

    def clear(self) -> None:
        self.cover.setPixmap(QPixmap())
        self.title.setText(_("Kein Eintrag ausgewaehlt"))
        self.subtitle.setText("")
        self.overview.setPlainText("")
        self.source_label.setText("")
        self.path_label.setText("")
        self._key = ""

    def show_item(self, item: Item | None) -> None:
        if item is None:
            self.clear()
            return
        self.title.setText(item.title or "?")

        bits: list[str] = []
        if item.authors:
            bits.append(", ".join(item.authors))
        if item.series:
            tag = item.series
            if item.series_index:
                tag += f" #{item.series_index}"
            bits.append(tag)
        if item.year:
            bits.append(str(item.year))
        self.subtitle.setText(" · ".join(bits))
        self.overview.setPlainText(item.description)

        if item.source:
            name = SOURCE_NAMES.get(item.source, item.source)
            url = item.source_url
            if url:
                self.source_label.setText(
                    _('Quelle: <a href="{url}">{name} ansehen ↗</a>').format(
                        url=url, name=name))
            else:
                self.source_label.setText(_("Quelle: {name}").format(name=name))
        else:
            self.source_label.setText("")

        self.path_label.setText(item.path)
        self.path_label.setToolTip(item.path)

        self._key = item.cover_url or item.path
        pm = self._loader.get(self._key)
        self._apply_cover(pm)

    def _on_cover(self, key: str, pixmap: QPixmap) -> None:
        if key == self._key:
            self._apply_cover(pixmap)

    def _apply_cover(self, pixmap: QPixmap | None) -> None:
        if pixmap and not pixmap.isNull():
            self.cover.setPixmap(
                pixmap.scaledToWidth(COVER_W, Qt.SmoothTransformation))
        else:
            self.cover.setPixmap(QPixmap())
