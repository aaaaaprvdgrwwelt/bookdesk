"""MOBI/AZW3 lesen - nur lesend, siehe `write_metadata` in base.py (dort
gibt es fuer diese Formate bewusst keine Implementierung). Ueber die reine-
Python-Bibliothek `mobi` (ein Wrapper um KindleUnpack): die entpackt eine
Datei entweder zu einem aequivalenten EPUB (KF8 - das sind praktisch alle
AZW3-Titel und neuere MOBI-Titel; dann wird einfach an `epub.py`
weitergereicht) oder, bei aelteren reinen MOBI7-Titeln ohne KF8-Anteil, zu
einer einzelnen HTML-Datei plus einer knappen `content.opf` mit den
Basis-Metadaten.

DRM-Erkennung laeuft direkt ueber das Encryption-Type-Feld im PalmDOC-
Header (siehe `is_drm_protected`), ohne vorher zu entpacken - das wuerde
bei einer verschluesselten Datei ohnehin scheitern."""
from __future__ import annotations

import shutil
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import mobi as _mobikit

from . import epub as _epub_format
from .base import BookMeta, Chapter

_NS_DC = "http://purl.org/dc/elements/1.1/"
_NS_OPF = "http://www.idpf.org/2007/opf"


def _record0_offset(header: bytes) -> int | None:
    """Byte-Offset des ersten Datensatzes (PalmDOC-/MOBI-Header) innerhalb
    der PalmDB-Datei - siehe PalmDB-Formatbeschreibung."""
    if len(header) < 78 + 4:
        return None
    (num_records,) = struct.unpack_from(">H", header, 76)
    if num_records < 1:
        return None
    (offset,) = struct.unpack_from(">I", header, 78)
    return offset


def is_drm_protected(path: Path) -> bool:
    """Encryption-Type-Feld im PalmDOC-Header (Byte 12-13 ab Record-0-
    Anfang): 0 = unverschluesselt, 1/2 = (alte/neue) Mobipocket-
    Verschluesselung."""
    try:
        with open(path, "rb") as f:
            offset = _record0_offset(f.read(86))
            if offset is None:
                return False
            f.seek(offset + 12)
            raw = f.read(2)
        if len(raw) < 2:
            return False
        (encryption_type,) = struct.unpack(">H", raw)
        return encryption_type != 0
    except OSError:
        return False


def _extract(path: Path) -> tuple[str | None, Path | None]:
    """Gibt (tempdir, entpackter_pfad) zurueck, oder (None, None) bei
    Verschluesselung oder einem Entpackfehler. Die Aufrufer sind fuers
    Aufraeumen von `tempdir` zustaendig (siehe `shutil.rmtree` unten in
    jeder oeffentlichen Funktion)."""
    if is_drm_protected(path):
        return None, None
    try:
        tempdir, extracted = _mobikit.extract(str(path))
    except Exception:  # noqa: BLE001 - kindleunpack wirft diverse eigene Fehlerklassen
        return None, None
    return tempdir, Path(extracted)


def _read_fallback_opf(content_opf: Path) -> BookMeta:
    """Nur fuer den MOBI7-Zweig (kein KF8-Anteil, also kein aequivalentes
    EPUB): liest dieselben Basisfelder wie epub.read_metadata aus der von
    kindleunpack danebengelegten `content.opf`."""
    if not content_opf.exists():
        return BookMeta()
    try:
        root = ET.fromstring(content_opf.read_bytes())
    except ET.ParseError:
        return BookMeta()
    metadata_el = root.find(f"{{{_NS_OPF}}}metadata")
    if metadata_el is None:
        return BookMeta()

    title_el = metadata_el.find(f"{{{_NS_DC}}}title")
    title = (title_el.text or "").strip() if title_el is not None else ""
    authors = [el.text.strip() for el in metadata_el.findall(f"{{{_NS_DC}}}creator")
              if el.text and el.text.strip()]
    lang_el = metadata_el.find(f"{{{_NS_DC}}}language")
    language = (lang_el.text or "").strip() if lang_el is not None else ""

    year = None
    for el in metadata_el.findall(f"{{{_NS_DC}}}date"):
        digits = "".join(c for c in (el.text or "")[:4] if c.isdigit())
        if len(digits) == 4:
            year = int(digits)
            break

    return BookMeta(title=title, authors=authors, language=language, year=year)


def read_metadata(path: Path) -> BookMeta:
    tempdir, extracted = _extract(path)
    if extracted is None:
        return BookMeta(title=path.stem)
    try:
        if extracted.suffix.lower() == ".epub":
            return _epub_format.read_metadata(extracted)
        meta = _read_fallback_opf(extracted.with_name("content.opf"))
        return meta if meta.title else BookMeta(title=path.stem)
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def cover_bytes(path: Path) -> bytes | None:
    tempdir, extracted = _extract(path)
    if extracted is None:
        return None
    try:
        if extracted.suffix.lower() == ".epub":
            return _epub_format.cover_bytes(extracted)
        # MOBI7-Zweig: kindleunpack legt ein evtl. vorhandenes Cover als
        # eigene Bilddatei neben book.html/content.opf ab - anders als bei
        # EPUB gibt es hier keine explizite "ist das wirklich das Cover"-
        # Kennzeichnung, das erste Bild im Ordner ist die beste Naeherung.
        for candidate in sorted(extracted.parent.glob("*")):
            if candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif"}:
                return candidate.read_bytes()
        return None
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def chapters(path: Path) -> list[Chapter]:
    """Bei KF8-Titeln (entpackt zu echtem EPUB) genauso kapitelweise wie
    natives EPUB. Der MOBI7-Zweig kennt keine Kapiteldateien - kindleunpack
    schreibt dort alles in eine einzige book.html, die deshalb als ein
    einziges "Kapitel" mit dem kompletten Text zurueckgegeben wird (im
    Reader also ein durchgehendes Buch ohne Kapitel-Navigation - eine
    dokumentierte Einschraenkung fuer diese aelteren Dateien)."""
    tempdir, extracted = _extract(path)
    if extracted is None:
        return []
    try:
        if extracted.suffix.lower() == ".epub":
            return _epub_format.chapters(extracted)
        return [Chapter(title=path.stem, html=extracted.read_bytes())]
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
