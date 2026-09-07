"""Tests fuer bookdesk/coverstore.py - Cover dauerhaft speichern, neben
der Buchdatei oder in einem eigenen Ordner."""
from __future__ import annotations

from pathlib import Path

from bookdesk import coverstore


class FakeResponse:
    def __init__(self, content: bytes = b"\xff\xd8\xfake-jpeg-data"):
        self.content = content

    def raise_for_status(self) -> None:
        pass


def test_target_path_none_mode_is_none():
    assert coverstore.target_path(1, "Titel", Path("/books/b.epub"),
                                  coverstore.STORAGE_NONE, "") is None


def test_target_path_next_to_book_replaces_suffix():
    target = coverstore.target_path(
        1, "Titel", Path("/books/Band 1.epub"), coverstore.STORAGE_NEXT_TO_BOOK, "")
    assert target == Path("/books/Band 1.jpg")


def test_target_path_directory_uses_id_and_sanitized_title(tmp_path):
    target = coverstore.target_path(
        42, "Die letzte Chance", Path("/books/x.epub"),
        coverstore.STORAGE_DIRECTORY, str(tmp_path))
    assert target == tmp_path / "42-Die letzte Chance.jpg"


def test_target_path_directory_sanitizes_unsafe_characters(tmp_path):
    target = coverstore.target_path(
        1, 'Bad:/\\*?"<>|Title', Path("x.epub"),
        coverstore.STORAGE_DIRECTORY, str(tmp_path))
    assert target is not None
    assert "/" not in target.name.replace(str(tmp_path), "")
    for char in ':\\*?"<>|':
        assert char not in target.name


def test_target_path_directory_without_directory_is_none():
    assert coverstore.target_path(
        1, "Titel", Path("x.epub"), coverstore.STORAGE_DIRECTORY, "") is None


def test_save_cover_none_mode_downloads_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(coverstore.requests, "get",
                        lambda *a, **k: calls.append(1) or FakeResponse())
    result = coverstore.save_cover(
        1, "Titel", Path("/books/b.epub"), "https://example.invalid/c.jpg",
        coverstore.STORAGE_NONE, "")
    assert result is None
    assert calls == []


def test_save_cover_without_url_is_none():
    result = coverstore.save_cover(
        1, "Titel", Path("/books/b.epub"), None,
        coverstore.STORAGE_NEXT_TO_BOOK, "")
    assert result is None


def test_save_cover_next_to_book_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(coverstore.requests, "get",
                        lambda *a, **k: FakeResponse(b"cover-bytes"))
    book = tmp_path / "Band 1.epub"
    book.write_bytes(b"")
    result = coverstore.save_cover(
        1, "Titel", book, "https://example.invalid/c.jpg",
        coverstore.STORAGE_NEXT_TO_BOOK, "")
    assert result == tmp_path / "Band 1.jpg"
    assert result.read_bytes() == b"cover-bytes"


def test_save_cover_directory_creates_missing_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(coverstore.requests, "get",
                        lambda *a, **k: FakeResponse(b"cover-bytes"))
    covers_dir = tmp_path / "covers" / "nested"
    result = coverstore.save_cover(
        7, "Die letzte Chance", tmp_path / "b.epub",
        "https://example.invalid/c.jpg", coverstore.STORAGE_DIRECTORY,
        str(covers_dir))
    assert result == covers_dir / "7-Die letzte Chance.jpg"
    assert result.exists()


def test_save_cover_returns_none_on_download_failure(tmp_path, monkeypatch):
    import requests

    def raise_error(*a, **k):
        raise requests.RequestException("boom")

    monkeypatch.setattr(coverstore.requests, "get", raise_error)
    result = coverstore.save_cover(
        1, "Titel", tmp_path / "b.epub", "https://example.invalid/c.jpg",
        coverstore.STORAGE_NEXT_TO_BOOK, "")
    assert result is None


def test_save_cover_directory_mode_without_directory_setting_is_none(monkeypatch):
    calls = []
    monkeypatch.setattr(coverstore.requests, "get",
                        lambda *a, **k: calls.append(1) or FakeResponse())
    result = coverstore.save_cover(
        1, "Titel", Path("/books/b.epub"), "https://example.invalid/c.jpg",
        coverstore.STORAGE_DIRECTORY, "")
    assert result is None
    assert calls == [], "sollte gar nicht erst herunterladen, wenn kein Ordner eingestellt ist"
