# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Noch kein Release getaggt — alles bislang unter „Unreleased“.

## [Unreleased]

### Added

- EPUB- und PDF-Unterstützung: sichten, lesen (kapitel- bzw. seitenweise),
  umbenennen, löschen.
- Metadaten-Abgleich gegen OpenLibrary (kostenlos, kein API-Key).
- Metadaten in die Originaldatei zurückschreiben (`Strg+S`), nur auf
  Wunsch — EPUB über eine sichere Kopie-Prüfe-Austausche-Kette.
- Reader-Zoom (`Strg++`/`Strg+-`/`Strg+0`) und Volltextsuche über alle
  Kapitel bzw. Seiten.
- Erkennung DRM-geschützter EPUBs (Adobe ADEPT/LCP), klar als Fehler
  markiert statt mit leeren Metadaten.
- Gezielter Scan nur eines einzelnen Buchs statt des ganzen Wurzelordners.
- Windows-Installer und macOS-Pakete (PyInstaller + Inno Setup), gebaut in
  CI bei einem Versions-Tag.
- `.desktop`-Eintrag für Quellinstallationen unter Linux.
- Scan-Fortschrittsdialog mit „Abbrechen“-Knopf.
- Testsuite (pytest) für Formate, Matcher, Bibliotheksindex, Reader,
  Scanner.
- CI (GitHub Actions): Tests bei jedem Push/PR.
- Projektseite unter `aaaaaprvdgrwwelt.github.io/bookdesk`.

### Changed

- Gemeinsame Bausteine (Kachel-Delegate, Ordnerliste) nach
  [deskkit](https://github.com/aaaaaprvdgrwwelt/deskkit) ausgelagert —
  geteilt mit MovieDesk, ComicDesk und AudioDesk.

[Unreleased]: https://github.com/aaaaaprvdgrwwelt/bookdesk/commits/main
