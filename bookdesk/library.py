"""Bibliotheksindex: SQLite mit einer Zeile je Ebook-Datei.

Wie bei moviedesk (anders als comicdesk mit ComicInfo.xml *in* der Datei)
gibt es fuer Ebooks kein verlaesslich einheitliches eingebettetes
Zuordnungsformat quer durch EPUB/PDF - diese Datenbank ist deshalb die
Quelle der Wahrheit fuer Zuordnungen.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from deskkit.backup import backup_database

STATUS_MATCHED = "matched"
STATUS_UNSURE = "unsure"
STATUS_UNMATCHED = "unmatched"
STATUS_ERROR = "error"

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    root TEXT NOT NULL,
    title TEXT DEFAULT '',
    authors TEXT DEFAULT '[]',
    series TEXT DEFAULT '',
    series_index TEXT DEFAULT '',
    year INTEGER,
    language TEXT DEFAULT '',
    description TEXT DEFAULT '',
    cover_url TEXT,
    cover_path TEXT,
    source TEXT DEFAULT '',
    external_id TEXT DEFAULT '',
    score INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'unmatched',
    note TEXT DEFAULT '',
    last_position INTEGER DEFAULT 0,
    scanned_at REAL,
    matched_at REAL
)
"""


def data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    path = Path(base) / "bookdesk"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Item:
    id: int
    path: str
    root: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    series: str = ""
    series_index: str = ""
    year: int | None = None
    language: str = ""
    description: str = ""
    cover_url: str | None = None
    cover_path: str | None = None
    source: str = ""
    external_id: str = ""
    score: int = 0
    status: str = STATUS_UNMATCHED
    note: str = ""
    last_position: int = 0

    @property
    def display_title(self) -> str:
        year = f" ({self.year})" if self.year else ""
        return f"{self.title}{year}"

    @property
    def author_line(self) -> str:
        return ", ".join(self.authors)

    @property
    def source_url(self) -> str | None:
        if self.source == "openlibrary" and self.external_id:
            return f"https://openlibrary.org{self.external_id}"
        return None


_COLUMNS = [
    "id", "path", "root", "title", "authors", "series", "series_index",
    "year", "language", "description", "cover_url", "cover_path", "source",
    "external_id", "score", "status", "note", "last_position",
]


def _row_to_item(row: sqlite3.Row) -> Item:
    data = dict(row)
    data["authors"] = json.loads(data.get("authors") or "[]")
    return Item(**{k: data.get(k) for k in _COLUMNS})


