# Birdreports

Projektarbeit im Modul Data Engineering (HS26, ZHAW). Wir untersuchen, wie vollständig Citizen-Science-Plattformen die Brutverbreitung von Vögeln in der Schweiz abbilden, und ob sich die Lücken mit der Landnutzung erklären lassen.

## Gruppe

| Name | ZHAW-Mail |
|---|---|
| Marc Vogelmann | vogmar04@students.zhaw.ch |
| Muriele Stermcnik | stermmur@students.zhaw.ch |
| Alen Rama | ramaale1@students.zhaw.ch |

## Fragestellung

Als Referenz dient die Schweizerische Brutvogeldatenbank der Vogelwarte Sempach mit Brutnachweisen pro Art und 5×5-km-Quadrat. Für jedes Quadrat prüfen wir, ob eBird, iNaturalist und Observation.org die dort brütenden Arten im Zeitraum 2020–2024 während der Brutzeit (April bis Juli) melden. Die Abdeckungsquote eines Quadrats ist der Anteil der Arten mit Brutnachweis, die auf einer Plattform gemeldet sind. Weil die Vogelwarte pro Art und Quadrat nur das letzte Brutjahr führt, zählen in der Hauptanalyse nur Nachweise mit letztem Brutjahr ab 2020; ältere Nachweise lassen offen, ob die Art im Beobachtungszeitraum noch dort brütet. Bei iNaturalist entfallen Meldungen mit einer Koordinatenungenauigkeit über 2'500 m. Beide Setzungen werden in Sensitivitätsläufen variiert (alle Nachweise, 5'000 m).

FF1 (Landnutzung): Hängt die Abdeckungsquote eines Quadrats von seiner Landnutzung ab?

- H1: Je höher der Siedlungsanteil, desto höher die Abdeckungsquote.
- H2: Je höher der Anteil unproduktiver Fläche, desto niedriger die Abdeckungsquote.

FF2 (Plattformen): Unterscheiden sich die Plattformen im Abdeckungsmuster?

- H3: Die Abdeckungsquote von iNaturalist hängt stärker vom Siedlungsanteil ab als die von eBird.

Problemstellung, Methodik, Lebenszyklus und Limitationen sind im Notebook (`notebooks/birdreports.py`, Abschnitte 1, 2 und 9) und in der Präsentation (`docs/presentation/`) ausgeführt.

## Datenquellen

