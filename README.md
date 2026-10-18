# Birdreports

Projektarbeit im Modul Data Engineering (HS26, ZHAW). Wir untersuchen, wie vollständig Citizen-Science-Plattformen die Brutverbreitung von Vögeln in der Schweiz abbilden, und ob sich die Lücken mit der Landnutzung erklären lassen.

## Gruppe

| Name | ZHAW-Mail |
|---|---|
| Marc Vogelmann | vogmar04@students.zhaw.ch |
| Muriele Stermcnik | stermmur@students.zhaw.ch |
| Alen Rama | ramaale1@students.zhaw.ch |

## Fragestellung

Als Referenz dient die Schweizerische Brutvogeldatenbank der Vogelwarte Sempach mit Brutnachweisen pro Art und 5×5-km-Quadrat. Für jedes Quadrat prüfen wir, ob eBird, iNaturalist und Observation.org die dort brütenden Arten im Zeitraum 2020–2024 während der Brutzeit (April bis Juli) melden. Die Abdeckungsquote eines Quadrats ist der Anteil der Arten mit Brutnachweis, die auf einer Plattform gemeldet sind.

FF1 (Landnutzung): Hängt die Abdeckungsquote eines Quadrats von seiner Landnutzung ab?

- H1: Je höher der Siedlungsanteil, desto höher die Abdeckungsquote.
- H2: Je höher der Anteil unproduktiver Fläche, desto niedriger die Abdeckungsquote.

FF2 (Plattformen): Unterscheiden sich die Plattformen im Abdeckungsmuster?

- H3: Die Abdeckungsquote von iNaturalist hängt stärker vom Siedlungsanteil ab als die von eBird.

Problemstellung, Methodik, Lebenszyklus und Limitationen sind im separaten Dokument «Projektarbeit Teil 1: Konzeption» ausgeführt.

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

Die Rohdaten liegen wegen ihrer Grösse und des GitHub-Limits von 100 MB pro Datei nicht im Repository. Sie gehören lokal nach `data/`.

1. Plattformdaten: GBIF-Download mit den Filtern Country = Switzerland, Year 2020–2024, Scientific name = Aves, Occurrence status = Present und taxonomischer Referenz Catalogue of Life. Der Export enthält neben den drei Plattform-Datensätzen 87'741 Zeilen der Vogelwarte-Datenbank, die wegen der Jahresfilterung nur Brutjahre ab 2020 abdecken und als Referenz ungeeignet sind, sowie 94 Zeilen aus drei weiteren Datensätzen. Verwendet werden ausschliesslich die drei Dataset-Keys aus der Tabelle oben. Ablage: `data/0024005-260928105237408.csv`, trotz Endung tabulatorgetrennt.
2. Referenz: Darwin-Core-Archiv der Brutvogeldatenbank direkt von der Vogelwarte, ohne Jahresfilter. Der Bezug über GBIF mit Jahresfilter wäre ungeeignet, weil `year` dort das letzte Brutjahr bezeichnet. Ablage: `data/dwca-soi_aves-v1/` mit `occurrence.txt`, `meta.xml` und `eml.xml`. Das Archiv umfasst 135'310 Datensätze, davon 129'240 in der Schweiz.
3. Landnutzung: Arealstatistik «Aktueller Stand» als CSV, Ablage in `data/`.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Struktur

```
birdreports/
├── README.md
├── requirements.txt
├── .gitignore
├── docs/
│   └── lueckenanalyse-teil1.md  # Abgleich mit Bewertungsraster und Vorlesung
├── src/
│   ├── storage_test.py          # Storage-Evaluation DuckDB gegen SQLite
│   ├── profile_data.py          # initiale Analyse der Datengrundlage (misst nur)
│   ├── build_analysis_table.py  # Bereinigung und Analysetabelle pro Quadrat
│   └── hypothesis_tests.py      # Hypothesentests H1 bis H3
├── mappings/
│   └── taxon_mapping.csv        # Artnamen Vogelwarte gegen Catalogue of Life
├── build_out/                   # bereinigte Tabellen, Analysetabelle, Analysedatenbank
├── analysis_out/                # Ergebnisse der Hypothesentests
└── data/                        # lokal, nicht versioniert
```