class LibraryIndex:
    def __init__(self, path: Path | None = None):
        self._path = path or (data_dir() / "library.sqlite")
        self._con = sqlite3.connect(str(self._path), check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._con.execute(SCHEMA)
            self._con.commit()

    def close(self) -> None:
        self._con.close()

    def backup_to(self, destination: Path) -> None:
        """Sichert die Datenbank nach `destination` - sicher aufrufbar,
        waehrend die App laeuft (siehe deskkit.backup)."""
        with self._lock:
            backup_database(self._con, destination)

    # --- Scannen --------------------------------------------------------
    def mark_scanned(self, path: Path, root: Path, title: str = "",
                     authors: list[str] | None = None, series: str = "",
                     series_index: str = "", year: int | None = None,
                     language: str = "") -> None:
        """Datei bekannt machen, falls neu - vorhandene Zuordnung bleibt."""
        with self._lock:
            self._con.execute(
                "INSERT INTO items (path, root, title, authors, series, "
                "series_index, year, language, scanned_at) "
                "VALUES (?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(path) DO UPDATE SET scanned_at=excluded.scanned_at",
                (str(path), str(root), title, json.dumps(authors or []),
                 series, series_index, year, language, time.time()))
            self._con.commit()

    def forget_missing(self, root: Path, existing: set[str]) -> int:
        """Eintraege loeschen, deren Datei unter `root` nicht mehr da ist."""
        with self._lock:
            rows = self._con.execute(
                "SELECT path FROM items WHERE root=?", (str(root),)).fetchall()
            gone = [r["path"] for r in rows if r["path"] not in existing]
            if gone:
                self._con.executemany(
                    "DELETE FROM items WHERE path=?", [(p,) for p in gone])
                self._con.commit()
            return len(gone)

    def forget_missing_under(self, folder: Path, existing: set[str]) -> int:
        """Wie `forget_missing`, aber nur fuer Eintraege unterhalb `folder` -
        fuer einen gezielten Scan nur eines einzelnen Buchs statt des ganzen
        Wurzelordners."""
        prefix = str(folder).rstrip("/") + "/"
        with self._lock:
            rows = self._con.execute(
                "SELECT path FROM items WHERE path LIKE ? ESCAPE '\\'",
                (prefix.replace("%", "\\%").replace("_", "\\_") + "%",)).fetchall()
            gone = [r["path"] for r in rows if r["path"] not in existing]
            if gone:
                self._con.executemany(
                    "DELETE FROM items WHERE path=?", [(p,) for p in gone])
                self._con.commit()
            return len(gone)

    def remove_path(self, path: Path) -> None:
        """Einzelnen Eintrag entfernen - nachdem seine Datei geloescht wurde."""
        with self._lock:
            self._con.execute("DELETE FROM items WHERE path=?", (str(path),))
            self._con.commit()

    def remove_under(self, folder: Path) -> None:
        """Alle Eintraege unterhalb `folder` entfernen - nach Loeschen des
        ganzen Verzeichnisses."""
        prefix = str(folder).rstrip("/") + "/"
        with self._lock:
            self._con.execute(
                "DELETE FROM items WHERE path LIKE ? ESCAPE '\\'",
                (prefix.replace("%", "\\%").replace("_", "\\_") + "%",))
            self._con.commit()

    # --- Zuordnung --------------------------------------------------------
    def set_match(self, path: Path, title: str, authors: list[str],
                  series: str, series_index: str, year: int | None,
                  description: str, cover_url: str | None, source: str,
                  external_id: str, score: int, status: str,
                  note: str = "") -> None:
        with self._lock:
            self._con.execute(
                "UPDATE items SET title=?, authors=?, series=?, "
                "series_index=?, year=?, description=?, cover_url=?, "
                "source=?, external_id=?, score=?, status=?, note=?, "
                "matched_at=? WHERE path=?",
                (title, json.dumps(authors), series, series_index, year,
                 description, cover_url, source, external_id, score, status,
                 note, time.time(), str(path)))
            self._con.commit()

    def set_status(self, path: Path, status: str, note: str = "") -> None:
        with self._lock:
            self._con.execute(
                "UPDATE items SET status=?, note=? WHERE path=?",
                (status, note, str(path)))
            self._con.commit()

    def set_cover_path(self, path: Path, cover_path: str) -> None:
        with self._lock:
            self._con.execute(
                "UPDATE items SET cover_path=? WHERE path=?",
                (cover_path, str(path)))
            self._con.commit()

    def set_last_position(self, path: Path, position: int) -> None:
        with self._lock:
            self._con.execute(
                "UPDATE items SET last_position=? WHERE path=?",
                (position, str(path)))
            self._con.commit()

    def update_path(self, old: Path, new: Path) -> None:
        with self._lock:
            self._con.execute(
                "UPDATE items SET path=? WHERE path=?", (str(new), str(old)))
            self._con.commit()

    # --- Lesen --------------------------------------------------------
    def get(self, path: Path) -> Item | None:
        with self._lock:
            row = self._con.execute(
                "SELECT * FROM items WHERE path=?", (str(path),)).fetchone()
        return _row_to_item(row) if row else None

    def list_books(self) -> list[Item]:
        with self._lock:
            rows = self._con.execute(
                "SELECT * FROM items ORDER BY title COLLATE NOCASE").fetchall()
        return [_row_to_item(r) for r in rows]

    def series_groups(self) -> list[tuple[str, list[Item]]]:
        """Buecher nach Serie gruppiert (Gross-/Kleinschreibung egal, siehe
        die entsprechende Loesung in moviedesk/library.py), Titel
        alphabetisch. Buecher ohne Serie tauchen hier nicht auf."""
        by_key: dict[str, list[Item]] = {}
        for item in self.list_books():
            if not item.series:
                continue
            key = item.series.casefold()
            by_key.setdefault(key, []).append(item)
        groups = [
            (next((i.series for i in items if i.source), None)
             or items[0].series, items)
            for items in by_key.values()
        ]
        return sorted(groups, key=lambda kv: kv[0].casefold())

    def unresolved(self) -> list[Item]:
        with self._lock:
            rows = self._con.execute(
                "SELECT * FROM items WHERE status IN (?, ?) "
                "ORDER BY path", (STATUS_UNSURE, STATUS_UNMATCHED)).fetchall()
        return [_row_to_item(r) for r in rows]

    def all_items(self) -> list[Item]:
        with self._lock:
            rows = self._con.execute("SELECT * FROM items ORDER BY path").fetchall()
        return [_row_to_item(r) for r in rows]
