"""Bibliotheksordner einlesen: Ebook-Dateien finden, Metadaten lesen."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from .formats.base import BOOK_EXTENSIONS, is_drm_protected, read_metadata
from .i18n import _
from .library import STATUS_ERROR, LibraryIndex
from .parser import parse_filename


def find_books(root: Path) -> list[Path]:
    """Alle Ebook-Dateien unter `root`."""
    if not root.is_dir():
        return []
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in BOOK_EXTENSIONS:
            continue
        found.append(path)
    found.sort(key=lambda p: str(p).casefold())
    return found


def _scan_one(path: Path, root: Path, library: LibraryIndex) -> None:
    """Eine einzelne Datei einlesen - geteilt vom vollen und vom gezielten
    Scan (siehe `scan_folder`)."""
    meta = read_metadata(path)
    title = meta.title
    authors = meta.authors
    if not title or not authors:
        guess = parse_filename(path)
        title = title or guess.title
        authors = authors or ([guess.author] if guess.author else [])
    library.mark_scanned(
        path, root, title, authors, meta.series, meta.series_index,
        meta.year, meta.language)
    if is_drm_protected(path):
        # Sonst liegt die Datei stillschweigend mit leeren/geratenen
        # Metadaten in der Bibliothek, ohne dass ersichtlich ist, warum
        # Titel/Autor fehlen bzw. warum sich die Datei nicht lesen laesst.
        library.set_status(
            path, STATUS_ERROR,
            _("DRM-geschuetzt - kann nicht gelesen oder umbenannt werden."))


class ScanWorker(QObject):
    """Laeuft im eigenen Thread - Verzeichnisse koennen gross sein, die
    Oberflaeche soll dabei nicht einfrieren."""

    progress = Signal(str)   # aktuell durchsuchter Ordner
    finished = Signal()

    def __init__(self, book_roots: list[str], library: LibraryIndex):
        super().__init__()
        self.book_roots = book_roots
        self.library = library
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        for root in self.book_roots:
            if self._stop:
                break
            self.progress.emit(root)
            root_path = Path(root)
            found = find_books(root_path)
            for path in found:
                if self._stop:
                    break
                _scan_one(path, root_path, self.library)
            # find_books() lief vollstaendig, auch bei einem Abbruch mitten
            # in der Schleife darueber - das Aufraeumen bleibt deshalb sicher
            # auf tatsaechlich fehlende Dateien beschraenkt.
            self.library.forget_missing(root_path, {str(p) for p in found})
        self.finished.emit()


def run_in_thread(book_roots: list[str], library: LibraryIndex):
    """Gibt (thread, worker) zurueck - der Aufrufer verbindet die Signale."""
    thread = QThread()
    worker = ScanWorker(book_roots, library)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    return thread, worker


def scan_folder(folder: Path, root: Path, library: LibraryIndex,
                should_stop=None) -> None:
    """Nur `folder` neu einlesen - z. B. der Ordner eines einzelnen Buchs,
    statt des ganzen Wurzelordners `root`. Eintraege werden weiterhin unter
    `root` gefuehrt (wie beim vollen Scan), aber nur unterhalb von `folder`
    verglichen/aufgeraeumt. `should_stop` ist ein parameterloses Callable,
    das True liefert, sobald abgebrochen werden soll (siehe
    FolderScanWorker.stop())."""
    should_stop = should_stop or (lambda: False)
    found = find_books(folder)
    for path in found:
        if should_stop():
            break
        _scan_one(path, root, library)
    library.forget_missing_under(folder, {str(p) for p in found})


class FolderScanWorker(QObject):
    """Wie `ScanWorker`, aber fuer einen einzelnen Unterordner statt aller
    konfigurierten Wurzelordner - fuer den gezielten Scan aus dem
    Kontextmenue eines einzelnen Buchs."""

    progress = Signal(str)
    finished = Signal()

    def __init__(self, folder: Path, root: Path, library: LibraryIndex):
        super().__init__()
        self.folder = folder
        self.root = root
        self.library = library
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        self.progress.emit(str(self.folder))
        scan_folder(self.folder, self.root, self.library,
                   should_stop=lambda: self._stop)
        self.finished.emit()


def run_folder_in_thread(folder: Path, root: Path, library: LibraryIndex):
    """Gibt (thread, worker) zurueck - der Aufrufer verbindet die Signale."""
    thread = QThread()
    worker = FolderScanWorker(folder, root, library)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    return thread, worker
