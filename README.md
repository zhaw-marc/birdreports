# Birdreports

Projektarbeit im Modul Data Engineering (HS26, ZHAW). Wir untersuchen, wie vollständig Citizen-Science-Plattformen die Brutverbreitung von Vögeln in der Schweiz abbilden, und ob die Landnutzung die Lücken erklärt.

## Gruppe

| Name | ZHAW-Mail |
|---|---|
| Marc Vogelmann | vogmar04@students.zhaw.ch |
| Muriele Stermcnik | stermmur@students.zhaw.ch |
| Alen Rama | ramaale1@students.zhaw.ch |

## Fragestellung

Als Referenz dient die Schweizerische Brutvogeldatenbank der Vogelwarte Sempach (Brutnachweise pro Art und 5×5-km-Quadrat). Für jedes Quadrat prüfen wir, ob eBird, iNaturalist und Observation.org die dort brütenden Arten im Zeitraum 2020–2024 während der Brutzeit (April bis Juli) melden. Die Abdeckungsquote eines Quadrats ist der Anteil der Arten mit Brutnachweis, die auf einer Plattform gemeldet sind.

- **FF1: Landnutzung.** Hängt die Abdeckungsquote eines Quadrats von seiner Landnutzung ab?
  - H1: Je höher der Siedlungsanteil, desto höher die Abdeckungsquote.
  - H2: Je höher der Anteil unproduktiver Fläche, desto niedriger die Abdeckungsquote.
- **FF2: Plattformen.** Unterscheiden sich die Plattformen im Abdeckungsmuster?
  - H3: Die Abdeckungsquote von iNaturalist hängt stärker vom Siedlungsanteil ab als die von eBird.

Die Konzeption (Problemstellung, Methoden, Lebenszyklus, Limitationen) steht im separaten Dokument «Projektarbeit Teil 1: Konzeption».

## Datenquellen

| Quelle | Inhalt | Lizenz |
|---|---|---|
| eBird Observation Dataset (GBIF) | Beobachtungen, Schweiz, Vögel, 2020–2024 | CC BY 4.0 |
| Observation.org (GBIF) | Beobachtungen, Schweiz, Vögel, 2020–2024 | CC BY-NC 4.0 |
| iNaturalist Research-grade Observations (GBIF) | Foto-Belege, Schweiz, Vögel, 2020–2024 | je Beobachtung CC0, CC BY oder CC BY-NC |
| Swiss National Breeding Bird Databank (Vogelwarte) | Letztes Brutjahr pro Art und 5×5-km-Quadrat, Version 1.1 | CC BY 4.0 |
| Arealstatistik BFS, Aktueller Stand (CSV) | Landnutzung pro Hektare, Erhebungsjahre 2013–2020 | Quellenangabe, kommerziell nur mit Zustimmung |

**Zitate**

- Wechsler S, Volet B, Schmid H (2023). Swiss National Breeding Bird Databank. Version 1.1. Swiss Ornithological Institute. DOI 10.15468/jujcgr.
- GBIF.org (13 October 2026). GBIF Occurrence Download. https://doi.org/10.15468/dl.9qfxn7 (Download-Key `0024005-260928105237408`).

## Daten beschaffen

Die Rohdaten liegen **nicht** im Repository (Grösse, GitHub-Limit von 100 MB pro Datei). Sie werden lokal nach `data/` gelegt.

