# BookDesk

[![Tests](https://github.com/aaaaaprvdgrwwelt/bookdesk/actions/workflows/tests.yml/badge.svg)](https://github.com/aaaaaprvdgrwwelt/bookdesk/actions/workflows/tests.yml)

Ein Dateimanager, der nur Ebooks kennt: sichten, lesen, Metadaten holen,
umbenennen, löschen. Python + Qt (PySide6), auf demselben
[deskkit](https://github.com/aaaaaprvdgrwwelt/deskkit)-Fundament wie
[MovieDesk](https://github.com/aaaaaprvdgrwwelt/moviedesk),
[ComicDesk](https://github.com/aaaaaprvdgrwwelt/comicdesk) und
[AudioDesk](https://github.com/aaaaaprvdgrwwelt/audiodesk). Läuft unter
Linux, Windows und macOS. Oberfläche auf Deutsch und Englisch.

Unterstützte Formate: **EPUB** (Kapitel-Reader), **PDF** (Seiten-Reader) und
**MOBI/AZW3/AZW** (nur lesend, siehe [Formate](#formate)). Metadaten
kommen zuerst aus der Datei selbst, ergänzt durch einen optionalen
Abgleich gegen [OpenLibrary](https://openlibrary.org) (kostenlos, kein
API-Key nötig).

> Status: nutzbar. Entwickelt und getestet unter Linux; Windows und macOS
> sollten funktionieren (reines Qt/Python), sind aber nicht manuell
> getestet — siehe [Bekannte Grenzen](#bekannte-grenzen).

## Installation

### Fertige Pakete (Windows, macOS)

Unter [Releases](https://github.com/aaaaaprvdgrwwelt/bookdesk/releases)
liegen ein Windows-Installer und je ein DMG für Apple Silicon und Intel.
Python muss dafür nicht installiert sein.

Beide sind **nicht signiert** — ein Zertifikat kostet mehr, als ein
kostenloses Projekt ausgeben mag. Deshalb einmalig:

* **Windows:** „Der Computer wurde geschützt“ → *Weitere Informationen* →
  *Trotzdem ausführen*.
* **macOS:** beim ersten Start *Rechtsklick auf BookDesk → Öffnen*, dann
  im Dialog *Öffnen*. Ein Doppelklick allein wird abgelehnt.

Wie die Pakete entstehen, steht in [packaging/](packaging/README.md).

### Aus dem Quelltext (Linux und alle anderen)

Voraussetzung ist Python 3.10 oder neuer. `deskkit` muss als
Geschwister-Ordner neben `bookdesk/` liegen (siehe `requirements.txt`,
`-e ../deskkit`):

```bash
git clone https://github.com/aaaaaprvdgrwwelt/deskkit.git
git clone https://github.com/aaaaaprvdgrwwelt/bookdesk.git
cd bookdesk
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Starten

```bash
./bookdesk.sh                 # oder: .venv/bin/python -m bookdesk
./install-desktop.sh          # Eintrag im Anwendungsmenue und Symbole anlegen (Linux)
```

Unter Windows/macOS entsprechend `.venv\Scripts\python -m bookdesk` bzw.
`.venv/bin/python -m bookdesk`.

## Erste Schritte

1. Über **Ordner hinzufügen …** einen Ebook-Ordner angeben.
2. **Scannen** (`F5`) liest den Ordner ein — Titel/Autor/Serie/Cover
   kommen dabei zuerst aus der Datei selbst (EPUB-Metadaten bzw.
   PDF-Dokumenteigenschaften).
3. **Automatisch zuordnen** (`Strg+T`) ergänzt fehlende Angaben und ein
   Cover über OpenLibrary. Unsichere oder fehlgeschlagene Treffer bleiben
   markiert und lassen sich per Rechtsklick → *Manuell zuordnen* von Hand
   nachtragen.
4. Doppelklick oder **Lesen** (`Enter`) öffnet den Reader — EPUB
   kapitelweise, PDF seitenweise. Die zuletzt gelesene Stelle wird
   gemerkt.

## Reader

Ein Fenster für beide Formate, mit Zoom und Volltextsuche:

* **Zoom** — `Strg++`/`Strg+-`/`Strg+0` (oder die A+/A-/100 %-Knöpfe).
  Bei EPUB ändert das die Schriftgröße, bei PDF die Renderauflösung
  (50–250 %).
* **Suche** — Eingabe im Suchfeld + `Enter`/◀/▶. Bei EPUB wird zunächst
  im aktuellen Kapitel gesucht, ohne Treffer der Reihe nach durch die
  übrigen Kapitel (mit Umlauf am Buchanfang/-ende). Bei PDF läuft die
  Suche über PyMuPDFs eigene Textsuche und springt zur nächsten/vorherigen
  Seite mit Treffer — ohne Textmarkierung auf der Seite selbst, nur der
  Sprung zur Fundstelle.
* **Navigation** — ←/→-Tasten oder die *Zurück*/*Weiter*-Knöpfe.

## DRM-geschützte EPUBs

EPUBs mit Adobe-ADEPT- oder LCP-Verschlüsselung lassen sich nicht lesen —
BookDesk erkennt das am `META-INF/encryption.xml`-Eintrag im Archiv und
markiert die Datei beim Scannen klar als **Fehler** mit dem Hinweis
„DRM-geschützt“, statt sie stillschweigend mit leerem oder geratenem Titel
in der Bibliothek zu führen.

## Metadaten-Quelle

**[OpenLibrary](https://openlibrary.org)** — kein API-Key nötig, per
Vorgabe aktiv, unter *Einstellungen → Quellen* abschaltbar. Liefert Titel,
Autor(en), Beschreibung und ein Cover, gesucht über Titel und Autor aus
den vorhandenen Metadaten bzw. dem Dateinamen. Die Metadaten werden nicht
automatisch in die Ebook-Datei zurückgeschrieben — dafür gibt es
**Metadaten in Datei speichern …** (`Strg+S`), ausdrücklich auf Wunsch.

## Formate

| Format | Lesen | Metadaten | Zurückschreiben |
|---|---|---|---|
| EPUB | ja, kapitelweise | OPF-Metadaten inkl. Calibre-Serieninformation | ja — OPF-Datei im Archiv wird ersetzt, alle anderen Dateien bleiben byte-identisch |
| PDF | ja, seitenweise (über [PyMuPDF](https://pymupdf.readthedocs.io/)) | Dokumenteigenschaften (Titel/Autor, falls gesetzt) — PDFs haben in der Regel keine Serieninformation | ja — inkrementell über PyMuPDF, kein Neuschreiben der ganzen Datei |
| MOBI / AZW3 / AZW | ja — über die reine-Python-Bibliothek [mobi](https://pypi.org/project/mobi/) (KindleUnpack) intern entpackt | Bei KF8-Titeln (praktisch alle AZW3 und neueren MOBI) wie EPUB, weil intern zu einem gleichwertigen EPUB entpackt wird; bei älteren reinen MOBI7-Titeln nur Titel/Autor/Sprache/Jahr aus der beigelegten OPF | **nein** — das Binärformat lässt sich nicht sicher inkrementell patchen; „Metadaten speichern …“ meldet das als Fehler statt still zu scheitern |

Zurückschreiben in EPUB läuft über einen sicheren Umweg: erst in eine
temporäre Datei schreiben, deren ZIP-Integrität prüfen, dann erst das
Original per atomarem `os.replace()` ersetzen — ein Fehler mittendrin
beschädigt nie die vorhandene Datei.

Bei MOBI7-Titeln (kein KF8-Anteil) schreibt KindleUnpack den gesamten Text
in eine einzige HTML-Datei — der Reader zeigt sie deshalb als ein
durchgehendes „Kapitel“ ohne Kapitel-Navigation, statt wie bei EPUB
kapitelweise zu blättern. Verschlüsselte (DRM-geschützte) MOBI/AZW3-Dateien
werden über das Encryption-Type-Feld im PalmDOC-Header erkannt und wie
DRM-geschützte EPUBs klar als Fehler markiert, statt entpackt zu werden.

## Umbenennen …

`Strg+R`, Vorschau vor jeder Änderung. Vorlage frei einstellbar unter
*Einstellungen → Umbenennen*, Vorgabe:

```
{author}/{series} #{series_index} - {title}{ext}
```

Platzhalter: `{author} {series} {series_index} {title} {year} {ext}`. Ein
`/` in der Vorlage legt eine neue Ordnerebene an.

## Nur ein einzelnes Buch neu scannen

Rechtsklick auf ein Buch → *Nur dieses Buch scannen*. Anders als bei
MovieDesk (Serie = eigener Ordner) gibt es dafür keine
Serien-weite Variante: Bücher gruppieren sich nach Metadaten
(`series`-Feld), nicht zuverlässig nach Ordner.

## Löschen

Verschiebt Dateien in den Papierkorb, nichts wird endgültig gelöscht.

## Bibliothek sichern

`Datei → Bibliothek sichern …` kopiert die Datenbank mit allen Zuordnungen
an einen selbst gewählten Ort (über SQLites Online-Backup-API, sicher auch
während die App läuft). Sie ist die einzige Quelle der Wahrheit für
Zuordnungen; ohne Sicherung wäre ein Datenverlust nicht rückgängig zu
machen.

## Bedienung

| Kürzel | Aktion |
|---|---|
| `F5` | Scannen |
| `Strg+T` | Automatisch zuordnen |
| `Enter` | Lesen |
| `Strg+R` | Umbenennen … |
| `Strg+S` | Metadaten in Datei speichern … |
| `Strg+F` | Suchen |
| `Entf` | Löschen … |
| `Strg+,` | Einstellungen … |
| `F1` | Hilfe … |
| `Strg+Q` | Beenden |

## Wo Daten liegen

| Was | Wo |
|---|---|
| Einstellungen | `~/.config/bookdesk/bookdesk.conf` |
| Bibliotheksindex (Zuordnungen, Lesefortschritt) | `~/.local/share/bookdesk/library.sqlite` |
| Antwort-Cache, Cover | `~/.cache/bookdesk/` |

## Aufbau

- `bookdesk/formats/` — `epub.py` (ebooklib zum Lesen, direktes
  OPF-Patchen zum Schreiben, DRM-Erkennung), `pdf.py` (PyMuPDF: Metadaten,
  Cover, Seitenbilder, Textsuche), `base.py` (gemeinsame Schnittstelle)
- `bookdesk/scanner.py` — Ordner einlesen (voller Scan und gezielter Scan
  eines einzelnen Buchs), beides abbrechbar
- `bookdesk/library.py` — SQLite-Bibliotheksindex, Gruppierung nach Serie
  (case-insensitiv)
- `bookdesk/matcher.py` — Kandidaten sammeln und bewerten (Titel- und
  Autor-Ähnlichkeit)
- `bookdesk/providers/openlibrary.py` — OpenLibrary-Anbindung
- `bookdesk/reader.py` — Lesefenster (Zoom, Suche)
- `bookdesk/renamer.py`/`renamedialog.py` — Vorlagen-Umbenennung
- `bookdesk/mainwindow.py` — Hauptfenster, Kachelansicht
- `bookdesk/config.py` — Einstellungen (QSettings)
- `bookdesk/i18n.py` — Übersetzungstabelle

## Entwickeln

```bash
.venv/bin/pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen .venv/bin/pytest
```

Die Tests erzeugen echte EPUB-/PDF-Testdateien über
[ebooklib](https://github.com/aerkalov/ebooklib) und
[PyMuPDF](https://pymupdf.readthedocs.io/) statt zu mocken — inklusive
eines simulierten DRM-Archivs für die Erkennungstests.

Windows-Installer und macOS-Pakete entstehen per PyInstaller + Inno Setup
in CI, ausgelöst von einem Tag wie `v0.2.0` — siehe
[packaging/README.md](packaging/README.md).

## Bekannte Grenzen

- Windows/macOS sind reines Qt/Python und sollten funktionieren, wurden
  aber nicht manuell auf diesen Plattformen getestet.
- DRM-geschützte EPUBs werden erkannt und klar markiert, lassen sich aber
  naturgemäß nicht lesen oder umbenennen.
- Reader ohne Lesezeichen, Notizen oder Manga-Leserichtung.
- Kein Drag & Drop aus anderen Dateimanagern.

## Lizenz

[MIT](LICENSE). Verwendet [PySide6](https://doc.qt.io/qtforpython/) (LGPL),
[ebooklib](https://github.com/aerkalov/ebooklib) (AGPL),
[PyMuPDF](https://pymupdf.readthedocs.io/) (AGPL/kommerziell) und
[Send2Trash](https://github.com/arsenetar/send2trash) (BSD). Metadaten
stammen von [OpenLibrary](https://openlibrary.org) (Daten CC0).
