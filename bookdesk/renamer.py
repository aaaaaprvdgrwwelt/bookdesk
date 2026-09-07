"""Zielpfade aus Vorlagen bauen und Umbenennungsplaene ausfuehren.

Reine Planung ist von der Ausfuehrung getrennt: `build_plan` fasst nur an,
was auf dem Papier passieren soll; erst `apply` ruehrt das Dateisystem an -
und auch das nur fuer die vom Nutzer bestaetigten Eintraege. Anders als bei
moviedesk wird nicht auf einen erfolgreichen Online-Abgleich gewartet - die
eingebetteten Metadaten reichen bei den meisten Ebooks schon.
"""
from __future__ import annotations

import glob
import re
import shutil
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from .i18n import _
from .library import Item, LibraryIndex

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

SIDECAR_EXTENSIONS = (".opf",)


def sanitize_segment(text: str) -> str:
    text = _INVALID.sub("", text).strip()
    text = text.rstrip(". ")
    return text or "_"


@dataclass
class RenameOp:
    old: Path
    new: Path
    root: Path = field(default_factory=Path)
    status: str = "ok"          # ok | same | conflict
    reason: str = ""
    warning: str = ""
    selected: bool = True


_DOUBLE_DASH = re.compile(r"\s*-\s*-\s*")
_TRAILING_DASH = re.compile(r"\s*-\s*$")
_EMPTY_PARENS = re.compile(r"\s*\(\s*\)")
_PATH_BREAKER = re.compile(r"[/\\]+")


def _safe_value(text) -> str:
    return _PATH_BREAKER.sub(" - ", str(text))


def _clean_empty_tokens(formatted: str) -> str:
    parts = []
    for part in formatted.split("/"):
        part = _EMPTY_PARENS.sub("", part)
        part = _DOUBLE_DASH.sub(" - ", part)
        part = _TRAILING_DASH.sub("", part)
        parts.append(part)
    return "/".join(p for p in parts if p.strip())


def _series_index_value(raw: str) -> int | float | str:
    """Als Zahl liefern, wenn `raw` eine ist - sonst unveraendert als Text.
    Nur so wirkt eine Breitenangabe in der Vorlage wie `{series_index:02}`
    tatsaechlich fuehrend auffuellend: str.format richtet Zahlen bei einer
    Breitenangabe rechtsbuendig aus (führende Nullen), Text dagegen
    linksbuendig (nachgestellte Nullen) - bei reinem Text kaeme bei ":02"
    also "10" -> "10" aber "5" -> "50" statt der gewuenschten "05" heraus."""
    raw = raw.strip()
    if not raw:
        return ""
    try:
        value = float(raw)
    except ValueError:
        return _safe_value(raw)
    return int(value) if value.is_integer() else value


def build_target(root: Path, item: Item, template: str) -> Path:
    ext = Path(item.path).suffix
    formatted = template.format(
        author=_safe_value(", ".join(item.authors) or _("Unbekannt")),
        series=_safe_value(item.series or ""),
        series_index=_series_index_value(item.series_index or ""),
        title=_safe_value(item.title or _("Unbekannt")),
        year=item.year or "", ext="")
    formatted = _clean_empty_tokens(formatted)
    segments = [sanitize_segment(s) for s in formatted.split("/") if s.strip()]
    segments[-1] += ext
    return root.joinpath(*segments)


def _title_warning(*raw_values: str) -> str:
    for value in raw_values:
        if value and _PATH_BREAKER.search(value):
            return _("Titel enthielt einen Schraegstrich - wurde durch "
                     "\" - \" ersetzt.")
    for value in raw_values:
        if value and _INVALID.search(value):
            return _("Titel enthielt Zeichen, die im Dateinamen nicht "
                     "erlaubt sind - wurden entfernt.")
    return ""


def build_plan(items: list[Item], template: str) -> list[RenameOp]:
    ops: list[RenameOp] = []
    for item in items:
        root = Path(item.root)
        old = Path(item.path)
        new = build_target(root, item, template)
        warning = _title_warning(item.title or "")
        status = "same" if new == old else "ok"
        ops.append(RenameOp(old, new, root=root, status=status, warning=warning))

    targets = Counter(op.new for op in ops if op.status != "same")
    for op in ops:
        if op.status == "same":
            continue
        if targets[op.new] > 1:
            op.status, op.reason = "conflict", _("Mehrere Dateien wollen dasselbe Ziel.")
        elif op.new.exists():
            op.status, op.reason = "conflict", _("Zieldatei existiert bereits.")
    return ops


def _move_sidecars(old: Path, new: Path) -> None:
    if not old.parent.is_dir():
        return
    pattern = glob.escape(old.stem) + "*"
    for candidate in old.parent.glob(pattern):
        if candidate == old or candidate.suffix.lower() not in SIDECAR_EXTENSIONS:
            continue
        extra = candidate.name[len(old.stem):]
        target = new.parent / f"{new.stem}{extra}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(candidate), str(target))
        except OSError:
            pass


def _cleanup_empty_dirs(folder: Path, root: Path) -> None:
    try:
        root = root.resolve()
        current = folder.resolve()
    except OSError:
        return
    while current != root and root in current.parents:
        try:
            next(current.iterdir())
            return
        except StopIteration:
            pass
        except OSError:
            return
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _apply_one(op: RenameOp, library: LibraryIndex) -> str | None:
    try:
        op.new.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(op.old), str(op.new))
        library.update_path(op.old, op.new)
        _move_sidecars(op.old, op.new)
        if op.root != Path():
            _cleanup_empty_dirs(op.old.parent, op.root)
        return None
    except OSError as exc:
        return str(exc)


def apply(ops: Iterable[RenameOp],
         library: LibraryIndex) -> list[tuple[RenameOp, str | None]]:
    results: list[tuple[RenameOp, str | None]] = []
    for op in ops:
        if not op.selected or op.status != "ok":
            continue
        results.append((op, _apply_one(op, library)))
    return results


class RenameWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(list)

    def __init__(self, ops: list[RenameOp], library: LibraryIndex):
        super().__init__()
        self.ops = [op for op in ops if op.selected and op.status == "ok"]
        self.library = library

    def run(self) -> None:
        results: list[tuple[RenameOp, str | None]] = []
        total = len(self.ops)
        for i, op in enumerate(self.ops, 1):
            self.progress.emit(i, total, op.new.name)
            results.append((op, _apply_one(op, self.library)))
        self.finished.emit(results)


def run_in_thread(ops: list[RenameOp], library: LibraryIndex):
    thread = QThread()
    worker = RenameWorker(ops, library)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    return thread, worker
