"""Serie (und bei genau einem Buch: Band) fuer eine Auswahl von Buechern
zuweisen - unabhaengig vom eigentlichen Metadaten-Abgleich (siehe
matchdialog.py). Fuer den Fall, dass Buecher schon zugeordnet sind (oder
bewusst nicht online abgeglichen werden sollen) und nur die
Serienzugehoerigkeit fehlt - z. B. um mehrere Baende auf einen Schlag der
gleichen Serie zuzuordnen."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox,
)

from .i18n import _
from .library import Item, LibraryIndex


class SeriesDialog(QDialog):
    def __init__(self, items: list[Item], library: LibraryIndex, parent=None):
        super().__init__(parent)
        self.items = items
        self.library = library
        self.setWindowTitle(_("Serie zuweisen …"))

        form = QFormLayout(self)

        series_values = {item.series for item in items}
        default_series = items[0].series if len(series_values) == 1 else ""
        self.series_edit = QLineEdit(default_series)
        form.addRow(_("Serie"), self.series_edit)

        if len(items) == 1:
            self.index_edit = QLineEdit(items[0].series_index)
            self.auto_number = None
            form.addRow(_("Band"), self.index_edit)
        else:
            self.index_edit = None
            self.auto_number = QCheckBox(_("Fortlaufend nummerieren, ab"))
            self.auto_number.setChecked(True)
            self.start_number = QSpinBox()
            self.start_number.setRange(0, 9999)
            self.start_number.setValue(1)
            row = QHBoxLayout()
            row.addWidget(self.auto_number)
            row.addWidget(self.start_number, 1)
            form.addRow(row)
            hint = QLabel(_(
                "Nummeriert in der Reihenfolge, in der die Buecher gerade "
                "in der Liste stehen."))
            hint.setWordWrap(True)
            form.addRow(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        series = self.series_edit.text().strip()
        if not series:
            return
        if self.index_edit is not None:
            self.library.set_series(
                Path(self.items[0].path), series, self.index_edit.text().strip())
        else:
            auto = self.auto_number.isChecked()
            start = self.start_number.value()
            for offset, item in enumerate(self.items):
                index = str(start + offset) if auto else item.series_index
                self.library.set_series(Path(item.path), series, index)
        self.accept()
