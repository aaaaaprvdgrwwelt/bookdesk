"""Titel/Autor aus dem Dateinamen raten - Rueckfallebene, wenn die Datei
selbst keine brauchbaren Metadaten mitbringt (z. B. ein PDF ohne
Dokumenten-Titel, oder ein EPUB ohne DC-Autor)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_year_re = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")


def clean_words(text: str) -> str:
    text = text.replace(".", " ").replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def _strip_trailing_punct(text: str) -> str:
    return text.strip(" -._([")


@dataclass
class ParsedBook:
    title: str
    author: str = ""
    year: int | None = None


def parse_filename(path: Path) -> ParsedBook:
    """Haeufige Konventionen: "Autor - Titel", "Titel - Autor (Jahr)". Ohne
    erkennbaren Trenner wird der ganze (bereinigte) Dateiname als Titel
    genommen - keine Rateschlacht um jeden Sonderfall, der Rest landet als
    unsicherer Treffer im Match-Dialog statt eine falsche Automatik zu
    riskieren."""
    stem = clean_words(path.stem)
    year = None
    year_match = _year_re.search(stem)
    if year_match:
        year = int(year_match.group(1))
        stem = _strip_trailing_punct(
            stem[:year_match.start()] + stem[year_match.end():])

    parts = [p.strip() for p in stem.split(" - ") if p.strip()]
    if len(parts) >= 2:
        return ParsedBook(title=parts[1], author=parts[0], year=year)
    return ParsedBook(title=_strip_trailing_punct(stem), year=year)
