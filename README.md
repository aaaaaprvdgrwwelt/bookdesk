# BookDesk

Ein Dateimanager, der nur Ebooks kennt: sichten, lesen, Metadaten holen,
umbenennen, löschen. Python + Qt (PySide6), auf demselben
[deskkit](https://github.com/aaaaaprvdgrwwelt/deskkit)-Fundament wie
[MovieDesk](https://github.com/aaaaaprvdgrwwelt/moviedesk) und
[ComicDesk](https://github.com/aaaaaprvdgrwwelt/comicdesk).

Unterstützte Formate: EPUB (Kapitel-Reader) und PDF (Seiten-Reader).
Metadaten kommen zuerst aus der Datei selbst, ergänzt durch einen
optionalen Abgleich gegen [OpenLibrary](https://openlibrary.org) (kostenlos,
kein API-Key nötig).

> Status: in aktiver Entwicklung, jung.

## Aus dem Quelltext starten

```bash
git clone https://github.com/aaaaaprvdgrwwelt/bookdesk.git
git clone https://github.com/aaaaaprvdgrwwelt/deskkit.git
cd bookdesk
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./bookdesk.sh
```

`deskkit` muss dafür als Geschwister-Ordner neben `bookdesk/` liegen (siehe
`requirements.txt`, `-e ../deskkit`).

## Bedienung

Siehe den Hilfe-Dialog in der App (`F1`) für Ersteinrichtung, API-Keys und
Tastenkürzel.