1. **Plattformdaten:** GBIF-Download mit den Filtern Country = Switzerland, Year 2020–2024, Scientific name = Aves, Occurrence status = Present, taxonomische Referenz Catalogue of Life. Er enthält die drei Plattform-Datensätze, dazu 87'741 Zeilen der Vogelwarte-Datenbank (nur Brutjahre ab 2020, als Referenz ungeeignet) und 94 Zeilen aus drei weiteren Datensätzen. Wir verwenden nur die drei Dataset-Keys der Plattformen aus der Tabelle oben. Ablage: `data/0024005-260928105237408.csv` (Tab-getrennt trotz Endung).
2. **Referenz:** Darwin-Core-Archiv der Brutvogeldatenbank von der Vogelwarte, ohne Jahresfilter. Der Download über GBIF mit Jahresfilter ist ungeeignet, weil `year` dort das letzte Brutjahr ist. Ablage: `data/dwca-soi_aves-v1/` (enthält `occurrence.txt`, `meta.xml`, `eml.xml`). Die Datei enthält 135'310 Datensätze, davon 129'240 in der Schweiz.
3. **Landnutzung:** Arealstatistik «Aktueller Stand» als CSV von opendata.swiss, Ablage in `data/`.

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
├── src/
│   ├── storage_test.py          # Storage-Evaluation DuckDB gegen SQLite
│   ├── profile_data.py          # initiale Analyse der Datengrundlage (misst nur)
│   ├── build_analysis_table.py  # Bereinigung und Analysetabelle pro Quadrat
│   └── hypothesis_tests.py      # Hypothesentests H1 bis H3
├── mappings/
│   └── taxon_mapping.csv # Artnamen Vogelwarte gegen Catalogue of Life
├── build_out/            # bereinigte Tabellen, Analysetabelle, Analysedatenbank
├── analysis_out/         # Ergebnisse der Hypothesentests
└── data/                 # lokal, nicht versioniert
```

Die Struktur wächst mit den Schritten unten.

## Pipeline

```
python src/profile_data.py         AREAL.csv PLATTFORM.csv VOGELWARTE/occurrence.txt mappings/taxon_mapping.csv
python src/build_analysis_table.py AREAL.csv PLATTFORM.csv VOGELWARTE/occurrence.txt mappings/taxon_mapping.csv
python src/hypothesis_tests.py     build_out/analyse_quadrate.parquet
```

`build_analysis_table.py` bereinigt die drei Quellen nach den Regeln der Konzeption und
schreibt nach `build_out/`:

| Datei | Inhalt |
|---|---|
| `plattform_clean.parquet` | 605'576 Meldungen (drei Plattformen, CH, 2020–2024, April–Juli, Beobachter gehasht) |
| `referenz_clean.parquet` | 129'240 Art/Quadrat-Paare der Vogelwarte, 213 Arten, 10-km-Meldungen markiert |
| `landnutzung_cells.parquet` | 1'839 Quadrate mit Hektaren und Anteilen der vier AS_4-Klassen |
| `analyse_quadrate.csv/.parquet` | Analysetabelle, eine Zeile pro Quadrat (1'839, davon 1'637 in der Hauptanalyse) |
| `birdreports.duckdb` | Analysedatenbank mit allen vier Tabellen (18,9 MB) |
| `build_log.json` | Parameter, Eingabepfade und Zeilenzahlen des Laufs |

Die Beobachterkennung wird mit einem festen Salt (BLAKE2s, 8 Byte) gehasht, bevor
irgendetwas geschrieben wird; `recordedBy` verlässt das Skript nicht im Klartext.

## Lieferumfang Teil 1 und Stand

- [x] Konzeption: Problemstellung, Forschungsfragen, Methoden, Lebenszyklus
- [x] Ingestion: Plattformdaten (GBIF) und Referenz (Vogelwarte) heruntergeladen
- [x] Ingestion: Arealstatistik (Variablenbeschreibung geprüft, 4'129'071 Hektaren)
- [x] Storage: Evaluation und Wahl der Speicherumgebung (DuckDB mit Parquet)
- [x] Transformation Teil 1: initiale Analyse (`profile_data.py`) und Bereinigung (`build_analysis_table.py`)
- [x] Hypothesentests H1–H3 (`hypothesis_tests.py`)
- [ ] Beantwortung der Forschungsfragen im Notebook, mit Quellenangaben
- [ ] Sensitivitätsanalysen (10-km-Meldungen, Brutzeitgrenzen, Randquadrate)
- [ ] Tests für die Transformationsschritte
- [ ] Download-Skript mit DOI und Datum im Log
- [ ] Präsentation

Der offene Stand und die Lücken gegenüber dem Bewertungsraster stehen in
[docs/lueckenanalyse-teil1.md](docs/lueckenanalyse-teil1.md).

## Ergebnisse der Hypothesentests

Grundlage: 1'637 Quadrate der Hauptanalyse (Randquadrate unter 1'000 ha und Quadrate ohne
Brutnachweis ausgeschlossen) mit 127'269 Art/Quadrat-Paaren. Mittlere Abdeckungsquote je
Quadrat: eBird 30,5 %, iNaturalist 4,7 %, Observation.org 4,2 %, alle drei zusammen 33,0 %.

| Hypothese | Test | Effektstärke [95 %-KI] | p (Holm) | Ergebnis |
|---|---|---|---|---|
| H1 Siedlung ↑ → Abdeckung ↑ | Spearman | rho = 0,357 [0,311; 0,401] | 6,6e-50 | gestützt |
| H2 unproduktiv ↑ → Abdeckung ↓ | Spearman | rho = −0,026 [−0,077; 0,026] | 0,296 | nicht gestützt |
| H3 iNaturalist hängt stärker von Siedlung ab als eBird | Interaktionsterm | +0,205 [0,141; 0,270] | 8,0e-10 | gestützt |

Zwei Befunde brauchen eine Einordnung in der Präsentation:

- **Der Beobachtungsaufwand erklärt die Abdeckung fast vollständig.** Die Zahl der Meldungen
  je Quadrat korreliert mit rho = 0,95 mit der Abdeckungsquote; das R² steigt von 0,140
  (nur Landnutzung) auf 0,882, sobald der Aufwand als Kontrolle dazukommt. Der Koeffizient
  des Siedlungsanteils fällt dabei von +1,07 auf −0,056 [−0,112; −0,000]. Die Landnutzung
  wirkt also weitgehend **über** den Aufwand. Modell 2 widerlegt H1 nicht, es zeigt, dass der
  Aufwand der Mediator ist — beide Modelle werden berichtet.
- **H2 kehrt unter Kontrolle sogar das Vorzeichen um** (+0,097 [0,073; 0,120]): Bei gleichem
  Aufwand ist die Abdeckung in unproduktiven Quadraten leicht höher, vermutlich weil dort
  weniger Arten brüten und die wenigen Arten eher erfasst werden.

Einzelne Steigungen des Siedlungsanteils je Plattform (eigene Modelle, HC3): eBird −0,101
[−0,154; −0,047], iNaturalist +0,105 [0,053; 0,156], Observation.org −0,002 [−0,036; 0,031].

**Räumliche Autokorrelation:** Moran's I der Residuen von Modell 2 beträgt 0,161
(Permutationstest, 999 Permutationen, p = 0,001; Rook-Nachbarschaft auf dem 5-km-Raster).
Benachbarte Quadrate sind also nicht unabhängig, die p-Werte sind entsprechend vorsichtig zu
lesen. Das ist die in der Konzeption angekündigte Limitation; sie tritt ein.

## Storage

Die Analysedatenbank ist DuckDB, die bereinigten Rohdaten liegen als Parquet vor. Das Skript `src/storage_test.py` vergleicht DuckDB mit SQLite auf den Projektdaten (Einzelmessung, ein Rechner). Ergebnis:

| | DuckDB | SQLite |
|---|---|---|
| Laden Arealstatistik (4,1 Mio. Zeilen) | 0,27 s | 2,89 s |
| Laden Plattformdaten (1,6 Mio. Zeilen) | 2,43 s | 4,22 s |
| Aggregation auf 5-km-Quadrate | 0,01 s | 1,13 s |
| Zählung nach Datensatz, Jahr und Monat | 0,01 s | 1,01 s |
| Dateigrösse der Datenbank | 46,9 MB | 272,9 MB |

Die Plattformdaten als Parquet (neun Spalten) umfassen 26,5 MB. PostgreSQL/PostGIS wurde nicht gemessen: Es braucht einen Server, und räumliche Funktionen sind nicht nötig, weil die Quadrate aus den LV95-Koordinaten berechnet werden.

## Hinweise zu den Daten

- Die Brutvogeldatenbank enthält pro Art und Quadrat nur das letzte Brutjahr und beruht vor allem auf validierten ornitho.ch-Meldungen. Sie ist keine unabhängige Erhebung.
- Namen in der Referenz und in den Plattformdaten weichen bei 17 von 213 Arten ab (Gattungsumbenennungen). Die Zuordnung wird in einer Tabelle im Repository festgehalten.
- Beobachter-Kennungen werden vor dem Speichern gehasht, es liegen keine Klarnamen im Repository.
