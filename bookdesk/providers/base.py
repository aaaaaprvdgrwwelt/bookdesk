"""Gemeinsame Schnittstelle fuer Metadaten-Quellen (Buecher)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from deskkit.matching import normalize_title, title_similarity

__all__ = [
    "normalize_title", "title_similarity", "normalize_author",
    "author_overlap", "search_title", "ROLE_PRIMARY", "ROLE_SUPPLEMENT",
    "SearchQuery", "Candidate", "BookInfo", "MetadataProvider",
]

#: Quellen, die ein Buch selbst bestimmen koennen.
ROLE_PRIMARY = "primary"
#: Quellen, die nur ergaenzen. Gewinnen nie allein.
ROLE_SUPPLEMENT = "supplement"


def normalize_author(name: str) -> str:
    return normalize_title(name)


#: Klammerzusatz am Titelende, der eine Ausgabenvariante statt eines Teils
#: des eigentlichen Titels benennt - haeufig bei Amazon-/Kindle-Ebooks
#: ("German Edition", "Kindle Edition", "dunkle Edition", "Ungekuerzt").
#: Ohne diesen Zusatz sitzt der eigentliche Buchtitel meist trotzdem in
#: der verbleibenden Zeichenkette.
_EDITION_SUFFIX = re.compile(
    r"\s*\([^()]*\b(?:edition|ausgabe|ungek(?:u|ü|ue)rzt|gek(?:u|ü|ue)rzt|"
    r"unabridged|abridged|h(?:o|ö|oe)rbuch|audiobook)\b[^()]*\)\s*$",
    re.IGNORECASE)

#: Fuehrende Band-/Kapitelnummer wie "006 - " oder "12 - ", haeufig direkt
#: im eingebetteten Titel enthalten - z. B. wenn die Datei ueber ihren
#: Dateinamen "006 - Tag der Rache.epub" getaggt wurde. Ohne diesen Zusatz
#: sitzt der eigentliche Buchtitel meist trotzdem in der verbleibenden
#: Zeichenkette (beobachtet bei einem echten Fall: "006 - Tag der Rache"
#: fand nichts, "Tag der Rache" allein einen brauchbaren Treffer). Nur bis
#: zu vier Ziffern gefolgt von einem Bindestrich, damit echte Titel wie
#: "1984" nicht angetastet werden.
_VOLUME_PREFIX = re.compile(r"^\s*\d{1,4}\s*-\s+")


def search_title(title: str) -> str:
    """Titel fuer die Anfrage an eine Online-Quelle bereinigt - ein
    Klammerzusatz wie "(German Edition)" oder eine fuehrende Bandnummer
    wie "006 - " liefert sonst bei praktisch jeder Quelle null Treffer,
    selbst bei bekannten Buechern (siehe _EDITION_SUFFIX/_VOLUME_PREFIX
    fuer je einen real aufgetretenen Fall). Wirkt nur auf die
    Suchanfrage - der in der Bibliothek gespeicherte Titel bleibt
    unveraendert."""
    cleaned = title
    while True:
        stripped = _EDITION_SUFFIX.sub("", cleaned).strip()
        stripped = _VOLUME_PREFIX.sub("", stripped).strip()
        if stripped == cleaned:
            break
        cleaned = stripped
    return cleaned or title


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
