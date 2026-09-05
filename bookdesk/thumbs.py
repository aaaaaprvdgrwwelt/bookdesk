"""Cover-Thumbnails: Hintergrund-Erzeugung mit Cache auf der Platte."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

from deskkit.thumbs import ThumbLoader as _ThumbLoader

from .formats.base import cover_bytes

THUMB_SIZE = 220


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    d = Path(base) / "bookdesk" / "covers"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_path(key: str) -> Path:
    if key.startswith(("http://", "https://")):
        return cache_dir() / (hashlib.sha1(key.encode()).hexdigest() + ".jpg")
    path = Path(key)
    try:
        st = path.stat()
        cache_key = f"{path.resolve()}|{st.st_mtime_ns}|{st.st_size}|{THUMB_SIZE}"
    except OSError:
        cache_key = key
    return cache_dir() / (hashlib.sha1(cache_key.encode()).hexdigest() + ".jpg")


def _raw_bytes(key: str) -> bytes | None:
    if key.startswith(("http://", "https://")):
        try:
            response = requests.get(key, timeout=15)
            response.raise_for_status()
            return response.content
        except Exception:  # noqa: BLE001
            return None
    return cover_bytes(Path(key))


def _load(key: str) -> QImage:
    """`key` ist entweder ein lokaler Dateipfad (eingebettetes Cover wird
    extrahiert) oder eine http(s)-URL (Cover einer Online-Quelle,
    z. B. nach dem Zuordnen ueber OpenLibrary)."""
    img = QImage()
    cache = _cache_path(key)
    if cache.exists():
        img.load(str(cache))
    if img.isNull():
        data = _raw_bytes(key)
        if data:
            raw = QImage()
            raw.loadFromData(data)
            if not raw.isNull():
                img = raw.scaled(
                    THUMB_SIZE, THUMB_SIZE,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                try:
                    img.save(str(cache), "JPG")
                except Exception:  # noqa: BLE001
                    pass
    return img


class CoverLoader(_ThumbLoader):
    """Erzeugt Cover-Thumbnails nebenlaeufig und meldet sie per Signal."""

    def __init__(self, parent=None):
        super().__init__(_load, parent)

    def get(self, key: str | Path | None) -> QPixmap | None:
        if not key:
            return QPixmap()
        return super().get(str(key))

    def forget(self, key: str | Path) -> None:
        super().forget(str(key))
