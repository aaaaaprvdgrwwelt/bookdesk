"""Gemeinsame Schnittstelle fuer Metadaten-Quellen (Buecher)."""
from __future__ import annotations

from dataclasses import dataclass, field

from deskkit.matching import normalize_title, title_similarity

__all__ = [
    "normalize_title", "title_similarity", "normalize_author",
    "author_overlap", "ROLE_PRIMARY", "ROLE_SUPPLEMENT", "SearchQuery",
    "Candidate", "BookInfo", "MetadataProvider",
]

#: Quellen, die ein Buch selbst bestimmen koennen.
ROLE_PRIMARY = "primary"
#: Quellen, die nur ergaenzen. Gewinnen nie allein.
ROLE_SUPPLEMENT = "supplement"


def normalize_author(name: str) -> str:
    return normalize_title(name)


def author_overlap(a: list[str], b: list[str]) -> float:
    """Anteil der Autoren aus `a`, die (normalisiert) auch in `b` vorkommen -
    0 wenn eine Seite leer ist, damit fehlende Autorenangabe die
    Titel-Aehnlichkeit allein nicht zunichtemacht."""
    if not a or not b:
        return 0.0
    norm_b = {normalize_author(x) for x in b}
    hits = sum(1 for x in a if normalize_author(x) in norm_b)
    return hits / len(a)


@dataclass
class SearchQuery:
    """Was wir aus den vorhandenen Metadaten bzw. dem Dateinamen ueber das
    Buch wissen."""

    title: str
    authors: list[str] = field(default_factory=list)


@dataclass
class Candidate:
    """Ein Treffer einer Quelle, noch ohne volle Details."""

    source: str
    external_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    cover_url: str | None = None
    score: int = 0
    reasons: list[str] = field(default_factory=list)


@dataclass
class BookInfo:
    """Volle Metadaten eines gewaehlten Treffers."""

    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    description: str = ""
    cover_url: str | None = None
    source: str = ""
    external_id: str = ""


class MetadataProvider:
    """Basisklasse. `search` liefert Kandidaten, `details` vertieft."""

    name = "base"
    label = "Basis"
    role = ROLE_PRIMARY

    def available(self) -> tuple[bool, str]:
        """(nutzbar, Begruendung falls nicht)."""
        return False, "Nicht konfiguriert"

    def search(self, query: SearchQuery, limit: int = 10) -> list[Candidate]:
        raise NotImplementedError

    def details(self, candidate: Candidate) -> BookInfo:
        """Volle Metadaten fuer den Gewinner - erst hier noetig."""
        return BookInfo(
            title=candidate.title, authors=candidate.authors,
            year=candidate.year, cover_url=candidate.cover_url,
            source=candidate.source, external_id=candidate.external_id,
        )
