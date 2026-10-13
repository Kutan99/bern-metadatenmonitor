# Bern – unabhängige Metadatenmonitore

Dieses öffentliche Projekt beobachtet Änderungen an **öffentlich zugänglichen Metadaten** aus zwei getrennten Schweizer Katalogen. Es ist **kein offizielles Angebot des Kantons Bern oder des Bundesamts für Statistik (BFS)**. Es gibt **keinen direkten Abgleich zwischen I14Y und opendata.swiss**: Jeder Monitor vergleicht nur die eigenen Tagesstände.

## Dashboard

Die GitHub-Pages-Seite unter `https://Kutan99.github.io/i14y-bern-monitor/` bietet zwei Schaltflächen:

- **I14Y Monitor** (`docs/i14y.html`): öffentliche Metadatensätze mit Herausgeber `CH_KT_BERN`.
- **opendata.swiss Monitor** (`docs/opendata.html`): Metadatensätze der Organisation `kanton-bern-2`.

Jeder Bereich enthält einen **Zeitraumvergleich** zweier archivierter Tage, die Status **Neu / Entfernt / Verändert**, einen **Vorher-Nachher-Feldvergleich**, Suche und Filter, einen **Verlauf**, JSON-/CSV-Export sowie einen **getrennten Demo-Modus** mit erfundenen Beispieldaten. Der Demo-Modus schreibt keine Archivdateien. Der CSV-Export von Änderungen ist ohne Änderungen deaktiviert; der JSON-Vergleich wird nach einer erfolgreichen Gegenüberstellung angeboten.

Der Vergleich bewertet die gespeicherten Metadaten zwischen dem gewählten älteren und neueren Tag, **nicht** alle Zwischenereignisse oder die Inhalte extern verlinkter Dateien. »Entfernt« heisst nur, dass ein Datensatz im neueren Abruf nicht mehr gefunden wurde; das ist kein Beleg für eine tatsächliche Löschung.

## Automatische tägliche Prüfung

Der Workflow `.github/workflows/i14y-monitor.yml` kann über **Actions → Bern – täglicher Metadatenmonitor → Run workflow** manuell gestartet werden. Er ist täglich für **06:15 Uhr Europe/Zurich** geplant (gemäss Workflow-Datei; geplante Läufe können von GitHub verspätet oder vereinzelt gar nicht ausgeführt werden).

1. GitHub Actions lädt das Repository und richtet Python **auf einem GitHub-Runner** ein.
2. `python monitor.py` prüft den I14Y-Katalog.
3. `python opendata_monitor.py` prüft den opendata.swiss-Katalog.
4. Bei Erfolg werden neue beziehungsweise aktualisierte JSON-Stände und Webarchivdateien mit einem Commit unter `data/` und `docs/` gespeichert. Dafür benötigt der Workflow `contents: write` und die erforderlichen Repository-Schreibrechte.

**Wichtig:** Ein grüner GitHub-Workflow bestätigt nur die erfolgreiche Ausführung, nicht automatisch die inhaltliche Vollständigkeit. Bei Fehlern die Logs unter **Actions** prüfen. Die beiden Quellen werden im vorhandenen Workflow nacheinander ausgeführt; fällt eine Abfrage aus, kann der gesamte Lauf fehlschlagen und der Commit ausbleiben.

## Ablage und Dateien

| Pfad | Aufgabe |
|---|---|
| `docs/index.html` | Startseite und Umschaltung zwischen beiden Monitoren |
| `docs/i14y.html` | Browser-Oberfläche für I14Y |
| `docs/opendata.html` | Browser-Oberfläche für opendata.swiss |
| `monitor.py` | Abruf, Tagesstand und Bericht für I14Y |
| `opendata_monitor.py` | Abruf, Tagesstand und Bericht für opendata.swiss |
| `.github/workflows/i14y-monitor.yml` | Zeitplan und automatische Ausführung |
| `data/snapshots/YYYY-MM-DD.json` | I14Y-Tagesstände |
| `data/reports/YYYY-MM-DD.json` | I14Y-Tagesberichte |
| `docs/snapshots/YYYY-MM-DD.json` | Öffentlich verfügbare I14Y-Tagesstände für das Dashboard |
| `docs/index.json` | I14Y-Archivindex |
| `data/opendata/snapshots/YYYY-MM-DD.json` | opendata.swiss-Tagesstände |
| `data/opendata/reports/YYYY-MM-DD.json` | opendata.swiss-Tagesberichte |
| `docs/opendata/snapshots/YYYY-MM-DD.json` | Öffentlich verfügbare opendata.swiss-Tagesstände |
| `docs/opendata/index.json` | opendata.swiss-Archivindex |

