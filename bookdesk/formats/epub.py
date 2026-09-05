"""EPUB lesen und schreiben: Metadaten, Cover, Kapitel - ueber ebooklib zum
Lesen, direktes Patchen der OPF-Datei im Archiv zum Schreiben (siehe
`write_metadata`)."""
from __future__ import annotations

import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import ebooklib
from ebooklib import epub as _epub

from .base import BookMeta, Chapter

#: Datei, unter der Calibre/ebooklib eine automatisch erzeugte Cover-Seite
#: ablegen - kein echtes Kapitel, wird beim Lesen uebersprungen.
_COVER_PAGE_NAME = "cover.xhtml"

_NS_OPF = "http://www.idpf.org/2007/opf"
_NS_DC = "http://purl.org/dc/elements/1.1/"
_NS_CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"


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


def _opf_path(zf: zipfile.ZipFile) -> str:
    container = ET.fromstring(zf.read("META-INF/container.xml"))
    rootfile = container.find(f".//{{{_NS_CONTAINER}}}rootfile")
    if rootfile is None or not rootfile.get("full-path"):
        raise ValueError("container.xml ohne rootfile - kein gueltiges EPUB")
    return rootfile.get("full-path")


def _set_opf_meta(metadata_el: ET.Element, name: str, value: str) -> None:
    """Ein `<meta name="..." content="...">` setzen/entfernen - so legt
    Calibre die Serieninformation ab, die es sonst im EPUB-Standard nicht
    gibt."""
    existing = None
    for el in metadata_el.findall(f"{{{_NS_OPF}}}meta"):
        if el.get("name") == name:
            existing = el
            break
    if not value:
        if existing is not None:
            metadata_el.remove(existing)
        return
    if existing is None:
        existing = ET.SubElement(metadata_el, f"{{{_NS_OPF}}}meta")
        existing.set("name", name)
    existing.set("content", value)


def _patch_opf(data: bytes, meta: BookMeta) -> bytes:
    ET.register_namespace("", _NS_OPF)
    ET.register_namespace("dc", _NS_DC)
    root = ET.fromstring(data)
    metadata_el = root.find(f"{{{_NS_OPF}}}metadata")
    if metadata_el is None:
        raise ValueError("OPF ohne <metadata> - kein gueltiges EPUB")

    for tag in ("title", "creator", "description"):
        for el in metadata_el.findall(f"{{{_NS_DC}}}{tag}"):
            metadata_el.remove(el)

    title_el = ET.SubElement(metadata_el, f"{{{_NS_DC}}}title")
    title_el.text = meta.title

    for author in meta.authors:
        creator_el = ET.SubElement(metadata_el, f"{{{_NS_DC}}}creator")
        creator_el.text = author

    if meta.description:
        desc_el = ET.SubElement(metadata_el, f"{{{_NS_DC}}}description")
        desc_el.text = meta.description

    _set_opf_meta(metadata_el, "calibre:series", meta.series)
    _set_opf_meta(metadata_el, "calibre:series_index", meta.series_index)

    return ET.tostring(root, xml_declaration=True, encoding="utf-8")


def write_metadata(path: Path, meta: BookMeta) -> None:
    """Metadaten direkt in die vorhandene EPUB-Datei zurueckschreiben - alle
    anderen Dateien im Archiv bleiben byte-identisch, nur die OPF-Datei wird
    ersetzt. Schreibt erst in eine temporaere Datei und ersetzt das Original
    erst nach einem Gueltigkeits-Check, damit ein Fehler mittendrin nicht die
    vorhandene Datei beschaedigt."""
    tmp_path = path.with_name(path.name + ".bookdesk-tmp")
    with zipfile.ZipFile(path, "r") as zin:
        opf_name = _opf_path(zin)
        new_opf = _patch_opf(zin.read(opf_name), meta)
        try:
            with zipfile.ZipFile(tmp_path, "w") as zout:
                for info in zin.infolist():
                    data = new_opf if info.filename == opf_name else zin.read(info.filename)
                    compress_type = (
                        zipfile.ZIP_STORED if info.filename == "mimetype"
                        else zipfile.ZIP_DEFLATED)
                    new_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                    new_info.compress_type = compress_type
                    new_info.external_attr = info.external_attr
                    zout.writestr(new_info, data)

            with zipfile.ZipFile(tmp_path, "r") as check:
                if check.testzip() is not None:
                    raise ValueError("Neu geschriebenes EPUB ist beschaedigt")
            os.replace(tmp_path, path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
