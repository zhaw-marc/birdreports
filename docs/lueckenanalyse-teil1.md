# Lückenanalyse Teil 1 (Stand 18.10.2026)

Abgleich der Konzeption und des Repository-Stands mit den Vorlesungsfolien (Einführung,
Architekturen, Generierung/Beschaffung, Storage), dem Organisatorischen und dem
Bewertungsraster `DAENG_LNW1_2_Bewertungsraster_Projekte_2026.xlsx`.

Abgabe: 27.10.2026, 23:59 Uhr (Abgabe-Branch auf GitHub). Kolloquium: 28.10.2026, 18:00, SW 111.
Verbleibend: 9 Tage.

> **Stand 18.10.2026, nachgeführt:** Die Schritte 4, 6 und 7 der Liste am Ende sind umgesetzt —
> `requirements.txt` enthält scipy und statsmodels, `src/build_analysis_table.py` schreibt die
> bereinigten Tabellen und die Analysetabelle, `src/hypothesis_tests.py` testet H1 bis H3 inklusive
> Holm-Korrektur, Konfidenzintervallen und Moran's I. Ergebnisse siehe README. Die übrigen
> Blocker (Git-Abgabe, Notebook, Präsentation, Download-Skript) stehen unverändert offen.

## Wie bewertet wird

Das Raster vergibt für Teil 1 **fünf Blöcke × neun Kriterien**, je 0–4 Punkte:

| Block | Kriterien |
|---|---|
| Konzeptionalisierung | Kohärenz, Vollständigkeit, Skalierbarkeit, Fachlichkeit, Funktionalität, Objektivität, Originalität, Signifikanz, Eigenständigkeit |
| Entwurf DE-Lebenszyklus | dieselben neun |
| Ingestion | dieselben neun |
| Storage | dieselben neun |
| Transformation Teil 1 | dieselben neun |

Daraus folgen drei Dinge, die in der Konzeption noch nicht berücksichtigt sind:

1. **Jeder Block wird auf alle neun Kriterien bewertet**, auch die konzeptionellen Blöcke auf
   *Funktionalität* und *Skalierbarkeit*, und die technischen Blöcke auf *Objektivität* und
   *Originalität*. Jeder Block braucht also sowohl eine Begründung als auch ein Artefakt.
2. **Eigenständigkeit** heisst im Organisatorischen ausdrücklich: Verweis auf externe Quellen
   (Literatur **und Code-Vorlagen**) per Kommentar im Notebook bzw. in der `.py`-Datei nach dem
   ZHAW-Zitierleitfaden. Derzeit enthält kein Skript einen solchen Verweis.
3. Es gibt **keine Gewichtung nach Aufwand**: Storage (ein Benchmark-Skript) zählt genauso viel
   wie Transformation Teil 1. Die fünf Blöcke sollten gleich tief ausgearbeitet sein.

## Blocker (ohne diese Punkte ist die Abgabe unvollständig)

### 1. Nichts ist committet, es gibt keinen Abgabe-Branch

`git log` auf `main` ist leer, alle Dateien sind untracked. Abgegeben wird laut
Organisatorischem über einen **Abgabe-Branch** auf GitHub. Das ist der grösste Einzelrisikopunkt
und in 20 Minuten behoben: Repo auf GitHub (ZHAW-Mail im Account), `main` committen,
Branch `abgabe` anlegen, alle drei Gruppenmitglieder als Collaborators.

### 2. «Daten» sind Teil des Lieferumfangs, liegen aber vollständig in `.gitignore`

Gefordert sind «kommentierter Code, **die Daten** und die Präsentationsdateien». `.gitignore`
schliesst `data/`, `profile_out/` und `storage_test_out/` aus. Damit landet derzeit kein einziges
Datenartefakt in der Abgabe.

Die Rohdaten gehören wegen der 100-MB-Grenze tatsächlich nicht ins Repo, die Ergebnisse aber
schon, und die sind klein:

