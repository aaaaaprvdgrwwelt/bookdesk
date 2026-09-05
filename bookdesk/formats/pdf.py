"""PDF lesen: Metadaten, Cover (erste Seite), Seiten - ueber pymupdf.

PDFs haben in der Regel keine Serieninformation und keine Kapitel im
EPUB-Sinn - deshalb hier kein `chapters()`, der Reader liest PDF stattdessen
seitenweise (siehe `page_count`/`page_image` und `reader.py`).
"""
from __future__ import annotations

from pathlib import Path

import pymupdf

from .base import BookMeta

#: Rendergroesse fuer Cover-Thumbnails - kleiner als beim Lesen (page_image),
#: da nur fuers Raster gebraucht.
_COVER_ZOOM = 1.0


def _open(path: Path) -> pymupdf.Document | None:
    try:
        return pymupdf.open(str(path))
    except Exception:  # noqa: BLE001
        return None


def read_metadata(path: Path) -> BookMeta:
    doc = _open(path)
    if doc is None:
        return BookMeta()
    try:
        meta = doc.metadata or {}
        title = meta.get("title") or path.stem
        author = meta.get("author") or ""
        authors = [a.strip() for a in author.split(",") if a.strip()] if author else []
        year = None
        date = meta.get("creationDate") or ""
        # PDF-Datumsformat: "D:YYYYMMDD..."
        digits = date[2:6] if date.startswith("D:") else ""
        if digits.isdigit():
            year = int(digits)
        return BookMeta(title=title, authors=authors, year=year)
    finally:
        doc.close()


def cover_bytes(path: Path) -> bytes | None:
    doc = _open(path)
    if doc is None or doc.page_count == 0:
        return None
    try:
        page = doc.load_page(0)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(_COVER_ZOOM, _COVER_ZOOM))
        return pixmap.tobytes("png")
    finally:
        doc.close()


def page_count(path: Path) -> int:
    doc = _open(path)
    if doc is None:
        return 0
    try:
        return doc.page_count
    finally:
        doc.close()


def write_metadata(path: Path, meta: BookMeta) -> None:
    """Titel/Autor in die PDF-Dokumenteigenschaften zurueckschreiben. PDF hat
    kein Serien-Konzept, das bleibt unbeachtet - anders als bei EPUB wird
    hier ueber pymupdf inkrementell gespeichert (kein Neuschreiben des
    gesamten Archivs noetig)."""
    doc = _open(path)
    if doc is None:
        raise ValueError(f"Konnte {path} nicht oeffnen")
    try:
        doc.set_metadata({
            **(doc.metadata or {}),
            "title": meta.title,
            "author": ", ".join(meta.authors),
        })
        doc.saveIncr()
    finally:
        doc.close()


def page_image(path: Path, index: int, max_width: int = 1400) -> bytes | None:
    doc = _open(path)
    if doc is None or not (0 <= index < doc.page_count):
        if doc is not None:
            doc.close()
        return None
    try:
        page = doc.load_page(index)
        zoom = max_width / max(page.rect.width, 1)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        return pixmap.tobytes("png")
    finally:
        doc.close()
