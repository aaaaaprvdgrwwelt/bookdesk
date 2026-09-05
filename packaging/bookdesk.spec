# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Bauplan fuer Windows und macOS.

Aufruf aus dem Projektordner:

    pyinstaller packaging/bookdesk.spec --noconfirm
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

HIER = Path(SPECPATH).resolve()
WURZEL = HIER.parent
#: deskkit liegt als Geschwister-Repo daneben und wird per "pip install -e"
#: eingebunden (siehe requirements.txt) - PyInstallers statische Analyse
#: folgt dem editable-Import-Hook nicht von selbst, deshalb Quellordner und
#: Submodule hier ausdruecklich mitgeben.
DESKKIT = WURZEL.parent / "deskkit"

datas = [(str(WURZEL / "bookdesk" / "assets"), "bookdesk/assets")]
datas += collect_data_files("ebooklib")

hiddenimports = []
hiddenimports += collect_submodules("bookdesk")
hiddenimports += collect_submodules("deskkit")
hiddenimports += collect_submodules("ebooklib")

block_cipher = None

a = Analysis(
    [str(HIER / "entry.py")],
    pathex=[str(WURZEL), str(DESKKIT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # Qt bringt viel mit, was ein Ebook-Verwalter nie braucht. Das spart
    # rund 100 MB im fertigen Paket.
    excludes=[
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore", "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia", "PySide6.QtBluetooth", "PySide6.QtSensors",
        "PySide6.QtDesigner", "PySide6.QtTest",
        "tkinter", "unittest", "pydoc_data",
    ],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BookDesk",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # kein Konsolenfenster beim Start
    icon=str(HIER / "bookdesk.ico") if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="BookDesk",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="BookDesk.app",
        icon=str(HIER / "bookdesk.icns"),
        bundle_identifier="de.bookdesk.BookDesk",
        info_plist={
            "CFBundleName": "BookDesk",
            "CFBundleDisplayName": "BookDesk",
            "NSHighResolutionCapable": True,
            # Ohne das startet die App auf Deutsch nur zufaellig richtig.
            "CFBundleDevelopmentRegion": "de",
            "CFBundleDocumentTypes": [{
                "CFBundleTypeName": "E-Book",
                "CFBundleTypeRole": "Viewer",
                "LSItemContentTypes": ["org.idpf.epub-container", "com.adobe.pdf"],
                "CFBundleTypeExtensions": ["epub", "pdf"],
            }],
        },
    )