- Analysetabelle pro Quadrat (ca. 1'800 Zeilen × ~12 Spalten) — wenige hundert KB
- `profile_out/profile.json` und `storage_test_out/storage_test.json` — Messbelege
- `storage_test_out/plattform.parquet` (26,5 MB) und `test.duckdb` (46,9 MB) — unter 100 MB, also
  committebar; empfehlenswert ist mindestens die DuckDB-Analysedatenbank, weil das Raster unter
  «Artefakte (Codes, **Datenbanken**)» explizit Datenbanken nennt.

Konkret: `.gitignore` auf `data/` beschränken, Ergebnisordner wieder aufnehmen.

### 3. Das Download-Skript existiert nicht

Die Konzeption verspricht «Download-Skript mit Datum und DOI im Log, Search-API als Fallback»,
und der offene Punkt 1 stützt die Abgabe der Daten gerade darauf, dass dieses Skript die Rohdaten
reproduzierbar lädt. Im Repo liegt nur eine Prosa-Anleitung im README. Ohne das Skript fehlt dem
Ingestion-Block sein Artefakt — und damit Punkte bei *Funktionalität* in einem Block, der
konzeptionell schon gut dasteht.

### 4. Hypothesentests fehlen vollständig

Das Raster und das Organisatorische verlangen für Transformation Teil 1 ausdrücklich
«Initiale Analyse der Datengrundlage, **Hypothesentest**», «Initiale Datenbereinigung» und
«Beantwortung der Forschungsfragen». Vorhanden ist nur `profile_data.py` (Profiling, verändert
nichts). Es fehlen: Spearman für H1/H2, multiple Regression mit Aufwand als Kontrolle,
Interaktionsterm für H3, Holm-Korrektur, Konfidenzintervalle, Moran's I.

`requirements.txt` enthält weder `scipy` noch `statsmodels` — die geplante Statistik ist technisch
derzeit nicht ausführbar. Das ist der grösste inhaltliche Brocken der verbleibenden 9 Tage.

### 5. Kein Notebook, keine Präsentation

Die Konzeption nennt «Jupyter-Notebook und Präsentation» als Serving-Artefakt; das Organisatorische
verlangt Präsentationsdateien in der Abgabe und drei eigenständige Vorträge à ca. 5 Minuten.
Beides existiert nicht. Die Zitierpflicht (Eigenständigkeit) hängt am Notebook.

## Inhaltliche Lücken je Block

### Konzeptionalisierung — solide, zwei Kriterien unbelegt

Problemstellung, Forschungsfragen, Hypothesen, Methoden und Limitationen sind überdurchschnittlich
ausgearbeitet; Null-Ergebnisse als zulässig zu benennen und Effektstärken statt reiner p-Werte zu
fordern, zahlt direkt auf *Objektivität* ein.

Offen sind die zwei Kriterien, die man einer Konzeption nicht ansieht:

- **Skalierbarkeit:** Was passiert bei 10× Datenvolumen (eBird wächst von 49'000 auf 401'000
  Meldungen pro Jahr — die Zahl steht schon im Text und trägt das Argument), bei einem zweiten
  Land, bei einem 1-km-Raster? Ein Absatz genügt, aber er muss da sein.
- **Funktionalität:** Die Konzeption sollte auf die lauffähigen Artefakte verweisen (welches Skript
  belegt welche Setzung).

Zwei Punkte sind sachlich zu schärfen:

- Der **Begriff «Abdeckungsquote»** ist für Quadrate definiert, die Hypothesen operieren aber auf
  dem Quadrat *und* der Zahl der Referenzpaare. `profile_data.py` berichtet beides
  (Paaranteil: eBird 34,0 %, iNaturalist 5,2 %, Observation.org 4,4 %, alle drei 36,2 % bei 127'269
  Referenzpaaren). Die Konzeption sollte sagen, welche der beiden Grössen die abhängige Variable der
  Regression ist — das ist nicht dasselbe, weil artenreiche Quadrate sonst implizit höher gewichtet
  werden.
- Die **Klärung mit Frau Rothstein** zum FS26-Themenbereich (offener Punkt) ist 9 Tage vor Abgabe
  noch offen und betrifft die Zulässigkeit der Arbeit. Das ist eine Mail, nicht eine Diskussion —
  heute senden.

### Entwurf des DE-Lebenszyklus — Phasen vollständig, Vokabular der Vorlesung fehlt

Die fünf Phasen und alle sechs Unterströmungen sind benannt und passen zur Folie «Der Data
Engineering Lifecycle». Was fehlt, ist der Bezug auf die Architektur-Vorlesung, obwohl der Entwurf
die Architektur als Unterströmung führt. Mit geringem Aufwand holbar:

- **ELT statt ETL** benennen: Rohdaten unverändert laden, Transformation in DuckDB — das ist
  genau das ELT-Muster der Folien, und die Begründung (Zielsystem ist leistungsfähig genug) steht
  implizit schon im Storage-Abschnitt.
- **Drei Schichten** als Architekturmuster einordnen (Rohdaten/bereinigt/Analyse ≈ Multi-tier,
  Single-Node) statt nur aufzuzählen.
- **Zweiweg-Tür:** Der DuckDB-Entscheid ist reversibel (Parquet bleibt die Quelle der Wahrheit).
  Das ist die Sprache der Folie «Einweg- und Zweiwegtüren» und belegt *Fachlichkeit*.
- **Trade-off-Profil** (Folie «Architektur-Trade-off-Profil»): «Wir priorisieren X, akzeptieren
  dafür Y, begrenzen das Risiko durch Z» — für dieses Projekt etwa Durchsatz/Effizienz statt
  Latenz, Integriert/Single-Node statt verteilt, Self-managed statt Managed. Drei Regler mit je
  einem Satz.
- **Orchestration:** Das Makefile ist als Vorschlag genannt, existiert aber nicht. Es sind fünf
  Zeilen und macht die Unterströmung vom Versprechen zum Artefakt.

### Ingestion — Quellen gut dokumentiert, Quellsystem-Analyse fehlt

Die fünf Quellen sind mit Volumen, Lizenz, Genauigkeit und DOI dokumentiert — das ist mehr, als
der Block verlangt, und die Stichprobenprüfung des Rasters (15 Datensätze, überall 2'500 modulo
5'000) ist eine echte eigene Prüfung.

Nicht abgedeckt ist, was die Vorlesung «Generierung und Beschaffung» als Kern behandelt:

- **Evaluation der Quellsysteme** nach der Fragenliste von Reis & Housley (Kapitel 5, zwei Folien
  mit je ~10 Fragen): Aufbewahrung, Erzeugungsgeschwindigkeit, Konsistenz, Duplikate,
  Schemaänderungen, Abrufhäufigkeit, vorgelagerte Abhängigkeiten, Qualitätskontrollen. Für GBIF
  sind die Antworten alle bekannt — eine Tabelle Quelle × Frage ist die naheliegende Form.
- **Eigenschaften der Daten** im Vokabular der Folien: GBIF-Export = strukturiert (tabellarisch,
  Tab-getrennt); Darwin-Core-Archiv = semistrukturiert (`occurrence.txt` + `meta.xml` + `eml.xml`);
  Variablentypen der Zielgrössen (Abdeckungsquote stetig, Plattform nominal, letztes Brutjahr
  diskret, Landnutzungsanteile stetig). Das ist auch Prüfungsstoff (siehe Musterlösung HS23).
- **API-Paradigma:** GBIF ist eine öffentliche **REST**-API; der Download ist ein
  **Pull**-Muster, **begrenzte Daten** (bounded, über Zeit abgegrenzt), **Batch** (einmalig pro
  Version), **synchron**. Die Payload-Merkmale (Art, Form, Grösse, Schema, Metadaten) liegen alle
  vor. Das sind fünf Folienbegriffe, die der Konzeption nichts kosten und den Block sichtbar
  verankern.
- **Änderungserfassung:** Für die Quellen existiert **kein CDC und kein Log** — darum
  versionierte Snapshots über die GBIF-DOI. Genau diese Begründung fehlt, obwohl CDC/Logs ein
  Drittel der Vorlesung ausmachen. Für die Vogelwarte-Datenbank ist der Punkt sogar inhaltlich
  relevant: «nur letztes Brutjahr pro Art und Quadrat» *ist* fehlende Historisierung, also eine
  Quelle ohne Änderungsprotokoll. Das verbindet Folienstoff und Limitation.
- **Skalierbarkeit der Ingestion:** Search-API mit Paging, Download pro Jahr statt einmalig,
  Wiederaufnahme nach Abbruch. Bisher nur als Fallback-Satz erwähnt.

### Storage — Messung vorhanden, Evaluation zu eng

`storage_test.py` ist ein echter Benchmark auf den Projektdaten, und die Ergebnistabelle im README
ist ehrlich ausgewiesen (Einzelmessung, ein Rechner). Das ist gute *Objektivität*.

Die Evaluation deckt aber nur **eine** der Dimensionen ab, die die Storage-Vorlesung lehrt
(Performance), und lässt die anderen aus:

- **Storage Abstractions / Datenmodelle:** Die Vorlesung behandelt relational, Dokument, Graph,
  Zeitreihe, Key-Value, spaltenbasiert, Vektor und **polyglotte Persistenz** mit je eigenen
  Workshops. Die Konzeption vergleicht drei relationale/OLAP-Systeme und begründet nicht, warum
  das relationale bzw. spaltenbasierte Modell passt und die anderen nicht. Das ist der sichtbarste
  Verlust an *Vollständigkeit* im ganzen Teil 1 — und für dieses Projekt leicht zu argumentieren:
  Art/Quadrat-Paare sind eine Relation, die Analyse ist eine Aggregation über Spalten, ein Graph-
  oder Zeitreihenmodell bringt hier nichts (die Referenz hat gar keinen Zeitverlauf).
- **Storage Systems:** Die Folie «Vergleich der Speichersysteme» nennt File/Block/Object/Cache und
  führt SQLite, DuckDB, Parquet ausdrücklich unter *File Storage*. Die Wahl liegt also in einer
  Zeile dieser Tabelle — das kann man zitieren statt neu zu erfinden.
- **Datenbankeigenschaften:** ACID wird nicht gebraucht (ein Schreiber, keine Transaktionen),
  **CAP ist nicht anwendbar**, weil das System nicht verteilt ist und Partitionstoleranz keine
  Rolle spielt. Beides explizit so zu sagen, ist genau die geforderte Diskussion; das Weglassen
  sieht aus wie eine Lücke.
- **5 V's:** Volume (1,5 Mio. Meldungen + 4,1 Mio. Hektaren), Velocity (Batch, keine
  Aktualisierung), Variety (vier Quellen, zwei Formate), Veracity (Validierungsgrad je Plattform —
  das ist die Fragestellung selbst), Value. Vier Zeilen, ein ganzes Folienkapitel abgedeckt.
- **PostgreSQL/PostGIS** wurde ohne Messung verworfen. Die Begründung (Server nötig, keine
  Raumfunktionen erforderlich, weil das Raster aus LV95-Koordinaten gerechnet wird) ist sachlich
  richtig und sollte stehen bleiben — aber als dokumentierte qualitative Evaluation mit
  Kriterien, nicht als Nebensatz. Ergänzen: Die Folie «Mögliche Speicherumgebungen für die
  Projektarbeit» nennt MySQL/MariaDB/SQLite, Colab, Azure, AWS. DuckDB ist dort **nicht**
  aufgeführt; es ist die bessere Wahl, aber die Abweichung von der Vorlesungsliste sollte man
  begründen, nicht übergehen.
- **Skalierbarkeit:** Ab welchem Volumen kippt der Entscheid? (Parquet + DuckDB tragen weit, die
  Grenze ist der RAM eines Rechners; der Ausweg wäre Partitionierung nach Jahr.)

### Transformation Teil 1 — Profiling stark, Bereinigung und Tests fehlen

`profile_data.py` ist das stärkste Artefakt im Repo: Es belegt jede Setzung der Konzeption mit
Zahlen (Rasterabweichung Median 0,2 m, 213 Arten, 1'684 Referenzquadrate, 169 von 1'839 Quadraten
unter 1'000 ha, Abdeckung nach letztem Brutjahr, Wirkung der Koordinatenschwelle). Die
Sensitivitätsanalysen sind teilweise schon implementiert, bevor sie gebraucht werden — das ist
*Originalität* und *Objektivität* im Rastersinn.

Lücken:

- **Keine Bereinigung, keine Analysetabelle.** Das Skript misst nur. Es fehlt der Schritt, der
  bereinigte Parquet-Tabellen und die Analysetabelle (eine Zeile pro Quadrat) schreibt — also
  genau das Artefakt, das Storage und Hypothesentests verbindet.
- **Keine Tests.** Die Konzeption verspricht «jeder Schritt als Funktion mit Test»; `pytest` ist
  nicht in `requirements.txt`, Tests existieren nicht. Drei Tests reichen, um das Versprechen zu
  halten: Quadrat-ID aus bekannten LV95-Koordinaten, Abdeckungsquote auf einem Mini-Beispiel,
  Landnutzungsanteile summieren auf 1.
- **Beobachter-IDs werden nicht gehasht.** Konzeption, README und Unterströmung «Security» sagen
  zu, `recordedBy` vor dem Speichern zu hashen. `profile_data.py` liest die Spalte im Klartext und
  gibt am Ende die Top-5-Beobachteranteile von Observation.org auf die Konsole aus
  (`oj.recordedBy.value_counts(...)`). Bei GBIF-eBird stehen dort teilweise Klarnamen. Das ist der
  einzige Punkt, bei dem das Repo der eigenen Zusage widerspricht — und er betrifft
  *Kohärenz* und die Unterströmung Security direkt. Fix: Hashen in `add_cell`-Nähe ziehen, nur
  noch Hashes und Anzahlen ausgeben.
- **Stale Docstring:** `profile_data.py` behauptet «NICHT an den echten Daten getestet», aber
  `profile_out/profile.json` enthält Ergebnisse aus einem echten Lauf. Kleinigkeit, aber ein
  Prüfender liest den Docstring zuerst.
- **Nicht implementierte Sensitivitätsanalysen:** Verteilung der 7'070-m-Meldungen auf die vier
  enthaltenen Quadrate, Variation der Brutzeitgrenzen, Mitführen der Randquadrate. Alle drei sind
  in der Konzeption versprochen.
- **Eigenständigkeit:** Kein Skript verweist auf Quellen. Mindestens nötig: Herkunft der
  Rasterformel, Herkunft der `AS_4`-Codes (Variablenbeschreibung BFS), Herkunft übernommenen
  Codes aus dem FS26-Projekt, Zitat Reis & Housley für die Lebenszyklus-Struktur.

## Vorschlag für die 9 Tage

Nach Wirkung pro Aufwand sortiert:

| # | Schritt | Aufwand | Wirkung |
|---|---|---|---|
| 1 | GitHub-Repo, Commit, Abgabe-Branch, Collaborators | 20 min | Blocker |
| 2 | Mail an Frau Rothstein (FS26-Themenbereich) | 10 min | Blocker |
| 3 | `.gitignore` korrigieren, Ergebnisartefakte versionieren | 20 min | Blocker |
| 4 | ~~`scipy`/`statsmodels` in `requirements.txt`~~ (erledigt; `pytest` folgt mit Schritt 10) | 5 min | Voraussetzung |
| 5 | Beobachter-Hashing + Docstring korrigieren | 30 min | Kohärenz/Security |
| 6 | ~~Bereinigungsschritt + Analysetabelle pro Quadrat schreiben~~ (erledigt: `src/build_analysis_table.py`) | 0,5 Tag | Blocker |
| 7 | ~~Hypothesentests H1–H3 inkl. Holm, CI, Moran's I~~ (erledigt: `src/hypothesis_tests.py`) | 1,5 Tage | Blocker |
| 8 | Notebook als Serving-Artefakt mit Zitaten | 1 Tag | Blocker |
| 9 | Download-Skript mit DOI und Datum im Log | 0,5 Tag | Ingestion-Artefakt |
| 10 | Drei Tests für die Transformationsschritte | 2–3 h | Funktionalität |
| 11 | Makefile als Orchestrierung | 30 min | Unterströmung |
| 12 | Konzeption ergänzen: Quellsystem-Evaluation, Datentypen, REST/Pull/Batch, CDC-Begründung | 0,5 Tag | Ingestion |
| 13 | Konzeption ergänzen: Datenmodell-Begründung, ACID/CAP, 5 V's, Storage-Systems-Zeile | 0,5 Tag | Storage |
| 14 | Konzeption ergänzen: ELT, Zweiweg-Tür, Trade-off-Profil, Skalierbarkeit je Block | 0,5 Tag | Lebenszyklus |
| 15 | Präsentation, drei eigenständige Teile | 1 Tag | Blocker |
| 16 | Sensitivitätsanalysen (7'070 m, Brutzeit, Randquadrate) | 0,5 Tag | Objektivität |

Die Schritte 12–14 sind reine Textarbeit an einem bereits guten Dokument und adressieren die drei
konzeptionellen Blöcke, die zusammen 27 der 45 Rasterzellen ausmachen. Die Schritte 6–8 sind der
kritische Pfad.

Die Aufgabenteilung A/B/C der Konzeption passt dazu: A nimmt 9 + 13, B nimmt 6 + 7 + 10 + 16,
C nimmt 8 + 12 + 14. Schritte 1–5 und 11 macht, wer zuerst Zeit hat.
