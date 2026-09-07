"""Gemeinsamer Nenner fuer EPUB und PDF - Metadaten, Cover, Kapitel je nach
Dateiendung an das passende Modul weitergereicht. Aehnlich wie comicdesks
`archive.py` mehrere Comic-Archivformate hinter einer Schnittstelle
versteckt."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

EPUB_EXTENSIONS = {".epub"}
PDF_EXTENSIONS = {".pdf"}
#: .azw ist derselbe PalmDB/MOBI-Container wie .mobi, .azw3 ist die
#: neuere KF8-Variante - alle drei landen beim Entpacken ueber `mobi.py`.
MOBI_EXTENSIONS = {".mobi", ".azw", ".azw3"}
BOOK_EXTENSIONS = EPUB_EXTENSIONS | PDF_EXTENSIONS | MOBI_EXTENSIONS
#: Zurueckschreiben ist nur fuer EPUB und PDF moeglich - MOBI/AZW3 sind ein
#: verschachteltes Binaerformat, das sich nicht sicher inkrementell patchen
#: laesst (siehe formats/mobi.py: nur lesend, ueber Entpacken).
WRITABLE_EXTENSIONS = EPUB_EXTENSIONS | PDF_EXTENSIONS


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
    if suffix in MOBI_EXTENSIONS:
        from . import mobi
        return mobi.read_metadata(path)
    return BookMeta()


def cover_bytes(path: Path) -> bytes | None:
    suffix = path.suffix.lower()
    if suffix in EPUB_EXTENSIONS:
        from . import epub
        return epub.cover_bytes(path)
    if suffix in PDF_EXTENSIONS:
        from . import pdf
        return pdf.cover_bytes(path)
    if suffix in MOBI_EXTENSIONS:
        from . import mobi
        return mobi.cover_bytes(path)
    return None


def chapters(path: Path) -> list[Chapter]:
    """Fuer EPUB und MOBI/AZW3 belegt - PDF wird seitenweise gelesen (siehe
    reader.py), das Kapitel-Konzept passt dort nicht."""
    suffix = path.suffix.lower()
    if suffix in EPUB_EXTENSIONS:
        from . import epub
        return epub.chapters(path)
    if suffix in MOBI_EXTENSIONS:
        from . import mobi
        return mobi.chapters(path)
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


def is_drm_protected(path: Path) -> bool:
    """Fuer EPUB und MOBI/AZW3 belegt - PDF-Passwortschutz ist ein eigenes,
    selteneres Problem und wird hier (noch) nicht erkannt."""
    suffix = path.suffix.lower()
    if suffix in EPUB_EXTENSIONS:
        from . import epub
        return epub.is_drm_protected(path)
    if suffix in MOBI_EXTENSIONS:
        from . import mobi
        return mobi.is_drm_protected(path)
    return False


def find_pages(path: Path, query: str) -> list[int]:
    """Nur fuer PDF belegt - Seiten (0-basiert), auf denen `query` vorkommt."""
    if path.suffix.lower() in PDF_EXTENSIONS:
        from . import pdf
        return pdf.find_pages(path, query)
    return []


def can_write(path: Path) -> bool:
    return path.suffix.lower() in WRITABLE_EXTENSIONS


def write_metadata(path: Path, meta: BookMeta) -> None:
    """Metadaten direkt in die Datei zurueckschreiben - EPUB: OPF-Datei im
    Archiv ersetzt; PDF: Dokumenteigenschaften (kein Serien-Konzept dort).
    Nur auf ausdruecklichen Wunsch aufrufen (siehe mainwindow.py), nie
    automatisch beim Scannen/Zuordnen."""
    suffix = path.suffix.lower()
    if suffix in EPUB_EXTENSIONS:
        from . import epub
        epub.write_metadata(path, meta)
        return
    if suffix in PDF_EXTENSIONS:
        from . import pdf
        pdf.write_metadata(path, meta)
        return
    raise ValueError(f"Nicht unterstuetztes Format: {suffix}")
