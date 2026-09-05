"""OpenLibrary als Metadaten-Quelle - kostenlos, kein API-Key noetig."""
from __future__ import annotations

import threading
import time

import requests

from deskkit.cache import ResponseCache

from .base import BookInfo, Candidate, MetadataProvider, SearchQuery

API_BASE = "https://openlibrary.org"
COVER_BASE = "https://covers.openlibrary.org/b/id"
USER_AGENT = "BookDesk/1.0"
MIN_INTERVAL = 0.2


class OpenLibraryProvider(MetadataProvider):
    name = "openlibrary"
    label = "OpenLibrary"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT
        self._last_call = 0.0
        self._lock = threading.Lock()
        self._cache = ResponseCache("bookdesk", "openlibrary.sqlite")

    def available(self) -> tuple[bool, str]:
        return True, ""

    def _get(self, path: str, params: dict) -> dict:
        key = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        with self._lock:
            wait = MIN_INTERVAL - (time.time() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            response = self._session.get(API_BASE + path, params=params, timeout=15)
            self._last_call = time.time()
        response.raise_for_status()
        data = response.json()
        self._cache.put(key, data)
        return data

    def search(self, query: SearchQuery, limit: int = 10) -> list[Candidate]:
        data = self._get("/search.json", {"q": query.title, "limit": limit})
        results = []
        for doc in data.get("docs", [])[:limit]:
            cover_id = doc.get("cover_i")
            results.append(Candidate(
                source=self.name, external_id=doc.get("key") or "",
                title=doc.get("title") or "",
                authors=doc.get("author_name") or [],
                year=doc.get("first_publish_year"),
                cover_url=f"{COVER_BASE}/{cover_id}-L.jpg" if cover_id else None,
            ))
        return results

    def details(self, candidate: Candidate) -> BookInfo:
        description = ""
        if candidate.external_id:
            try:
                data = self._get(candidate.external_id + ".json", {})
            except requests.RequestException:
                data = {}
            desc = data.get("description")
            if isinstance(desc, dict):
                description = desc.get("value", "")
            elif isinstance(desc, str):
                description = desc
        return BookInfo(
            title=candidate.title, authors=candidate.authors,
            year=candidate.year, description=description,
            cover_url=candidate.cover_url, source=self.name,
            external_id=candidate.external_id,
        )
