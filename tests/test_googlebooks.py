"""Tests fuer die Google-Books-Anbindung (bookdesk/providers/googlebooks.py) -
Netzwerk wird gemockt (self._session.get gepatcht), analog zu den
gemockten Provider-Tests der Geschwister-Apps (siehe z. B.
moviedesk/audiodesk-Planung: `_get()` gemockt statt echter Netzwerkzugriff)."""
from __future__ import annotations

from pathlib import Path

import pytest

from bookdesk.providers.base import SearchQuery
from bookdesk.providers.googlebooks import GoogleBooksProvider


class FakeResponse:
    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._data


SEARCH_RESPONSE = {
    "items": [
        {
            "id": "abc123",
            "volumeInfo": {
                "title": "Last Licks",
                "authors": ["M. R. Forbes"],
                "publishedDate": "2023-05-01",
                "imageLinks": {"thumbnail": "http://books.google.com/cover.jpg"},
            },
        },
        {
            "id": "def456",
            "volumeInfo": {
                "title": "Something Else",
                "authors": ["Someone Else"],
            },
        },
    ]
}

DETAILS_RESPONSE = {
    "volumeInfo": {"description": "Ein Raumschiff-Abenteuer."},
}


@pytest.fixture
def provider(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    return GoogleBooksProvider()


def test_available_is_always_true(provider):
    ok, why = provider.available()
    assert ok is True


def test_search_parses_candidates(provider, monkeypatch):
    monkeypatch.setattr(provider._session, "get",
                        lambda *a, **k: FakeResponse(SEARCH_RESPONSE))
    results = provider.search(SearchQuery(title="Last Licks", authors=["M. R. Forbes"]))
    assert len(results) == 2
    first = results[0]
    assert first.source == "googlebooks"
    assert first.external_id == "abc123"
    assert first.title == "Last Licks"
    assert first.authors == ["M. R. Forbes"]
    assert first.year == 2023


def test_search_upgrades_cover_url_to_https(provider, monkeypatch):
    monkeypatch.setattr(provider._session, "get",
                        lambda *a, **k: FakeResponse(SEARCH_RESPONSE))
    results = provider.search(SearchQuery(title="Last Licks"))
    assert results[0].cover_url == "https://books.google.com/cover.jpg"


def test_search_without_cover_yields_none(provider, monkeypatch):
    monkeypatch.setattr(provider._session, "get",
                        lambda *a, **k: FakeResponse(SEARCH_RESPONSE))
    results = provider.search(SearchQuery(title="x"))
    assert results[1].cover_url is None


def test_search_caches_and_avoids_second_http_call(provider, monkeypatch):
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        return FakeResponse(SEARCH_RESPONSE)

    monkeypatch.setattr(provider._session, "get", fake_get)
    provider.search(SearchQuery(title="Last Licks"))
    provider.search(SearchQuery(title="Last Licks"))
    assert len(calls) == 1


def test_details_fetches_description(provider, monkeypatch):
    monkeypatch.setattr(provider._session, "get",
                        lambda *a, **k: FakeResponse(DETAILS_RESPONSE))
    from bookdesk.providers.base import Candidate
    candidate = Candidate(source="googlebooks", external_id="abc123",
                          title="Last Licks", authors=["M. R. Forbes"], year=2023)
    info = provider.details(candidate)
    assert info.description == "Ein Raumschiff-Abenteuer."
    assert info.source == "googlebooks"
    assert info.external_id == "abc123"


def test_source_url_points_to_google_books(tmp_path):
    from bookdesk.library import LibraryIndex

    lib = LibraryIndex(tmp_path / "library.sqlite")
    path = Path("/books/test.epub")
    lib.mark_scanned(path, tmp_path, title="Last Licks", authors=["M. R. Forbes"])
    lib.set_match(path, "Last Licks", ["M. R. Forbes"], "", "", 2023, "", None,
                 "googlebooks", "abc123", 90, "matched")
    item = lib.get(path)
    assert item.source_url == "https://books.google.com/books?id=abc123"
    lib.close()