## Pipeline

```
python src/profile_data.py         AREAL.csv PLATTFORM.csv VOGELWARTE/occurrence.txt mappings/taxon_mapping.csv
python src/build_analysis_table.py AREAL.csv PLATTFORM.csv VOGELWARTE/occurrence.txt mappings/taxon_mapping.csv
python src/hypothesis_tests.py     build_out/analyse_quadrate.parquet
```

`build_analysis_table.py` bereinigt die drei Quellen nach den Regeln der Konzeption und schreibt nach `build_out/`:

| Datei | Inhalt |
|---|---|
| `plattform_clean.parquet` | 605'576 Meldungen (drei Plattformen, CH, 2020–2024, April–Juli, Beobachter gehasht) |
| `referenz_clean.parquet` | 129'240 Art/Quadrat-Paare der Vogelwarte, 213 Arten, 10-km-Meldungen markiert |
| `landnutzung_cells.parquet` | 1'839 Quadrate mit Hektaren und Anteilen der vier AS_4-Klassen |
| `analyse_quadrate.csv/.parquet` | Analysetabelle, eine Zeile pro Quadrat (1'839, davon 1'637 in der Hauptanalyse) |
| `birdreports.duckdb` | Analysedatenbank mit allen vier Tabellen (18,9 MB) |
| `build_log.json` | Parameter, Eingabepfade und Zeilenzahlen des Laufs |

Die Beobachterkennung wird mit einem festen Salt gehasht (BLAKE2s, 8 Byte), bevor irgendetwas geschrieben wird; `recordedBy` verlässt das Skript nicht im Klartext.

## Lieferumfang Teil 1 und Stand

- [x] Konzeption: Problemstellung, Forschungsfragen, Methoden, Lebenszyklus
- [x] Ingestion: Plattformdaten (GBIF) und Referenz (Vogelwarte) heruntergeladen
- [x] Ingestion: Arealstatistik (Variablenbeschreibung geprüft, 4'129'071 Hektaren)
- [x] Storage: Evaluation und Wahl der Speicherumgebung (DuckDB mit Parquet)
- [x] Transformation Teil 1: initiale Analyse (`profile_data.py`) und Bereinigung (`build_analysis_table.py`)
- [x] Hypothesentests H1 bis H3 (`hypothesis_tests.py`)
- [ ] Beantwortung der Forschungsfragen im Notebook, mit Quellenangaben
- [ ] Sensitivitätsanalysen (10-km-Meldungen, Brutzeitgrenzen, Randquadrate)
- [ ] Tests für die Transformationsschritte
- [ ] Download-Skript mit DOI und Datum im Log
- [ ] Präsentation

Die Lücken gegenüber dem Bewertungsraster sind in [docs/lueckenanalyse-teil1.md](docs/lueckenanalyse-teil1.md) dokumentiert.

## Ergebnisse der Hypothesentests

Grundlage sind 1'637 Quadrate der Hauptanalyse, also ohne Randquadrate unter 1'000 ha und ohne Quadrate ohne Brutnachweis, mit insgesamt 127'269 Art/Quadrat-Paaren. Die mittlere Abdeckungsquote je Quadrat beträgt 30,5 % für eBird, 4,7 % für iNaturalist, 4,2 % für Observation.org und 33,0 % für alle drei Plattformen zusammen.

| Hypothese | Test | Effektstärke [95 %-KI] | p (Holm) | Ergebnis |
|---|---|---|---|---|
| H1 Siedlung ↑ → Abdeckung ↑ | Spearman | rho = 0,357 [0,311; 0,401] | 6,6e-50 | gestützt |
| H2 unproduktiv ↑ → Abdeckung ↓ | Spearman | rho = −0,026 [−0,077; 0,026] | 0,296 | nicht gestützt |
| H3 iNaturalist hängt stärker von Siedlung ab als eBird | Interaktionsterm | +0,205 [0,141; 0,270] | 8,0e-10 | gestützt |

