"""Automatischer Metadaten-Abgleich: Kandidaten sammeln, bewerten, besten
Treffer uebernehmen. Struktur wie moviedesk/matcher.py, ohne Episode-Zweig."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import requests
from PySide6.QtCore import QObject, QThread, Signal

from deskkit.matching import title_similarity

from . import coverstore
from .i18n import _
from .library import LibraryIndex, STATUS_ERROR, STATUS_MATCHED, STATUS_UNSURE
from .providers.base import (
    BookInfo, Candidate, MetadataProvider, SearchQuery, author_overlap,
    search_title,
)

DEFAULT_THRESHOLD = 70


@dataclass
class MatchConfig:
    threshold: int = DEFAULT_THRESHOLD
    providers: list[MetadataProvider] = field(default_factory=list)
    cover_storage: str = coverstore.STORAGE_NONE
    cover_directory: str = ""


def score_candidate(query: SearchQuery, candidate: Candidate) -> int:
    """Titel zaehlt am meisten, Autor-Uebereinstimmung stuetzt - fehlt der
    Autor auf einer Seite, soll das den Titel-Treffer nicht zunichtemachen."""
    score = title_similarity(query.title, candidate.title) * 70
    score += author_overlap(query.authors, candidate.authors) * 30
    return round(min(score, 100))


def _describe_error(provider: MetadataProvider, exc: Exception) -> str:
    """Kurze, fuer den Nutzer verstaendliche Fehlermeldung statt einer
    rohen Exception - vor allem fuer ein erschoepftes Tageslimit bei
    Google Books (HTTP 429), das sonst nicht von einem echten "kein
    Treffer" zu unterscheiden waere."""
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        status = exc.response.status_code
        if status == 429:
            return _("{name}: Tageslimit erreicht").format(name=provider.label)
        return _("{name}: Fehler ({code})").format(name=provider.label, code=status)
    return _("{name}: Fehler").format(name=provider.label)


def collect_candidates(query: SearchQuery, config: MatchConfig,
                       limit: int = 10,
                       errors: list[str] | None = None) -> list[Candidate]:
    """`errors` wird (falls uebergeben) um eine kurze Meldung je Quelle
    ergaenzt, die einen Fehler statt "kein Treffer" geliefert hat - siehe
    identify()."""
    candidates: list[Candidate] = []
    for provider in config.providers:
        ok, _why = provider.available()
        if not ok:
            continue
        try:
            found = provider.search(query, limit)
        except Exception as exc:  # noqa: BLE001
            if errors is not None:
                errors.append(_describe_error(provider, exc))
            continue
        for candidate in found:
            candidate.score = score_candidate(query, candidate)
            candidates.append(candidate)
    candidates.sort(key=lambda c: -c.score)
    return candidates


def identify(query: SearchQuery,
            config: MatchConfig) -> tuple[BookInfo | None, int, str]:
    """(Info, Score, Fehlgrund). Info ist None, wenn keine Quelle etwas
    gefunden hat."""
    if not config.providers:
        return None, 0, _("Keine Quelle konfiguriert.")
    errors: list[str] = []
    candidates = collect_candidates(query, config, errors=errors)
    if not candidates:
        note = _("kein Treffer")
        if errors:
            note += " (" + "; ".join(errors) + ")"
        return None, 0, note
    best = candidates[0]
    provider = next((p for p in config.providers if p.name == best.source), None)
    info = provider.details(best) if provider else None
    return info, best.score, ""


class AutoMatchWorker(QObject):
    """Laeuft im eigenen Thread, meldet pro Datei ein Ergebnis."""

    progress = Signal(int, int, str)
    finished = Signal()

    def __init__(self, paths: list[Path], config: MatchConfig,
                library: LibraryIndex):
        super().__init__()
        self.paths = paths
        self.config = config
        self.library = library
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        total = len(self.paths)
        for i, path in enumerate(self.paths, 1):
            if self._stop:
                break
            self.progress.emit(i, total, path.name)
            item = self.library.get(path)
            if item is None:
                continue
            query = SearchQuery(title=search_title(item.title), authors=item.authors)
            try:
                info, score, note = identify(query, self.config)
            except Exception as exc:  # noqa: BLE001
                self.library.set_status(path, STATUS_ERROR, str(exc))
                continue
            if info is None:
                self.library.set_status(path, STATUS_UNSURE, note)
                continue
            status = STATUS_MATCHED if score >= self.config.threshold else STATUS_UNSURE
            self.library.set_match(
                path, info.title, info.authors, item.series, item.series_index,
                info.year, info.description, info.cover_url, info.source,
                info.external_id, score, status)
            if info.cover_url:
                saved = coverstore.save_cover(
                    item.id, info.title, path, info.cover_url,
                    self.config.cover_storage, self.config.cover_directory)
                if saved:
                    self.library.set_cover_path(path, str(saved))
        self.finished.emit()


def run_in_thread(paths: list[Path], config: MatchConfig, library: LibraryIndex):
    """Gibt (thread, worker) zurueck - der Aufrufer verbindet die Signale."""
    thread = QThread()
    worker = AutoMatchWorker(paths, config, library)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    return thread, worker
