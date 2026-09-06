"""Hauptfenster: Bibliotheks-Raster, Scan, Lesen, Umbenennen."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QProgressDialog,
    QSizePolicy, QSplitter, QStatusBar,
    QToolBar, QToolButton, QVBoxLayout, QWidget,
)
from send2trash import send2trash

from deskkit.actions import ActionRegistry
from deskkit.paths import subfolder_of
from deskkit.tiles import STATUS_ROLE, SUBTITLE_ROLE, CoverDelegate, configure_grid

from . import matcher, renamer, scanner
from .appicon import icon as app_icon
from .config import Settings
from .formats.base import BookMeta
from .formats.base import write_metadata as write_book_metadata
from .helpdialog import HelpDialog
from .i18n import _, set_language
from .icons import icon as tool_icon
from .library import Item, LibraryIndex
from .matchdialog import MatchDialog
from .metapanel import MetaPanel
from .reader import ReaderWindow
from .renamedialog import RenameDialog
from .settingsdialog import SettingsDialog
from .thumbs import CoverLoader

TILE_W = 140
COVER_H = 190

STATUS_LABEL = {
    "matched": _("zugeordnet"),
    "unsure": _("unsicher"),
    "unmatched": _("nicht zugeordnet"),
    "error": _("Fehler"),
}
STATUS_COLOR = {
    "matched": QColor(46, 160, 90),
    "unsure": QColor(214, 154, 40),
    "unmatched": QColor(150, 150, 150),
    "error": QColor(192, 57, 43),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BookDesk")
        self.setWindowIcon(app_icon())
        self.resize(1200, 760)

        self.qsettings = QSettings("bookdesk", "bookdesk")
        self.settings = Settings.load(self.qsettings)
        set_language(self.settings.language)

        self.library = LibraryIndex()
        self.loader = CoverLoader(self)
        self.loader.ready.connect(self._on_cover)

        self._search_text = ""
        self._build_central()
        self._build_actions()
        self._build_toolbar()
        self._build_menubar()
        self.setStatusBar(QStatusBar())

        self.refresh_view()

    # ------------------------------------------------------------------
    def _build_central(self) -> None:
        self.series_list = QListWidget()
        self.series_list.itemSelectionChanged.connect(self._on_series_selected)
        series_panel = QWidget()
        series_layout = QVBoxLayout(series_panel)
        series_layout.setContentsMargins(0, 0, 0, 0)
        series_layout.addWidget(QLabel(_("Serien")))
        series_layout.addWidget(self.series_list)

        self.book_list = QListWidget()
        configure_grid(self.book_list, CoverDelegate(
            STATUS_COLOR, tile_w=TILE_W, cover_h=COVER_H, parent=self.book_list))
        self.book_list.itemSelectionChanged.connect(self._on_book_selected)
        self.book_list.itemDoubleClicked.connect(lambda _i: self.read_selected())
        self.book_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.book_list.customContextMenuRequested.connect(self._book_context_menu)

        self.meta = MetaPanel(self.loader)

        split = QSplitter()
        split.addWidget(series_panel)
        split.addWidget(self.book_list)
        split.addWidget(self.meta)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)
        split.setStretchFactor(2, 2)
        self.setCentralWidget(split)

    def _build_actions(self) -> None:
        self.actions_map = ActionRegistry(self, _)
        a = self.actions_map
        a.add("add_root", "Ordner hinzufuegen …", slot=self._add_book_root)
        a.add("scan", "Scannen", "F5", self.scan_all, tool_icon("refresh"))
        a.add("auto_match", "Automatisch zuordnen", "Ctrl+T", self.auto_match,
             tool_icon("match"))
        a.add("rename", "Umbenennen …", "Ctrl+R", self.rename_preview,
             tool_icon("rename"))
        a.add("save_metadata", "Metadaten in Datei speichern …", "Ctrl+S",
             self.write_metadata_to_file, tool_icon("check"))
        a.add("read", "Lesen", "Return", self.read_selected, tool_icon("read"),
             target=self.book_list, shortcut_context=Qt.WidgetWithChildrenShortcut)
        a.add("delete", "Loeschen …", "Del", self.delete_selected,
             tool_icon("delete"), target=self.book_list,
             shortcut_context=Qt.WidgetWithChildrenShortcut)
        a.add("search", "Suchen", "Ctrl+F", self.focus_search)
        a.add("settings", "Einstellungen …", "Ctrl+,", self.open_settings,
             tool_icon("settings"))
        a.add("help", "Hilfe …", "F1", self.open_help, tool_icon("help"))
        a.add("quit", "Beenden", "Ctrl+Q", self.close)

    def _build_toolbar(self) -> None:
        bar = QToolBar()
        bar.setMovable(False)
        bar.setIconSize(QSize(20, 20))
        self.addToolBar(bar)
        a = self.actions_map

        add_action = bar.addAction(tool_icon("folder_new"), _("Ordner hinzufuegen …"))
        add_action.triggered.connect(self._add_book_root)
        button = bar.widgetForAction(add_action)
        if isinstance(button, QToolButton):
            button.setPopupMode(QToolButton.DelayedPopup)

        bar.addAction(a["scan"])
        bar.addAction(a["auto_match"])
        bar.addSeparator()
        bar.addAction(a["read"])
        bar.addAction(a["rename"])
        bar.addAction(a["delete"])
        bar.addSeparator()
        bar.addAction(a["settings"])
        bar.addAction(a["help"])

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bar.addWidget(spacer)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(_("Suchen …"))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(240)
        self.search_edit.textChanged.connect(self._on_search_changed)
        bar.addWidget(self.search_edit)

    def _build_menubar(self) -> None:
        a = self.actions_map
        bar = self.menuBar()

        menu = bar.addMenu(_("&Datei"))
        menu.addAction(a["add_root"])
        menu.addSeparator()
        menu.addAction(a["scan"])
        menu.addSeparator()
        menu.addAction(a["quit"])

        menu = bar.addMenu(_("&Bearbeiten"))
        menu.addAction(a["rename"])
        menu.addAction(a["delete"])

        menu = bar.addMenu(_("&Ansicht"))
        menu.addAction(a["search"])

        menu = bar.addMenu(_("E&xtras"))
        menu.addAction(a["auto_match"])
        menu.addAction(a["save_metadata"])
        menu.addSeparator()
        menu.addAction(a["settings"])

        bar.addMenu(_("&Hilfe")).addAction(a["help"])

    def focus_search(self) -> None:
        self.search_edit.selectAll()
        self.search_edit.setFocus()

    # --- Ordner verwalten -------------------------------------------------
    def _add_book_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, _("Ordner waehlen"))
        if not folder:
            return
        self.settings.book_roots.append(folder)
        self.settings.save(self.qsettings)
        self.scan_all()

    # --- Scannen -----------------------------------------------------
    def scan_all(self) -> None:
        if not self.settings.book_roots:
            QMessageBox.information(
                self, _("Scannen"), _("Bitte mindestens einen Ordner hinzufuegen."))
            return

        progress = QProgressDialog(_("Scanne …"), _("Abbrechen"), 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        thread, worker = scanner.run_in_thread(self.settings.book_roots, self.library)
        worker.progress.connect(progress.setLabelText)
        progress.canceled.connect(worker.stop)
        thread.finished.connect(progress.close)
        thread.finished.connect(self.refresh_view)
        thread.finished.connect(
            lambda: self.statusBar().showMessage(_("Scan abgeschlossen."), 4000))
        self._scan_thread, self._scan_worker = thread, worker
        thread.start()
        progress.exec()
        thread.wait(5000)

    def _scan_book(self, book: Item) -> None:
        """Nur den Ordner des ausgewaehlten Buchs neu einlesen, statt jedes
        Mal den ganzen Wurzelordner zu durchsuchen."""
        root = Path(book.root)
        folder = subfolder_of(Path(book.path), root)
        progress = QProgressDialog(_("Scanne …"), _("Abbrechen"), 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        thread, worker = scanner.run_folder_in_thread(folder, root, self.library)
        worker.progress.connect(progress.setLabelText)
        progress.canceled.connect(worker.stop)
        thread.finished.connect(progress.close)
        thread.finished.connect(self.refresh_view)
        thread.finished.connect(
            lambda: self.statusBar().showMessage(_("Scan abgeschlossen."), 4000))
        self._scan_thread, self._scan_worker = thread, worker
        thread.start()
        progress.exec()
        thread.wait(5000)

    # --- Ansicht befuellen --------------------------------------------
    def refresh_view(self) -> None:
        self._fill_series()
        self._fill_books()

    def _on_search_changed(self, text: str) -> None:
        self._search_text = text.strip().lower()
        self._fill_books()

    def _selected_series(self) -> str | None:
        items = self.series_list.selectedItems()
        return items[0].data(Qt.UserRole) if items else None

    def _fill_series(self) -> None:
        selected_titles = {i.data(Qt.UserRole) for i in self.series_list.selectedItems()}
        self.series_list.clear()
        all_item = QListWidgetItem(_("Alle Buecher"))
        all_item.setData(Qt.UserRole, None)
        self.series_list.addItem(all_item)
        to_reselect = [all_item] if None in selected_titles or not selected_titles else []
        for name, items in self.library.series_groups():
            list_item = QListWidgetItem(f"{name}  ({len(items)})")
            list_item.setData(Qt.UserRole, name)
            self.series_list.addItem(list_item)
            if name in selected_titles:
                to_reselect.append(list_item)
        if to_reselect:
            self.series_list.setCurrentItem(to_reselect[0])
            for list_item in to_reselect:
                list_item.setSelected(True)
        elif not selected_titles:
            self.series_list.setCurrentItem(all_item)

    def _on_series_selected(self) -> None:
        self._fill_books()

    def _fill_books(self) -> None:
        selected_ids = {i.data(Qt.UserRole).id for i in self.book_list.selectedItems()}
        self.book_list.clear()
        series = self._selected_series()
        to_reselect = []
        for item in self.library.list_books():
            if series is not None and item.series != series:
                continue
            if self._search_text and not (
                    self._search_text in (item.title or "").lower()
                    or self._search_text in item.author_line.lower()):
                continue
            list_item = QListWidgetItem(item.title or Path(item.path).stem)
            list_item.setData(Qt.UserRole, item)
            list_item.setData(SUBTITLE_ROLE, item.author_line)
            list_item.setData(STATUS_ROLE, item.status)
            status_line = STATUS_LABEL.get(item.status, item.status)
            if item.note:
                status_line += f" - {item.note}"
            list_item.setToolTip(f"{item.path}\n{status_line}")
            key = item.cover_url or item.path
            pm = self.loader.get(key) if key else None
            if pm and not pm.isNull():
                list_item.setIcon(QIcon(pm))
            self.book_list.addItem(list_item)
            if item.id in selected_ids:
                to_reselect.append(list_item)
        if to_reselect:
            self.book_list.setCurrentItem(to_reselect[0])
            for list_item in to_reselect:
                list_item.setSelected(True)

    def _on_cover(self, key: str, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        for row in range(self.book_list.count()):
            item = self.book_list.item(row)
            book: Item = item.data(Qt.UserRole)
            if (book.cover_url or book.path) == key:
                item.setIcon(QIcon(pixmap))

    # --- Auswahl -----------------------------------------------------
    def _selected_books(self) -> list[Item]:
        return [i.data(Qt.UserRole) for i in self.book_list.selectedItems()]

    def _current_book(self) -> Item | None:
        items = self._selected_books()
        return items[0] if items else None

    def _on_book_selected(self) -> None:
        self.meta.show_item(self._current_book())

    # --- Automatisches Zuordnen ------------------------------------------
    def auto_match(self) -> None:
        config = self.settings.build_config()
        if not config.providers:
            QMessageBox.warning(
                self, _("Automatisch zuordnen"),
                _("Keine Quelle aktiviert.") + " " + _("Einstellungen …"))
            return
        selected = self._selected_books()
        if selected:
            paths = [Path(i.path) for i in selected]
        else:
            paths = [Path(i.path) for i in self.library.unresolved()]
        if not paths:
            QMessageBox.information(
                self, _("Automatisch zuordnen"),
                _("Nichts zu tun - alles bereits zugeordnet."))
            return

        progress = QProgressDialog(
            _("Ordne zu …"), _("Abbrechen"), 0, len(paths), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        thread, worker = matcher.run_in_thread(paths, config, self.library)
        worker.progress.connect(lambda i, n, name: (
            progress.setMaximum(n), progress.setValue(i), progress.setLabelText(name)))
        progress.canceled.connect(worker.stop)
        thread.finished.connect(progress.close)
        thread.finished.connect(self.refresh_view)
        self._match_thread, self._match_worker = thread, worker
        thread.start()
        progress.exec()
        thread.wait(5000)

    def _manual_match(self, item: Item) -> None:
        config = self.settings.build_config()
        dialog = MatchDialog(item, config, self.library, self.loader, self)
        if dialog.exec():
            self.refresh_view()

    # --- Metadaten in die Datei zurueckschreiben --------------------------
    def write_metadata_to_file(self) -> None:
        """Anders als Umbenennen/Loeschen aendert das die Originaldatei
        selbst - deshalb ausdruecklich bestaetigen lassen und nie
        automatisch beim Scannen/Zuordnen aufrufen."""
        items = self._selected_books()
        if not items:
            QMessageBox.information(
                self, _("Metadaten speichern …"),
                _("Bitte mindestens eine Datei waehlen."))
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(_("Metadaten speichern …"))
        box.setText(
            _("Metadaten von {n} Datei(en) direkt in die Datei schreiben?")
            .format(n=len(items)))
        box.setInformativeText(_(
            "Das aendert die Originaldatei. Serieninformation wird bei PDF "
            "nicht unterstuetzt und dabei nicht geschrieben."))
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        if box.exec() != QMessageBox.Yes:
            return

        errors: list[str] = []
        for item in items:
            path = Path(item.path)
            meta = BookMeta(
                title=item.title, authors=item.authors, series=item.series,
                series_index=item.series_index, year=item.year,
                description=item.description)
            try:
                write_book_metadata(path, meta)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{path.name}: {exc}")
        if errors:
            QMessageBox.warning(
                self, _("Metadaten speichern …"),
                _("Nicht alles konnte gespeichert werden:") + "\n"
                + "\n".join(errors))
        else:
            QMessageBox.information(
                self, _("Metadaten speichern …"), _("Metadaten gespeichert."))

    # --- Lesen ---------------------------------------------------------
    def read_selected(self) -> None:
        item = self._current_book()
        if item is None:
            return
        path = Path(item.path)
        if not path.exists():
            QMessageBox.warning(
                self, _("Lesen"),
                _("Datei nicht gefunden - eventuell verschoben oder geloescht."))
            return
        dialog = ReaderWindow(item, self.library, self)
        dialog.exec()
        self.refresh_view()

    # --- Umbenennen ------------------------------------------------------
    def rename_preview(self) -> None:
        items = self._selected_books()
        if not items:
            items = self.library.list_books()
        ops = renamer.build_plan(items, self.settings.rename_template)
        unchanged = sum(1 for op in ops if op.status == "same")
        pending = [op for op in ops if op.status != "same"]
        if not pending:
            QMessageBox.information(
                self, _("Umbenennen …"),
                _("Nichts zu tun - alle Dateien bereits korrekt benannt."))
            return
        dialog = RenameDialog(pending, self.library, unchanged, self)
        if dialog.exec():
            self.refresh_view()

    # --- Loeschen --------------------------------------------------------
    def delete_selected(self) -> None:
        items = self._selected_books()
        if not items:
            QMessageBox.information(
                self, _("Loeschen …"), _("Bitte mindestens eine Datei waehlen."))
            return
        names = "\n".join(f"- {Path(i.path).name}" for i in items[:10])
        if len(items) > 10:
            names += f"\n… (+{len(items) - 10})"
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(_("Loeschen …"))
        box.setText(
            _("{n} Datei(en) in den Papierkorb verschieben?").format(n=len(items)))
        box.setInformativeText(names)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        if box.exec() != QMessageBox.Yes:
            return
        errors: list[str] = []
        for item in items:
            path = Path(item.path)
            try:
                send2trash(str(path))
                self.library.remove_path(path)
            except OSError as exc:
                errors.append(f"{path.name}: {exc}")
        self.refresh_view()
        if errors:
            QMessageBox.warning(
                self, _("Loeschen …"),
                _("Nicht alles konnte geloescht werden:") + "\n" + "\n".join(errors))

    # --- Kontextmenue -------------------------------------------------
    def _book_context_menu(self, pos) -> None:
        items = self._selected_books()
        if not items:
            return
        menu = QMenu(self)
        menu.addAction(self.actions_map["read"])
        menu.addSeparator()
        menu.addAction(self.actions_map["auto_match"])
        if len(items) == 1:
            menu.addAction(_("Manuell zuordnen …"),
                           lambda: self._manual_match(items[0]))
            menu.addAction(
                tool_icon("refresh"), _("Nur dieses Buch scannen"),
                # Erst starten, wenn das Kontextmenue sich geschlossen hat -
                # ein QThread + modaler Dialog waehrend dessen eigener
                # Event-Schleife (Popup-Grab) kann sonst abstuerzen.
                lambda: QTimer.singleShot(0, lambda: self._scan_book(items[0])))
        menu.addSeparator()
        menu.addAction(self.actions_map["rename"])
        menu.addAction(self.actions_map["save_metadata"])
        menu.addSeparator()
        menu.addAction(self.actions_map["delete"])
        menu.exec(self.book_list.viewport().mapToGlobal(pos))

    # --- Einstellungen/Hilfe --------------------------------------------
    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() and dialog.result_settings:
            self.settings = dialog.result_settings
            self.settings.save(self.qsettings)
            set_language(self.settings.language)
            self.refresh_view()

    def open_help(self) -> None:
        HelpDialog(self).exec()

    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802
        for attr in ("_scan_thread", "_match_thread"):
            thread = getattr(self, attr, None)
            if thread is not None and thread.isRunning():
                thread.wait(2000)
        self.library.close()
        super().closeEvent(event)
