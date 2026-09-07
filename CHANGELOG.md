# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Noch kein Release getaggt — alles bislang unter „Unreleased“.

## [Unreleased]

### Added

- „Serie zuweisen …“ (Rechtsklick, ein oder mehrere Bücher) — setzt nur
  Serie und Band, unabhängig vom sonstigen Metadaten-Abgleich, alles
  andere bleibt unangetastet. Bei mehreren ausgewählten Büchern
  gemeinsam für alle, mit optionaler fortlaufender Nummerierung.
- Zwei feste Zusatzfilter in der Serien-Liste, mit Live-Anzahl:
  **Nicht zugeordnet** (Status ungleich „zugeordnet“) und **Ohne Serie**
  (leeres Serien-Feld) — um gezielt durch das zu arbeiten, was noch
  Aufmerksamkeit braucht, statt die ganze Bibliothek durchzusehen.
- `{series_index}` in der Umbenennen-Vorlage unterstützt jetzt eine
  Breitenangabe für führende Nullen: `{series_index:02}` macht aus `1`
  `01`, `{series_index:03}` macht `007` aus `7`. Wirkt nur bei einer
  reinen Zahl — Dezimalzahlen und reiner Text bleiben unverändert.
- Cover dauerhaft speichern (`coverstore.py`), statt nur im flüchtigen
  Thumbnail-Cache: unter *Einstellungen → Bibliothek* wählbar zwischen
  „nicht speichern“ (Vorgabe), „neben der Buchdatei“ (gleicher Name,
  `.jpg`) und „in einem eigenen Ordner“. Lädt automatisch beim Zuordnen
  herunter, egal ob automatisch oder von Hand.
- „Manuell zuordnen“: neuer Reiter **Von Hand eintragen** im Dialog —
  Titel, Autor(en), Serie, Band, Jahr, Beschreibung und Cover-URL direkt
  selbst eintippen, für den Fall, dass auch keine Online-Quelle etwas
  findet (kleine Self-Publishing-Reihen sind oft nirgends katalogisiert).
- [Google Books](https://books.google.com) als zweite Metadaten-Quelle,
  neben OpenLibrary — kostenlos, kein API-Key nötig, per Vorgabe aktiv,
  unter *Einstellungen → Quellen* abschaltbar. Deckt oft Self-Publishing-/
  Kindle-Titel ab, die OpenLibrary nicht kennt.
- MOBI/AZW3/AZW-Unterstützung (nur lesend): sichten, lesen, Metadaten
  automatisch abgleichen. Titel mit KF8-Anteil (praktisch alle AZW3 und
  neueren MOBI-Titel) werden intern zu einem gleichwertigen EPUB entpackt
  und wie EPUB kapitelweise gelesen; ältere reine MOBI7-Titel ohne
  KF8-Anteil landen als ein durchgehendes „Kapitel“ im Reader.
  Verschlüsselte (DRM-geschützte) Dateien werden erkannt und nicht
  entpackt. Zurückschreiben (`Strg+S`) bleibt EPUB/PDF vorbehalten — das
  Binärformat lässt sich nicht sicher inkrementell patchen.
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

### Fixed

- Automatisches Zuordnen fand bei Titeln mit Klammerzusatz wie
  „(German Edition)“ oder „(dunkle Edition)“ (häufig bei Amazon-/Kindle-
  Ebooks) oft gar nichts, selbst bei bekannten Büchern — der Zusatz
  landete unbereinigt in der Suchanfrage. Ein konkreter, real
  aufgetretener Fall: „QualityLand (dunkle Edition)“ fand nichts,
  „QualityLand“ allein sofort einen 100%-Treffer. Die Suchanfrage wird
  jetzt um solche Zusätze bereinigt (`providers/base.py: search_title()`)
  — der gespeicherte Titel selbst bleibt unverändert.
- Suche fand bei einer Serie nur den einen Band, dessen eigener Titel
  zufällig genauso hieß wie die Serie — die übrigen Bände (eigener Titel,
  nur über den Serienname zusammengehalten) blieben unsichtbar. Die Suche
  prüft jetzt zusätzlich zu Titel/Autor auch den Serienname.

[Unreleased]: https://github.com/aaaaaprvdgrwwelt/bookdesk/commits/main
