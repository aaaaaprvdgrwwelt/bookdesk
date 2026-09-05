"""Gemeinsamer Nenner fuer EPUB und PDF - Metadaten, Cover, Kapitel je nach
Dateiendung an das passende Modul weitergereicht. Aehnlich wie comicdesks
`archive.py` mehrere Comic-Archivformate hinter einer Schnittstelle
versteckt."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

EPUB_EXTENSIONS = {".epub"}
PDF_EXTENSIONS = {".pdf"}
BOOK_EXTENSIONS = EPUB_EXTENSIONS | PDF_EXTENSIONS


@dataclass
class BookMeta:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    series: str = ""
    series_index: str = ""
    year: int | None = None
    language: str = ""
    description: str = ""


@dataclass
class Chapter:
    title: str
    html: bytes


def read_metadata(path: Path) -> BookMeta:
    suffix = path.suffix.lower()
    if suffix in EPUB_EXTENSIONS:
        from . import epub
        return epub.read_metadata(path)
    if suffix in PDF_EXTENSIONS:
        from . import pdf
        return pdf.read_metadata(path)
    return BookMeta()


def cover_bytes(path: Path) -> bytes | None:
    suffix = path.suffix.lower()
    if suffix in EPUB_EXTENSIONS:
        from . import epub
        return epub.cover_bytes(path)
    if suffix in PDF_EXTENSIONS:
        from . import pdf
        return pdf.cover_bytes(path)
    return None


def chapters(path: Path) -> list[Chapter]:
    """Nur fuer EPUB belegt - PDF wird seitenweise gelesen (siehe reader.py),
    das Kapitel-Konzept passt dort nicht."""
    if path.suffix.lower() in EPUB_EXTENSIONS:
        from . import epub
        return epub.chapters(path)
    return []


def page_count(path: Path) -> int:
    """Nur fuer PDF belegt - Anzahl Seiten fuer den seitenweisen Reader."""
    if path.suffix.lower() in PDF_EXTENSIONS:
        from . import pdf
        return pdf.page_count(path)
    return 0


def page_image(path: Path, index: int, max_width: int = 1400) -> bytes | None:
    """Nur fuer PDF belegt - eine Seite als PNG gerendert."""
    if path.suffix.lower() in PDF_EXTENSIONS:
        from . import pdf
        return pdf.page_image(path, index, max_width)
    return None