Die Kontrolle des Beobachtungsaufwands verändert das Bild erheblich. Die Zahl der Meldungen je Quadrat korreliert zu rho = 0,95 mit der Abdeckungsquote, und das R² steigt von 0,140 im Modell mit Landnutzung allein auf 0,882, sobald der Aufwand hinzukommt. Der Koeffizient des Siedlungsanteils fällt dabei von +1,07 auf −0,056 [−0,112; −0,000]. Die Landnutzung wirkt also überwiegend über den Aufwand. Modell 2 widerlegt H1 damit nicht, sondern weist den Aufwand als Mediator aus; berichtet werden beide Modelle.

H2 kehrt unter Kontrolle des Aufwands sogar das Vorzeichen um (+0,097 [0,073; 0,120]). Bei gleichem Aufwand ist die Abdeckung in unproduktiven Quadraten leicht höher, vermutlich weil dort weniger Arten brüten und die wenigen vorkommenden Arten eher erfasst werden.

Die Steigung des Siedlungsanteils je Plattform, aus getrennten Modellen mit HC3-Standardfehlern: eBird −0,101 [−0,154; −0,047], iNaturalist +0,105 [0,053; 0,156], Observation.org −0,002 [−0,036; 0,031].

Moran's I der Residuen von Modell 2 beträgt 0,161 (Permutationstest mit 999 Permutationen, p = 0,001, Rook-Nachbarschaft auf dem 5-km-Raster). Benachbarte Quadrate sind demnach nicht unabhängig, womit die in der Konzeption angekündigte räumliche Autokorrelation tatsächlich auftritt und die p-Werte entsprechend vorsichtig zu interpretieren sind.

## Storage

Die Analysedatenbank ist DuckDB, die bereinigten Rohdaten liegen als Parquet vor. `src/storage_test.py` vergleicht DuckDB mit SQLite auf den Projektdaten; es handelt sich um eine Einzelmessung auf einem Rechner.

| | DuckDB | SQLite |
|---|---|---|
| Laden Arealstatistik (4,1 Mio. Zeilen) | 0,27 s | 2,89 s |
| Laden Plattformdaten (1,6 Mio. Zeilen) | 2,43 s | 4,22 s |
| Aggregation auf 5-km-Quadrate | 0,01 s | 1,13 s |
| Zählung nach Datensatz, Jahr und Monat | 0,01 s | 1,01 s |
| Dateigrösse der Datenbank | 46,9 MB | 272,9 MB |

Die Plattformdaten umfassen als Parquet mit neun Spalten 26,5 MB. PostgreSQL mit PostGIS haben wir nicht gemessen, weil es einen Server voraussetzt und räumliche Funktionen entbehrlich sind: Die Quadrate werden aus den LV95-Koordinaten gerechnet.

## Hinweise zu den Daten

- Die Brutvogeldatenbank führt pro Art und Quadrat nur das letzte Brutjahr und stützt sich vor allem auf validierte Meldungen von [ornitho.ch](https://www.ornitho.ch) sowie auf Monitoringprogramme. Sie ist keine unabhängige Erhebung.
- Die Artnamen der Referenz weichen bei 17 von 213 Arten von denen der Plattformdaten ab, überwiegend wegen Gattungsumbenennungen. Für 16 dieser Arten existiert ein Gegenname in den Plattformdaten; für *Ficedula parva* liegt im Zeitraum keine Meldung vor. Die Zuordnung ist in [`mappings/taxon_mapping.csv`](mappings/taxon_mapping.csv) mit Begründung je Zeile festgehalten.
- Beobachterkennungen werden vor dem Speichern gehasht; Klarnamen liegen nicht im Repository.