Ein Tagesstand wird mit dem jeweiligen Datum benannt; ein erneuter Lauf am selben Datum kann den Tagesstand dieses Datums aktualisieren. Ein echter Zeitraumvergleich benötigt zwei verschiedene gespeicherte Tage. Die ursprünglichen API-Quellen können ihre Daten zwischen Abrufen verändern, ohne dass das rückwirkend sichtbar wird.

## Einrichtung / Betrieb

1. Öffentliches GitHub-Repository mit den genannten Dateien und Ordnern auf Branch `main` verwenden.
2. Unter **Settings → Actions → General** ausreichende Workflow-Schreibberechtigungen sicherstellen, falls die Repository-Einstellungen dies verlangen.
3. Unter **Settings → Pages** die Veröffentlichung mit **Deploy from a branch**, Branch `main`, Ordner `/docs` aktivieren.
4. Workflow unter **Actions** einmal manuell starten und **beide** Prüfungen im Log kontrollieren.
5. Dashboard öffnen und prüfen, ob in beiden Bereichen die archivierten Tage angeboten werden. Bei Browser-Cache-Problemen Seite mit `Strg + F5` aktualisieren.

Die Webseite funktioniert ohne lokale Python-Installation. Die automatische Ausführung hängt von GitHub Actions ab, nicht davon, ob ein Browser geöffnet ist.

## Quellen, API-Regeln und Nutzungsbedingungen

**I14Y:** [Katalogauswahl Kanton Bern](https://www.i14y.admin.ch/de/catalog/datasets?publisher=CH_KT_BERN) und [offizielle I14Y-Public-API-Dokumentation mit Fair-Use-Richtlinien](https://handbook.i14y.admin.ch/de/metadaten_abrufen/api/). Die Public API stellt öffentliche Metadaten ohne Anmeldung bereit. Die dokumentierten Fair-Use-Vorgaben betreffen den API-Zugriff; sie sind **keine einheitliche Lizenz für alle beschriebenen Datensätze oder deren Metadaten**. Datensatzbezogene Rechte und Quellenpflichten sind gesondert zu beachten.

**opendata.swiss:** [Katalogauswahl Kanton Bern](https://opendata.swiss/de/organization/kanton-bern-2?organization=kanton-bern-2), [Nutzungsbedingungen](https://opendata.swiss/de/terms-of-use) und [API-Dokumentation](https://handbook.opendata.swiss/de/content/nutzen/api-nutzen.html). Die datensatzbezogenen Bedingungen können je nach Ressource Quellenangaben oder weitere Voraussetzungen verlangen.

**Weiterverwendung:** Es werden öffentlich zugängliche **Metadaten** archiviert, nicht die Originaldateien der beschriebenen Datensätze. Dennoch sind die vollständigen Tagesstände im öffentlichen Repository und teils auch über GitHub Pages einsehbar. Allgemeine Quellenhinweise ersetzen keine individuell vorgeschriebenen Quellenangaben. Der Softwarecode und die fremden Metadaten haben nicht automatisch dieselben Nutzungsrechte.

## Hinweise zum Datenschutz und zur Wartung

- Keine Geheimnisse, API-Tokens oder internen Informationen in diesem öffentlichen Repository speichern.
- Archiv-JSON-Dateien können Kontaktangaben enthalten, die von den öffentlichen Katalogen bereitgestellt wurden; vor einer Weiterverwendung die geltenden rechtlichen Vorgaben beachten.
- Das Archiv wächst täglich. Repository-Grösse, GitHub-Grenzen sowie API-Fair-Use regelmässig überprüfen.
- Ändern die Kataloge ihre API oder ihr Metadatenschema, müssen die Skripte beziehungsweise die Vergleichsdarstellung überprüft werden.

## Haftungs- und Unabhängigkeitshinweis

Dies ist eine unabhängige Auswertung öffentlich abrufbarer Katalogmetadaten, **kein offizielles Produkt des Kantons Bern oder des BFS**. Die Anzeige kann aufgrund von API-Fehlern, fehlenden Prüftagen, Änderungen der Herausgeberzuordnung oder Katalogaktualisierungen unvollständig sein. Für die Richtigkeit der ursprünglichen Metadaten sind die jeweils aufgeführten Herausgeber verantwortlich.
