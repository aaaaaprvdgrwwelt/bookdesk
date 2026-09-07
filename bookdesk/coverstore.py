"""Cover dauerhaft auf die Platte legen - neben der Buchdatei oder in einem
eigenen Ordner, statt nur im fluechtigen Thumbnail-Cache (siehe thumbs.py,
der bei einem geleerten Cache das Cover erneut herunterladen wuerde). Rein
optional (siehe config.Settings.cover_storage) - schreibt nur Dateien,
wenn der Nutzer das ausdruecklich eingestellt hat."""
from __future__ import annotations

import re
from pathlib import Path

import requests

STORAGE_NONE = "none"
STORAGE_NEXT_TO_BOOK = "next_to_book"
STORAGE_DIRECTORY = "directory"

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _sanitize(name: str) -> str:
    name = _UNSAFE.sub("_", name).strip(" .")
    return name or "cover"


def target_path(item_id: int, item_title: str, book_path: Path,
                mode: str, directory: str) -> Path | None:
    """Wohin das Cover geschrieben wuerde - None, wenn Speichern
    deaktiviert ist oder (bei "eigener Ordner") kein Ordner eingestellt
    ist."""
    if mode == STORAGE_NEXT_TO_BOOK:
        return book_path.with_suffix(".jpg")
    if mode == STORAGE_DIRECTORY:
        if not directory:
            return None
        # Buch-ID vorangestellt, damit zwei Buecher mit gleichem Titel
        # (z. B. "Band 1" in verschiedenen Serien) sich nicht gegenseitig
        # das Cover ueberschreiben.
        return Path(directory) / f"{item_id}-{_sanitize(item_title)}.jpg"
    return None


def save_cover(item_id: int, item_title: str, book_path: Path,
               cover_url: str | None, mode: str, directory: str) -> Path | None:
    """Laedt `cover_url` herunter und speichert es an der konfigurierten
    Stelle. Gibt den geschriebenen Pfad zurueck, oder None, wenn Speichern
    deaktiviert ist, keine Cover-URL vorliegt oder der Download
    fehlschlaegt (dann bleibt es beim fluechtigen Cache - kein Fehler, der
    den Abgleich abbrechen sollte)."""
    if mode == STORAGE_NONE or not cover_url:
        return None
    target = target_path(item_id, item_title, book_path, mode, directory)
    if target is None:
        return None
    try:
        response = requests.get(cover_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException:
        return None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
    except OSError:
        return None
    return target