| Quelle | Inhalt | Lizenz |
|---|---|---|
| [EOD – eBird Observation Dataset](https://www.gbif.org/dataset/4fa7b334-ce0d-4e88-aaae-2e0c138d049e), [doi:10.15468/aomfnb](https://doi.org/10.15468/aomfnb) | Beobachtungen, Schweiz, Vögel, 2020–2024 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| [Observation.org, Nature data from around the World](https://www.gbif.org/dataset/8a863029-f435-446a-821e-275f4f641165), [doi:10.15468/5nilie](https://doi.org/10.15468/5nilie) | Beobachtungen mit Anzahl und Uhrzeit | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) |
| [iNaturalist Research-grade Observations](https://www.gbif.org/dataset/50c9509d-22c7-4a22-a47d-8c48425ef4a7), [doi:10.15468/ab3s5x](https://doi.org/10.15468/ab3s5x) | Foto-Belege, Medianungenauigkeit 18 m | Datensatz [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), einzelne Meldungen CC0 oder CC BY |
| [Swiss National Breeding Bird Databank](https://www.gbif.org/dataset/63f077c9-96a0-49de-b3ea-2aa565ee1098), Version 1.1, [doi:10.15468/jujcgr](https://doi.org/10.15468/jujcgr) | Letztes Brutjahr pro Art und 5×5-km-Quadrat | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Arealstatistik des BFS, «Aktueller Stand» ([Erhebung](https://www.bfs.admin.ch/bfs/de/home/statistiken/raum-umwelt/erhebungen/area.html), [Datensatz](https://opendata.swiss/de/dataset/arealstatistik-schweiz)) | Landnutzung pro Hektare, Erhebungsjahre 2013–2020 | Quellenangabe erforderlich, kommerzielle Nutzung nur mit Zustimmung |

Die Lizenzangabe für iNaturalist steht auf Datensatzebene; in unserem Auszug verteilen sich die 66'117 Meldungen auf 53'544 unter CC BY-NC 4.0, 11'133 unter CC BY 4.0 und 1'440 unter CC0 1.0. Observation.org und die nichtkommerziell lizenzierten iNaturalist-Meldungen schliessen eine spätere kommerzielle Weiterverwendung aus; für die Studienarbeit ist die Nutzung gedeckt.

### Zitation

- Wechsler, S., Volet, B. & Schmid, H. (2023). *Swiss National Breeding Bird Databank*. Version 1.1. Swiss Ornithological Institute. <https://doi.org/10.15468/jujcgr>
- GBIF.org (13. Oktober 2026). *GBIF Occurrence Download*. <https://doi.org/10.15468/dl.9qfxn7> (Download-Key `0024005-260928105237408`)
- Bundesamt für Statistik. *Arealstatistik Schweiz* (Standardnomenklatur NOAS04). <https://www.bfs.admin.ch/bfs/de/home/statistiken/raum-umwelt/erhebungen/area.html> (Abgerufen: 13.10.26)

## Daten beschaffen

Die Rohdaten liegen wegen ihrer Grösse und des GitHub-Limits von 100 MB pro Datei nicht im Repository. Sie gehören lokal nach `data/` und werden mit `src/download_data.py` bezogen:

```
python src/download_data.py
```

Das Skript lädt alle drei Quellen, entpackt die Archive und schreibt Datum, Quell-URL, DOI, HTTP-Status, Grösse und SHA-256-Prüfsumme nach `ingest_out/download_log.json`. Vorhandene Dateien bleiben unangetastet, `--force` lädt neu, `--only` beschränkt auf eine Quelle. Das Darwin-Core-Archiv der Vogelwarte ist dadurch verifizierbar: Ein erneuter Bezug ergibt dieselbe Prüfsumme wie die vorliegende Kopie.

GBIF hält erzeugte Downloads nicht unbegrenzt vor. Fällt der Download weg, bezieht `--fallback` dieselben Filter über die Search-API, aufgeteilt nach Datensatz, Jahr und Monat, weil eine einzelne Abfrage höchstens 100'000 Treffer liefert. Diese Variante ist nicht byteidentisch, da die Suche auf der GBIF-Backbone-Taxonomie beruht und der Download auf dem Catalogue of Life; der Lauf wird im Protokoll entsprechend vermerkt.

Inhaltlich beziehen sich die drei Quellen auf:

1. Plattformdaten: GBIF-Download mit den Filtern Country = Switzerland, Year 2020–2024, Scientific name = Aves, Occurrence status = Present und taxonomischer Referenz Catalogue of Life. Der Export enthält neben den drei Plattform-Datensätzen 87'741 Zeilen der Vogelwarte-Datenbank, die wegen der Jahresfilterung nur Brutjahre ab 2020 abdecken und als Referenz ungeeignet sind, sowie 94 Zeilen aus drei weiteren Datensätzen. Verwendet werden ausschliesslich die drei Dataset-Keys aus der Tabelle oben. Ablage: `data/0024005-260928105237408.csv`, trotz Endung tabulatorgetrennt.
2. Referenz: Darwin-Core-Archiv der Brutvogeldatenbank direkt von der Vogelwarte, ohne Jahresfilter. Der Bezug über GBIF mit Jahresfilter wäre ungeeignet, weil `year` dort das letzte Brutjahr bezeichnet. Ablage: `data/dwca-soi_aves-v1/` mit `occurrence.txt`, `meta.xml` und `eml.xml`. Das Archiv umfasst 135'310 Datensätze, davon 129'240 in der Schweiz.
3. Landnutzung: Arealstatistik «Aktueller Stand» als CSV, Ablage in `data/`.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Notebook

Das Notebook `notebooks/birdreports.py` bündelt Konzeption, Lebenszyklus und Ergebnisse von Teil 1. Es liest die gespeicherten Ergebnisse (`build_out/`, `analysis_out*/`, `profile_out/`, `storage_test_out/`, `ingest_out/`) und fragt die Analysedatenbank `build_out/birdreports.duckdb` per SQL ab, rechnet die Pipeline aber nicht neu und braucht die Rohdaten nicht. Die Phase Serving im engeren Sinn (Option B) folgt in Teil 2.

```
marimo edit notebooks/birdreports.py    # interaktiv
marimo run  notebooks/birdreports.py    # nur lesen
```

## Struktur

```
birdreports/
├── README.md
├── requirements.txt
├── run_all.sh                   # Orchestrierung: alle Schritte in fester Reihenfolge
├── .gitignore
├── docs/
│   └── presentation/            # Präsentation Kolloquium 1
├── notebooks/
│   └── birdreports.py           # marimo-Notebook: Konzeption, Lebenszyklus, Ergebnisse, Antworten
├── src/
│   ├── download_data.py         # Bezug der drei Rohquellen mit Protokoll
│   ├── storage_test.py          # Storage-Evaluation DuckDB gegen SQLite
│   ├── profile_data.py          # initiale Analyse der Datengrundlage (misst nur)
│   ├── build_analysis_table.py  # Bereinigung und Analysetabelle pro Quadrat
│   ├── check_outputs.py         # Datenprüfungen nach dem Muster der dbt-Tests
│   └── hypothesis_tests.py      # Hypothesentests H1 bis H3 inkl. Robustheit von H3
├── mappings/
│   └── taxon_mapping.csv        # Artnamen Vogelwarte gegen Catalogue of Life
├── ingest_out/                  # Protokoll der Downloads (Datum, URL, DOI, Prüfsumme)
├── build_out/                   # bereinigte Tabellen, Analysetabelle, Analysedatenbank, checks.json (Hauptanalyse)
├── analysis_out/                # Ergebnisse der Hypothesentests (Hauptanalyse)
├── build_out_sens_*/            # Sensitivitätsläufe: alle Nachweise, iNaturalist bis 5'000 m
├── analysis_out_sens_*/         # Testergebnisse der Sensitivitätsläufe
└── data/                        # lokal, nicht versioniert
```

## Datenfluss

Der Fluss folgt dem Data-Engineering-Lebenszyklus (Generierung, Ingestion, Storage, Transformation, Serving). Die Kästen nennen die ausführenden Skripte, die Ablagen und die wichtigsten Regeln.

```mermaid
flowchart TB
    subgraph GEN["Generierung (externe Quellen)"]
        direction LR
        G1["GBIF Occurrence Download<br/>eBird, iNaturalist, Observation.org<br/>CH, 2020-2024, Aves, CoL-Taxonomie"]
        G2["Vogelwarte Sempach<br/>Darwin-Core-Archiv<br/>Brutvogeldatenbank v1.1, ohne Jahresfilter"]
        G3["BFS Arealstatistik<br/>Aktueller Stand<br/>4'129'071 Hektarpunkte, AS_4"]
    end

    subgraph ING["Ingestion (Batch, Pull, bounded)"]
        I1["src/download_data.py<br/>Datum, URL, DOI, HTTP-Status, SHA-256"]
        I2[("data/<br/>Rohdaten, nicht versioniert")]
        I3["ingest_out/download_log.json"]
        FB["Fallback: GBIF Search-API<br/>--fallback, nicht byteidentisch"]
    end

    subgraph PROF["Transformation Teil 1: Analyse der Datengrundlage"]
        P1["src/profile_data.py<br/>misst nur, ändert nichts"]
        P2["profile_out/<br/>Kennzahlen zu Qualität, Unsicherheit, Zeitraum, Abdeckung"]
    end

    subgraph CLEAN["Transformation Teil 1: Bereinigung"]
        direction TB
        C0["src/build_analysis_table.py"]
        C1["Plattformen: CH, April bis Juli 2020-2024,<br/>iNaturalist nur bis 2500 m Ungenauigkeit,<br/>Koordinaten LV95, Beobachter gehasht"]
        C2["Referenz: nur CH, 10-km-Meldungen markiert,<br/>Hauptanalyse nur Nachweise ab 2020,<br/>Artnamen über mappings/taxon_mapping.csv"]
        C3["Landnutzung: Hektaren und Anteile<br/>der 4 Klassen pro 5-km-Quadrat"]
        C4["Analysetabelle: Abdeckungsquote pro Quadrat<br/>Hauptanalyse: Quadrate ab 1'000 ha<br/>und mit mindestens einem Brutnachweis"]
        C5["src/check_outputs.py<br/>Datenprüfungen, Abbruch bei Fehler"]
        C0 --> C1 & C2 & C3
        C1 & C2 & C3 --> C4
        C4 --> C5
    end

    subgraph STO["Storage"]
        S1[("build_out/*.parquet<br/>platform_clean, reference_clean, landuse_cells")]
        S2[("build_out/birdreports.duckdb<br/>Analysedatenbank")]
        S3["build_out/analysis_cells.csv und .parquet<br/>build_log.json"]
        ST["src/storage_test.py<br/>Evaluation DuckDB gegen SQLite"]
    end

    subgraph SRV["Transformation Teil 1: Hypothesentests und Darstellung"]
        direction TB
        H0["src/hypothesis_tests.py"]
        H1["H1: Spearman Siedlung<br/>H2: Spearman unproduktiv<br/>H3: Interaktion Plattform x Siedlung"]
        H2["Kontrolle Aufwand, Holm-Korrektur,<br/>Moran's I der Residuen,<br/>Robustheit H3 je Spezifikation"]
        H3["analysis_out/<br/>Ergebnisse der Tests"]
        H4["Beantwortung FF1 und FF2<br/>Notebook mit SQL auf DuckDB, Präsentation"]
        H0 --> H1 --> H2 --> H3 --> H4
    end

    subgraph SEN["Sensitivitätsläufe (eigene Ausgabeordner)"]
        direction TB
        V1["alle Brutnachweise<br/>build_out_sens_all_years"]
        V2["iNaturalist bis 5000 m<br/>build_out_sens_5000m"]
    end

    G1 & G2 & G3 --> I1
    I1 --> I2
    I1 --> I3
    FB -.-> I2
    I2 --> P1 --> P2
    P2 -. "Entscheide: Referenz ab 2020,<br/>iNaturalist bis 2500 m" .-> C0
    I2 --> C0
    C4 --> S1
    C4 --> S2
    C4 --> S3
    I2 -.-> V1 & V2
    V1 & V2 -.-> H0
    S3 --> H0
    S2 -.-> ST
    S2 --> H4

    subgraph UC["Undercurrents (querliegend)"]
        direction LR
        U1["Data Management: taxon_mapping.csv, Lizenzen, Zitation"]
        U2["Security: Beobachter-Hash mit festem Salt"]
        U3["DataOps: Protokolle, Prüfsummen, Datenprüfungen, requirements.txt"]
        U4["Orchestration: run_all.sh"]
    end
```

## Pipeline

`run_all.sh` führt alle Schritte in fester Reihenfolge aus und bricht beim ersten Fehler ab, auch wenn eine Datenprüfung fehlschlägt:

```
./run_all.sh                  # Download, Profiling, Bereinigung, Prüfungen, Tests, Sensitivitätsläufe
./run_all.sh --analysis-only  # nur Prüfungen und Hypothesentests auf den vorhandenen Tabellen
./run_all.sh --storage        # zusätzlich die Storage-Evaluation (rund 320 MB Testdateien)
```

Einzeln entspricht das diesen Aufrufen:

```
python src/download_data.py
python src/profile_data.py         data/ag-b-00/ag-b-00.03-37-area-current-csv.csv data/0024005-260928105237408.csv data/dwca-soi_aves-v1/occurrence.txt mappings/taxon_mapping.csv
python src/build_analysis_table.py data/ag-b-00/ag-b-00.03-37-area-current-csv.csv data/0024005-260928105237408.csv data/dwca-soi_aves-v1/occurrence.txt mappings/taxon_mapping.csv
python src/check_outputs.py        build_out
python src/hypothesis_tests.py     build_out/analysis_cells.parquet
```

Die Hauptanalyse verwendet Nachweise ab 2020 (`--min-breeding-year 2020`) und iNaturalist-Meldungen bis 2'500 m Ungenauigkeit (`--max-uncertainty 2500`); beides sind die Standardwerte. Die beiden Sensitivitätsläufe schreiben in eigene Ordner (`build_out_sens_all_years` mit `--min-breeding-year 0`, `build_out_sens_5000m` mit `--max-uncertainty 5000`) und lassen die Hauptanalyse unberührt.

`build_analysis_table.py` bereinigt die drei Quellen nach den Regeln der Konzeption und schreibt nach `build_out/`:

| Datei | Inhalt |
|---|---|
| `platform_clean.parquet` | 603'123 Meldungen (drei Plattformen, CH, 2020–2024, April–Juli, iNaturalist bis 2'500 m, Beobachter gehasht) |
| `reference_clean.parquet` | 129'240 Art/Quadrat-Paare der Vogelwarte, 213 Arten, 10-km-Meldungen markiert; die Hauptanalyse nutzt davon 86'530 (letztes Brutjahr ab 2020, ohne 10-km-Meldungen) |
| `landuse_cells.parquet` | 1'839 Quadrate mit Hektaren und Anteilen der vier AS_4-Klassen |
| `analysis_cells.csv/.parquet` | Analysetabelle, eine Zeile pro Quadrat (1'839, davon 1'614 in der Hauptanalyse) |
| `birdreports.duckdb` | Analysedatenbank mit allen vier Tabellen (18,9 MB) |
| `build_log.json` | Parameter, Eingabepfade und Zeilenzahlen des Laufs |

Die Beobachterkennung wird mit einem festen Salt gehasht (BLAKE2s, 8 Byte), bevor irgendetwas geschrieben wird; `recordedBy` verlässt das Skript nicht im Klartext.

### Datenprüfungen

`src/check_outputs.py` prüft die Tabellen nach jeder Bereinigung, bevor die Hypothesentests laufen. Die Prüfungen folgen den vier Arten der dbt-Datentests (unique, not_null, accepted_values, relationships) und stehen je für eine Regel, deren Verletzung eine falsche, aber plausibel aussehende Zahl ergäbe:

- Art/Quadrat-Paare der Referenz und Quadrate sind eindeutig
- Plattform, Jahr, Brutmonat und iNaturalist-Ungenauigkeit liegen in den erlaubten Werten, `recordedBy` ist entfernt
- Landnutzungsanteile summieren sich auf 1, kein Quadrat hat mehr als 2'500 ha
- Abdeckungsquoten liegen zwischen 0 und 1, Treffer übersteigen die Referenzarten nie
- Referenzarten und Treffer der Analysetabelle lassen sich aus den bereinigten Tabellen nachzählen

Das Ergebnis steht in `build_out/checks.json`; bei einer verletzten Regel endet das Skript mit Exit-Code 1.

Bezeichner und Spaltennamen sind im gesamten Repository englisch, Kommentare, Docstrings und Konsolenausgaben deutsch. Die vier Landnutzungsklassen heissen `settlement`, `agriculture`, `wooded` und `unproductive` (AS_4 = 1 bis 4), die Abdeckungsquoten `coverage_<plattform>` und `coverage_any`.

## Lieferumfang Teil 1 und Stand

- [x] Konzeption: Problemstellung, Forschungsfragen, Methoden, Lebenszyklus
- [x] Ingestion: Plattformdaten (GBIF) und Referenz (Vogelwarte) heruntergeladen
- [x] Ingestion: Arealstatistik (Variablenbeschreibung geprüft, 4'129'071 Hektaren)
- [x] Storage: Evaluation und Wahl der Speicherumgebung (DuckDB mit Parquet)
- [x] Transformation Teil 1: initiale Analyse (`profile_data.py`) und Bereinigung (`build_analysis_table.py`)
- [x] Datenprüfungen der bereinigten Tabellen (`check_outputs.py`)
- [x] Hypothesentests H1 bis H3 inklusive Robustheit von H3 (`hypothesis_tests.py`)
- [x] Download-Skript mit DOI, Datum und Prüfsumme im Protokoll (`download_data.py`)
- [x] Orchestrierung (`run_all.sh`)
- [x] Beantwortung der Forschungsfragen im Notebook, mit Quellenangaben
- [x] Sensitivitätsläufe zu Referenzalter und iNaturalist-Schwelle (`build_out_sens_*`, `analysis_out_sens_*`)
- [x] Präsentation (`docs/presentation/`)
- [ ] Weitere Sensitivitätsanalysen (10-km-Meldungen, Brutzeitgrenzen, Randquadrate), vorgesehen für Teil 2

## Ergebnisse der Hypothesentests

Grundlage ist die Hauptanalyse mit Nachweisen ab 2020 und iNaturalist-Meldungen bis 2'500 m Ungenauigkeit (die Parameter stehen im `build_log.json`). Sie umfasst 1'614 Quadrate, also ohne Randquadrate unter 1'000 ha und ohne Quadrate ohne Brutnachweis, mit insgesamt 86'530 Art/Quadrat-Paaren. Die mittlere Abdeckungsquote je Quadrat beträgt 37,2 % für eBird, 5,2 % für iNaturalist, 5,5 % für Observation.org und 39,9 % für alle drei Plattformen zusammen. Weil eBird den grössten Teil der Meldungen stellt, sind die Aussagen zur Abdeckung aller Plattformen weitgehend Aussagen über eBird.

| Hypothese | Test | Effektstärke [95 %-KI] | p (Holm) | Ergebnis |
|---|---|---|---|---|
| H1 Siedlung ↑ → Abdeckung ↑ | Spearman | rho = 0,338 [0,293; 0,382] | 4,7e-44 | gestützt |
| H2 unproduktiv ↑ → Abdeckung ↓ | Spearman | rho = −0,001 [−0,050; 0,048] | 0,974 | nicht gestützt |
| H3 iNaturalist hängt stärker von Siedlung ab als eBird | Interaktionsterm | +0,235 [0,151; 0,319] | 7,2e-08 | nur bedingt gestützt (siehe unten) |

Die Konfidenzintervalle für Spearman nutzen die Fisher-z-Transformation mit der Varianz (1 + rho²/2)/(n − 3) nach Bonett & Wright (2000).

Die Kontrolle des Beobachtungsaufwands verändert das Bild erheblich. Die Zahl der Meldungen je Quadrat korreliert zu rho = 0,934 mit der Abdeckungsquote, und das R² steigt von 0,126 im Modell mit Landnutzung allein auf 0,856, sobald der Aufwand hinzukommt. Der Koeffizient des Siedlungsanteils fällt dabei von +1,20 auf −0,059 [−0,133; 0,015] und ist nicht mehr von null verschieden. Das ist damit vereinbar, dass die Landnutzung über den Aufwand wirkt. Mit Querschnittsdaten lässt sich das aber nicht von einer gemeinsamen Ursache wie der Erreichbarkeit eines Quadrats unterscheiden, und der Zusammenhang zwischen Meldungen und Abdeckung ist teilweise mechanisch: Mehr Meldungen erfassen zwangsläufig mehr Arten. Modell 2 widerlegt H1 nicht; berichtet werden beide Modelle.

H2 bleibt auch ohne Aufwandskontrolle ohne Zusammenhang. Unter Kontrolle des Aufwands ist die Abdeckung in Quadraten mit mehr unproduktiver Fläche leicht höher (+0,130 [0,096; 0,164]). Das ist das Gegenteil der Hypothese; eine mögliche Erklärung ist, dass dort weniger Arten brüten und die wenigen vorkommenden Arten eher erfasst werden. Das haben wir nicht geprüft.

Die Steigung des Siedlungsanteils je Plattform, aus getrennten Modellen mit plattformeigenem Aufwand und HC3-Standardfehlern: eBird −0,118 [−0,191; −0,045], iNaturalist +0,117 [0,065; 0,169], Observation.org −0,026 [−0,065; 0,013]. Bei gleichem plattformeigenem Aufwand nimmt die Abdeckung von eBird mit dem Siedlungsanteil also leicht ab, die von iNaturalist zu.

**Robustheit von H3.** Das Ergebnis hängt an zwei Entscheiden der Modellierung: dass der Aufwand kontrolliert wird und dass er je Plattform verschieden wirken darf. Die zweite Setzung ist begründet, weil die Abdeckung von eBird und iNaturalist auf ganz verschiedenem Niveau liegt. Ohne diese Entscheide kehrt sich das Vorzeichen um:

| Spezifikation | Interaktion iNaturalist × Siedlung [95 %-KI] |
|---|---|
| A: Plattform × Landnutzung und Aufwand (primärer Test) | +0,235 [0,151; 0,319] |
| B: Aufwand mit gemeinsamem Koeffizienten | −0,296 [−0,376; −0,215] |
| C: ohne Kontrolle des Aufwands | −0,714 [−0,871; −0,557] |
| rangbasiert: Spearman Siedlung gegen Abdeckung | eBird 0,361, iNaturalist 0,327, Observation.org 0,200 |

Ohne Kontrolle hängt die Abdeckung von eBird absolut stärker am Siedlungsanteil, rangbasiert sind eBird und iNaturalist etwa gleich. H3 ist damit nur in der bedingten Form gestützt: Bei gleichem plattformeigenem Aufwand steigt die Abdeckung von iNaturalist mit dem Siedlungsanteil, die von eBird sinkt. Die allgemeine Aussage, iNaturalist hänge stärker vom Siedlungsanteil ab, tragen die Daten nicht.

Moran's I der Residuen von Modell 2 beträgt 0,113 (Permutationstest mit 999 Permutationen, p = 0,001, Rook-Nachbarschaft auf dem 5-km-Raster), das der Abdeckungsquote selbst 0,304. Benachbarte Quadrate sind demnach nicht unabhängig, womit die in der Konzeption angekündigte räumliche Autokorrelation tatsächlich auftritt und die p-Werte entsprechend vorsichtig zu interpretieren sind.

Die Abdeckungsquote ist bei iNaturalist und Observation.org ein Anteil nahe 0, wofür die lineare Regression nur eine Näherung ist. Die Aussagen zu H1 und H2 stützen sich deshalb primär auf Spearman; ein binomiales Modell ist für Teil 2 vorgesehen.

### Sensitivität

Die zwei Sensitivitätsläufe verändern je eine Setzung der Hauptanalyse (siehe Pipeline).

| | Hauptanalyse (ab 2020, 2'500 m) | alle Nachweise | iNaturalist bis 5'000 m |
|---|---|---|---|
| Quadrate / Referenzpaare | 1'614 / 86'530 | 1'637 / 127'269 | 1'614 / 86'530 |
| mittlere Abdeckung, alle Plattformen | 39,9 % | 32,6 % | 39,9 % |
| H1 Spearman rho [KI] | 0,338 [0,293; 0,382] | 0,368 [0,324; 0,410] | 0,339 [0,294; 0,382] |
| H2 Spearman rho [KI] | −0,001 [−0,050; 0,048] | −0,042 [−0,090; 0,006] | −0,001 [−0,050; 0,048] |
| H3 Interaktion, primär (A) [KI] | +0,235 [0,151; 0,319] | +0,204 [0,141; 0,268] | +0,236 [0,152; 0,319] |
| H3 Interaktion ohne Aufwand (C) | −0,714 | −0,656 | −0,710 |
| Siedlung in Modell 2 [KI] | −0,059 [−0,133; 0,015] | −0,044 [−0,098; 0,010] | −0,058 [−0,132; 0,017] |
| Moran's I der Residuen | 0,113 | 0,160 | 0,113 |

Die Aussagen sind in allen drei Läufen gleich: H1 gestützt, H2 nicht gestützt, H3 nur in der bedingten Form, der Siedlungsanteil in Modell 2 nicht von null verschieden. Die Schwelle für iNaturalist (2'500 gegen 5'000 m) ändert die Ergebnisse praktisch nicht, weil sie nur 2'455 Meldungen betrifft; sie belegt eher die Qualität der Koordinaten als eine Abhängigkeit der Ergebnisse. Das Referenzalter verschiebt vor allem das Niveau der Abdeckung (32,6 gegen 39,9 %), weil ältere Nachweise häufiger als Lücke erscheinen, und etwas die Effektstärken, ohne eine Schlussfolgerung zu kippen.

## Storage

Die Anforderungen sind tabellarisch und analytisch: ein Schreiber (die Pipeline), keine gleichzeitigen Zugriffe, keine Aktualisierung einzelner Zeilen, gelesen wird spaltenweise über viele Zeilen (Joins und Aggregationen über das Raster).

| Kriterium | Anforderung im Projekt | DuckDB + Parquet | SQLite | PostgreSQL/PostGIS |
|---|---|---|---|---|
| Datenmodell | relational, Aggregation über Spalten | spaltenorientiert (OLAP) | zeilenorientiert (OLTP) | zeilenorientiert, Erweiterungen möglich |
| Betrieb | ohne Server, im Repo reproduzierbar | eingebettet, eine Datei | eingebettet, eine Datei | Server nötig |
| Transaktionen (ACID) | nicht nötig, ein Schreiber im Batch | vorhanden | vorhanden | vorhanden |
| Verteilung (CAP) | nicht relevant, ein Rechner | – | – | Replikation möglich |
| Raumfunktionen | nicht nötig, Raster aus LV95-Koordinaten | Erweiterung «spatial» | SpatiaLite | PostGIS |
| Austauschformat | Tabellen für Notebook und Prüfungen | Parquet ist offen und typisiert | eigenes Dateiformat | Export nötig |

Die Rollen sind getrennt: Parquet ist die Ablage der bereinigten Tabellen, die Notebook, Prüfungen und Hypothesentests lesen. DuckDB ist die Abfrage-Engine; sie liest die Roh-CSV in der Bereinigung, und `build_out/birdreports.duckdb` bündelt alle vier Tabellen für SQL-Abfragen. Das Notebook nutzt sie für die Frage, welche Arten auf den Plattformen am häufigsten fehlen:

```
python -c "import duckdb; print(duckdb.connect('build_out/birdreports.duckdb', read_only=True).sql(
  'SELECT platform, COUNT(*) AS meldungen FROM platform_clean GROUP BY 1 ORDER BY 2 DESC'))"
```

PostgreSQL haben wir aufgrund der Kriterien nicht gemessen; ein Server bringt hier Betriebsaufwand ohne Nutzen. `src/storage_test.py` vergleicht DuckDB mit SQLite auf den Projektdaten:

| | DuckDB | SQLite |
|---|---|---|
| Laden Arealstatistik (4,1 Mio. Zeilen) | 0,26 s | 2,89 s |
| Laden Plattformdaten (1,6 Mio. Zeilen) | 2,29 s | 4,24 s |
| Aggregation auf 5-km-Quadrate | 0,01 s | 1,13 s |
| Zählung nach Datensatz, Jahr und Monat | 0,01 s | 1,01 s |
| Dateigrösse der Datenbank | 46,7 MB | 272,9 MB |

Es handelt sich um eine Einzelmessung auf einem Rechner, ohne Wiederholung. Die Ladezeiten sind nur bedingt vergleichbar, weil DuckDB die CSV mit dem eigenen Leser lädt und SQLite über pandas in Blöcken befüllt wird. Aussagekräftig sind die Abfragezeiten und die Dateigrösse; der Abstand bei den Aggregationen (Faktor rund 100) entspricht dem, was man von spaltenorientierter gegenüber zeilenorientierter Speicherung erwartet. Die Plattformdaten umfassen als Parquet mit neun Spalten 26,5 MB.

## Skalierbarkeit

Heute verarbeitet die Pipeline rund 600'000 bereinigte Meldungen und 1'839 Quadrate in wenigen Minuten auf einem Laptop. Bei 10-mal mehr Daten (weitere Jahre, Nachbarländer) oder einem 1-km-Raster (25-mal mehr Quadrate) wären das die Grenzen:

| Phase | trägt heute | Grenze | nächster Schritt |
|---|---|---|---|
| Ingestion | ein GBIF-Download, 1,6 Mio. Zeilen | Search-API höchstens 100'000 Treffer pro Abfrage | GBIF-Download ist asynchron und skaliert; der Fallback teilt bereits nach Datensatz, Jahr und Monat auf |
| Storage | Parquet und DuckDB auf einem Rechner | ein Schreiber, lokale Festplatte | Parquet nach Jahr und Datensatz partitionieren; DuckDB verarbeitet auch Daten grösser als der Arbeitsspeicher |
| Transformation | pandas im Arbeitsspeicher | RAM bei mehreren Millionen Meldungen | Raster und Aggregation in DuckDB-SQL statt pandas |
| Analyse | 1'614 Quadrate | Moran's-I-Permutationen wachsen mit der Zahl der Quadrate | dünn besetzte Gewichtsmatrix ist umgesetzt; ein 1-km-Raster trägt das noch |

## Hinweise zu den Daten

- Die Brutvogeldatenbank führt pro Art und Quadrat nur das letzte Brutjahr und stützt sich vor allem auf validierte Meldungen von [ornitho.ch](https://www.ornitho.ch) sowie auf Monitoringprogramme. Sie ist keine unabhängige Erhebung.
- Die Artnamen der Referenz weichen bei 17 von 213 Arten von denen der Plattformdaten ab, überwiegend wegen Gattungsumbenennungen. Für 16 dieser Arten existiert ein Gegenname in den Plattformdaten; für *Ficedula parva* liegt im Zeitraum keine Meldung vor. Die Zuordnung ist in [`mappings/taxon_mapping.csv`](mappings/taxon_mapping.csv) mit Begründung je Zeile festgehalten.
- Beobachterkennungen werden vor dem Speichern gehasht; Klarnamen liegen nicht im Repository.
