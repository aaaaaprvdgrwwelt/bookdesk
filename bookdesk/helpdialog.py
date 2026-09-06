"""Hilfe: was bookdesk kann und wie der Online-Abgleich funktioniert."""
from __future__ import annotations

from deskkit.helpdialog import HelpDialog as _HelpDialog

from .i18n import _

HELP_HTML = """
<h2>Erste Schritte</h2>
<ol>
<li>Ueber <b>Ordner hinzufuegen</b> einen Ebook-Ordner angeben.</li>
<li><b>Scannen</b> liest den Ordner ein - Titel/Autor/Serie/Cover kommen
    dabei zuerst aus der Datei selbst (EPUB-Metadaten bzw. PDF-Dokument-
    eigenschaften).</li>
<li><b>Automatisch zuordnen</b> ergaenzt fehlende Angaben und ein Cover
    ueber <a href="https://openlibrary.org">OpenLibrary</a> - kostenlos,
    kein API-Key noetig. Unsichere oder fehlgeschlagene Treffer bleiben
    markiert und lassen sich per Rechtsklick &rarr; <i>Manuell zuordnen</i>
    von Hand nachtragen.</li>
<li>Doppelklick oder <b>Lesen</b> oeffnet den Reader - EPUB kapitelweise,
    PDF seitenweise. Die zuletzt gelesene Stelle wird gemerkt.</li>
</ol>

<h2>Was OpenLibrary liefert</h2>
<p>Titel, Autor(en), Beschreibung und ein Cover, gesucht ueber Titel und
Autor aus den vorhandenen Metadaten bzw. dem Dateinamen. Die Metadaten
werden nicht in die Ebook-Datei zurueckgeschrieben - sie dienen nur der
Anzeige und dem Umbenennen.</p>

<h2>Unterstuetzte Formate</h2>
<p><b>EPUB</b>: Kapitelweiser Reader, Metadaten aus der eingebetteten OPF-
Datei (inkl. Calibre-Serieninformation, falls vorhanden).</p>
<p><b>PDF</b>: Seitenweiser Reader, Metadaten aus den PDF-Dokument-
eigenschaften (Titel/Autor, falls gesetzt) - PDFs haben in der Regel keine
Serieninformation.</p>

<h2>Im Reader: Zoom und Suche</h2>
<p><b>Zoom</b> - <code>Strg++</code>/<code>Strg+-</code>/<code>Strg+0</code>
(oder die A+/A-/100&nbsp;%-Knoepfe). Bei EPUB aendert das die
Schriftgroesse, bei PDF die Renderaufloesung (50-250&nbsp;%).</p>
<p><b>Suche</b> - Eingabe im Suchfeld + <code>Enter</code>/&#9664;/&#9654;.
Bei EPUB wird zunaechst im aktuellen Kapitel gesucht, ohne Treffer der
Reihe nach durch die uebrigen Kapitel (mit Umlauf am Buchanfang/-ende).
Bei PDF laeuft die Suche ueber PyMuPDFs eigene Textsuche und springt zur
naechsten/vorherigen Seite mit Treffer - ohne Textmarkierung auf der Seite
selbst, nur der Sprung zur Fundstelle.</p>

<h2>DRM-geschuetzte EPUBs</h2>
<p>EPUBs mit Adobe-ADEPT- oder LCP-Verschluesselung lassen sich nicht
lesen. bookdesk erkennt das am <code>META-INF/encryption.xml</code>-Eintrag
im Archiv und markiert die Datei beim Scannen als <b>Fehler</b> mit dem
Hinweis "DRM-geschuetzt", statt sie mit leerem oder geratenem Titel
unauffaellig in der Bibliothek zu fuehren.</p>

<h2>Umbenennen-Vorlage</h2>
<p>Unter <b>Einstellungen &rarr; Umbenennen</b> frei einstellbar. Platzhalter:
<code>{author} {series} {series_index} {title} {year} {ext}</code>. Ein
<code>/</code> in der Vorlage legt eine neue Ordnerebene an.</p>

<h2>Loeschen</h2>
<p>Verschiebt Dateien in den Papierkorb, nichts wird endgueltig geloescht.</p>

<h2>Bibliothek sichern</h2>
<p><b>Datei &rarr; Bibliothek sichern …</b> kopiert die Datenbank mit allen
Zuordnungen an einen selbst gewaehlten Ort - sie ist die einzige Quelle der
Wahrheit dafuer, ein Datenverlust liesse sich sonst nicht rueckgaengig
machen. Die Sicherung laesst sich bei Bedarf einfach zurueckkopieren (App
vorher schliessen) - dafuer gibt es keinen eigenen Knopf.</p>

<h2>Wo Daten liegen</h2>
<table cellpadding="4">
<tr><td>Einstellungen</td><td><code>~/.config/bookdesk/bookdesk.conf</code></td></tr>
<tr><td>Bibliotheksindex (Zuordnungen, Lesefortschritt)</td>
    <td><code>~/.local/share/bookdesk/library.sqlite</code></td></tr>
<tr><td>Antwort-Cache, Cover</td><td><code>~/.cache/bookdesk/</code></td></tr>
</table>
"""


class HelpDialog(_HelpDialog):
    def __init__(self, parent=None):
        super().__init__(HELP_HTML, _("Hilfe"), parent)
