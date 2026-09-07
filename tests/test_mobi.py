"""Tests fuer MOBI/AZW3 (bookdesk/formats/mobi.py).

Es gibt keine Beispieldatei zur Hand und Calibre/kindlegen sind hier nicht
verfuegbar - deshalb wird ein minimaler, aber echter MOBI6-Container
(PalmDOC + MOBI-Header, unkomprimiert, ohne KF8-Anteil) direkt in Python
zusammengesetzt. Das deckt den haeufigen "MOBI7-Fallback"-Zweig ab (siehe
mobi.py); der KF8/AZW3-Zweig, der zu einem echten EPUB entpackt wird, wird
separat mit einer gemockten `mobi.extract()` gegen ein echtes, per
ebooklib erzeugtes EPUB getestet - so ist auch dieser Zweig real verifiziert,
ohne einen kompletten binaeren KF8-Container von Hand bauen zu muessen."""
from __future__ import annotations

import shutil
import struct
import tempfile
from pathlib import Path

import pytest
from ebooklib import epub as _epub

from bookdesk.formats import base as formats
from bookdesk.formats import mobi as mobi_format

U32_NONE = 0xFFFFFFFF


def build_mobi(title: str, text: str, encrypted: bool = False) -> bytes:
    """Siehe Docstring oben - Feldoffsets richten sich nach dem, was
    mobi/mobi_header.py tatsaechlich ausliest (alle Offsets absolut ab
    Record-0-Anfang, d.h. inklusive des 16 Byte langen PalmDOC-Praefixes)."""
    text_bytes = text.encode("utf-8")
    full_name = title.encode("utf-8")
    mobi_header_len = 232
    full_name_offset = 16 + mobi_header_len

    mh = bytearray(mobi_header_len)

    def put_u32(rel_offset: int, value: int) -> None:
        struct.pack_into(">I", mh, rel_offset, value)

    mh[0:4] = b"MOBI"
    put_u32(0x04, mobi_header_len)
    put_u32(0x08, 2)          # mobiType: Mobipocket Book
    put_u32(0x0C, 65001)      # textEncoding: UTF-8
    put_u32(0x10, 0)          # uniqueID
    put_u32(0x14, 6)          # fileVersion (MOBI6, kein KF8)
    for off in (0x18, 0x1C, 0x20, 0x24, 0x28, 0x2C, 0x30, 0x34, 0x38, 0x3C):
        put_u32(off, U32_NONE)   # orthographicIndex .. extraIndex5: keine
    put_u32(0x40, U32_NONE)   # firstnontext (abs 0x50): keine
    put_u32(0x44, full_name_offset)
    put_u32(0x48, len(full_name))
    put_u32(0x4C, 0)          # locale
    put_u32(0x50, 0)          # Sprachcode-Fallback (abs 0x60)
    put_u32(0x54, 0)          # Sprachcode-Fallback (abs 0x64)
    put_u32(0x58, 6)          # mobi_version, fuer K8-Erkennung (abs 0x68)
    put_u32(0x5C, U32_NONE)   # firstresource (abs 0x6C): keine
    put_u32(0x60, 0)          # huffmanRecordOffset (nur bei Huffman-Kompression)
    put_u32(0x64, 0)          # huffmanRecordCount
    put_u32(0x68, 0)          # huffmanTableOffset
    put_u32(0x6C, 0)          # huffmanTableLength
    put_u32(0x70, 0)          # EXTHFlags (abs 0x80): kein EXTH-Record
    put_u32(0xE4, U32_NONE)   # NCX-Index (abs 0xF4): keine - letzte 4 Byte

    encryption_type = 2 if encrypted else 0
    record0 = struct.pack(">HHIHHHH", 1, 0, len(text_bytes), 1, 4096,
                          encryption_type, 0)
    record0 += bytes(mh)
    record0 += full_name
    record0 += b"\x00" * ((-len(record0)) % 4)

    records = [record0, text_bytes]
    header_len = 78
    record_info_len = len(records) * 8
    offset = header_len + record_info_len
    record_offsets = []
    for rec in records:
        record_offsets.append(offset)
        offset += len(rec)

    name = title.encode("utf-8")[:31].ljust(32, b"\x00")
    header = name
    header += struct.pack(">H", 0)             # attributes
    header += struct.pack(">H", 0)             # version
    header += struct.pack(">IIII", 0, 0, 0, 0)  # creation/mod/backup, modNumber
    header += struct.pack(">II", 0, 0)          # appInfoID, sortInfoID
    header += b"BOOK"
    header += b"MOBI"
    header += struct.pack(">II", 0, 0)          # uniqueIDseed, nextRecordListID
    header += struct.pack(">H", len(records))
    assert len(header) == header_len

    record_info = b""
    for i, off in enumerate(record_offsets):
        record_info += struct.pack(">I", off) + b"\x00" + struct.pack(">I", i)[1:]

    return header + record_info + b"".join(records)


