"""BookDesk - Dateimanager fuer Ebooks."""
from __future__ import annotations

import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from deskkit import theme

from .appicon import icon as app_icon
from .i18n import set_language
from .mainwindow import MainWindow


def selftest() -> int:
    """Kurzer Start ohne Fenster - fuer die Pruefung fertiger Pakete."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv[:1])
    theme.apply(app)
    app.setWindowIcon(app_icon())
    window = MainWindow()
    window.close()
    print("Qt: ok")
    print("Selbsttest bestanden.")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    app = QApplication(sys.argv)
    app.setApplicationName("BookDesk")
    app.setOrganizationName("bookdesk")
    set_language(QSettings("bookdesk", "bookdesk").value("language", "auto"))
    theme.apply(app)
    app.setWindowIcon(app_icon())
    app.setDesktopFileName("bookdesk")
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
