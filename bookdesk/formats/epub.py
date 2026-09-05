"""EPUB lesen: Metadaten, Cover, Kapitel - ueber ebooklib."""
from __future__ import annotations

from pathlib import Path

import ebooklib
from ebooklib import epub as _epub

from .base import BookMeta, Chapter

#: Datei, unter der Calibre/ebooklib eine automatisch erzeugte Cover-Seite
#: ablegen - kein echtes Kapitel, wird beim Lesen uebersprungen.
_COVER_PAGE_NAME = "cover.xhtml"


def _read(path: Path) -> _epub.EpubBook | None:
    try:
        return _epub.read_epub(str(path), options={"ignore_ncx": True})
    except Exception:  # noqa: BLE001
        return None


def _first(book: _epub.EpubBook, namespace: str, name: str) -> str:
    entries = book.get_metadata(namespace, name)
    return entries[0][0] if entries and entries[0][0] else ""


def read_metadata(path: Path) -> BookMeta:
    book = _read(path)
    if book is None:
        return BookMeta()

    title = _first(book, "DC", "title") or path.stem
    authors = [value for value, _attrs in book.get_metadata("DC", "creator")
              if value]
    language = _first(book, "DC", "language")
    description = _first(book, "DC", "description")

    year = None
    for value, _attrs in book.get_metadata("DC", "date"):
        digits = "".join(c for c in (value or "")[:4] if c.isdigit())
        if len(digits) == 4:
            year = int(digits)
            break

    series = ""
    series_index = ""
    for value, attrs in book.get_metadata("OPF", "meta"):
        name = attrs.get("name") or attrs.get("property") or ""
        if name == "calibre:series":
            series = value or attrs.get("content", "")
        elif name == "calibre:series_index":
            series_index = value or attrs.get("content", "")

    return BookMeta(title=title, authors=authors, series=series,
                    series_index=series_index, year=year, language=language,
                    description=description)


def cover_bytes(path: Path) -> bytes | None:
    book = _read(path)
    if book is None:
        return None
    for item in book.get_items_of_type(ebooklib.ITEM_COVER):
        return item.get_content()
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        return item.get_content()
    return None


def chapters(path: Path) -> list[Chapter]:
    book = _read(path)
    if book is None:
        return []
    result = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        if item.get_name().endswith(_COVER_PAGE_NAME):
            continue
        result.append(Chapter(title=item.get_name(), html=item.get_content()))
    return result
