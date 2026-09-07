"""Google Books als zweite Metadaten-Quelle - kostenlos, kein API-Key
noetig fuer den ueblichen persoenlichen Gebrauch. Deckt vor allem
Self-Publishing-/Kindle-Titel ab, die OpenLibrary oft gar nicht
katalogisiert hat (z. B. deutsche Uebersetzungen kleinerer US-Indie-
Reihen) - Google indiziert solche Titel ueber das Partnerprogramm, in dem
Amazon/Kindle-Verlage ihre Buecher selbst einreichen.

Ohne eigenen API-Key gilt ein grosszuegiges, aber nicht dokumentiertes
Tageslimit pro IP - bei sehr haeufiger Nutzung (z. B. vielen parallelen
Nutzern hinter derselben IP) kann das ausgeschoepft sein; ein einzelner
fehlgeschlagener Aufruf lässt den Abgleich dann einfach diese Quelle
auslassen (siehe matcher.collect_candidates: Fehler pro Quelle werden
abgefangen, nicht der ganze Abgleich abgebrochen)."""
from __future__ import annotations

import threading
import time

import requests

from deskkit.cache import ResponseCache

from .base import BookInfo, Candidate, MetadataProvider, SearchQuery

API_BASE = "https://www.googleapis.com/books/v1/volumes"
USER_AGENT = "BookDesk/1.0"
MIN_INTERVAL = 0.3


class GoogleBooksProvider(MetadataProvider):
    name = "googlebooks"
    label = "Google Books"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT
        self._last_call = 0.0
        self._lock = threading.Lock()
        self._cache = ResponseCache("bookdesk", "googlebooks.sqlite")

    def available(self) -> tuple[bool, str]:
        return True, ""

    def _throttled_get(self, url: str, params: dict, cache_key: str) -> dict:
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        with self._lock:
            wait = MIN_INTERVAL - (time.time() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            response = self._session.get(url, params=params, timeout=15)
            self._last_call = time.time()
        response.raise_for_status()
        data = response.json()
        self._cache.put(cache_key, data)
        return data

    def _query_string(self, query: SearchQuery) -> str:
        parts = [f"intitle:{query.title}"]
        if query.authors:
            parts.append(f"inauthor:{query.authors[0]}")
        return " ".join(parts)

    def search(self, query: SearchQuery, limit: int = 10) -> list[Candidate]:
        params = {"q": self._query_string(query), "maxResults": limit}
        cache_key = "search:" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        data = self._throttled_get(API_BASE, params, cache_key)
        results = []
        for item in data.get("items", [])[:limit]:
            vi = item.get("volumeInfo", {})
            year = None
            date = vi.get("publishedDate") or ""
            if len(date) >= 4 and date[:4].isdigit():
                year = int(date[:4])
            images = vi.get("imageLinks") or {}
            cover = images.get("thumbnail") or images.get("smallThumbnail")
            results.append(Candidate(
                source=self.name, external_id=item.get("id") or "",
                title=vi.get("title") or "",
                authors=vi.get("authors") or [],
                year=year,
                # Google liefert Cover-URLs ueber http:// - unnoetig, da der
                # Server https ebenso beherrscht, und Qt/requests laden
                # https ohne Mixed-Content-Fragen konsistenter.
                cover_url=cover.replace("http://", "https://", 1) if cover else None,
            ))
        return results

    def details(self, candidate: Candidate) -> BookInfo:
        description = ""
        if candidate.external_id:
            try:
                url = f"{API_BASE}/{candidate.external_id}"
                data = self._throttled_get(url, {}, f"id:{candidate.external_id}")
                description = data.get("volumeInfo", {}).get("description", "")
            except requests.RequestException:
                pass
        return BookInfo(
            title=candidate.title, authors=candidate.authors,
            year=candidate.year, description=description,
            cover_url=candidate.cover_url, source=self.name,
            external_id=candidate.external_id,
        )