def make_mobi_file(tmp_path: Path, name: str = "book.mobi", **kwargs) -> Path:
    path = tmp_path / name
    path.write_bytes(build_mobi("Testbuch", "<html><body><h1>Kapitel 1</h1>"
                                "<p>Hallo Welt.</p></body></html>", **kwargs))
    return path


def make_epub_file(tmp_path: Path) -> Path:
    book = _epub.EpubBook()
    book.set_identifier("id1")
    book.set_title("KF8 Test")
    book.set_language("en")
    book.add_author("Autor X")
    chap = _epub.EpubHtml(title="Kapitel 1", file_name="c1.xhtml", lang="en")
    chap.content = "<html><body><p>Hallo</p></body></html>"
    book.add_item(chap)
    book.spine = ["nav", chap]
    book.add_item(_epub.EpubNcx())
    book.add_item(_epub.EpubNav())
    path = tmp_path / "book.epub"
    _epub.write_epub(str(path), book)
    return path


def test_is_drm_protected_false_for_plain_mobi(tmp_path):
    path = make_mobi_file(tmp_path)
    assert formats.is_drm_protected(path) is False


def test_is_drm_protected_true_for_encrypted_mobi(tmp_path):
    path = make_mobi_file(tmp_path, encrypted=True)
    assert formats.is_drm_protected(path) is True


def test_read_metadata_mobi7_fallback(tmp_path):
    path = make_mobi_file(tmp_path)
    meta = formats.read_metadata(path)
    assert meta.title == "Testbuch"


def test_chapters_mobi7_returns_single_chapter_with_full_text(tmp_path):
    path = make_mobi_file(tmp_path)
    chaps = formats.chapters(path)
    assert len(chaps) == 1
    assert b"Hallo Welt" in chaps[0].html


def test_cover_bytes_none_when_no_image_present(tmp_path):
    path = make_mobi_file(tmp_path)
    assert formats.cover_bytes(path) is None


def test_encrypted_mobi_yields_empty_metadata_and_no_chapters(tmp_path):
    path = make_mobi_file(tmp_path, encrypted=True)
    meta = formats.read_metadata(path)
    assert meta.title == path.stem
    assert formats.chapters(path) == []
    assert formats.cover_bytes(path) is None


@pytest.mark.parametrize("suffix", [".mobi", ".azw", ".azw3"])
def test_base_dispatches_all_mobi_extensions(tmp_path, suffix):
    path = make_mobi_file(tmp_path, name=f"book{suffix}")
    assert formats.read_metadata(path).title == "Testbuch"


def test_can_write_false_for_mobi(tmp_path):
    path = make_mobi_file(tmp_path)
    assert formats.can_write(path) is False


def test_write_metadata_raises_for_mobi(tmp_path):
    path = make_mobi_file(tmp_path)
    meta = formats.read_metadata(path)
    with pytest.raises(ValueError):
        formats.write_metadata(path, meta)


def test_kf8_extraction_delegates_to_epub(tmp_path, monkeypatch):
    """KF8/AZW3-Titel entpackt `mobi.extract()` zu einem echten,
    aequivalenten EPUB - dieser Zweig wird hier gegen ein per ebooklib
    erzeugtes EPUB verifiziert, inklusive Aufraeumen des Temp-Verzeichnisses."""
    created_tempdirs = []

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    epub_src = make_epub_file(src_dir)

    def fake_extract(_path):
        tempdir = tempfile.mkdtemp(dir=tmp_path)
        created_tempdirs.append(tempdir)
        target_dir = Path(tempdir) / "mobi8"
        target_dir.mkdir()
        epub_dst = target_dir / "book.epub"
        shutil.copy(epub_src, epub_dst)
        return tempdir, str(epub_dst)

    monkeypatch.setattr(mobi_format._mobikit, "extract", fake_extract)

    fake_azw3 = tmp_path / "book.azw3"
    fake_azw3.write_bytes(b"placeholder - extract() is mocked")

    meta = formats.read_metadata(fake_azw3)
    assert meta.title == "KF8 Test"
    assert meta.authors == ["Autor X"]

    chaps = formats.chapters(fake_azw3)
    assert any(b"Hallo" in c.html for c in chaps)

    assert not Path(created_tempdirs[0]).exists(), "Temp-Verzeichnis wurde nicht aufgeraeumt"
