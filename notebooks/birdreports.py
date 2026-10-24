"""Serving: Notebook zur Projektarbeit Teil 1 (Data Engineering HS26, ZHAW).

Das Notebook liest die gespeicherten Ergebnisse der Pipeline (build_out/, analysis_out/,
profile_out/, storage_test_out/, ingest_out/) und stellt Konzeption, Lebenszyklus,
Ergebnisse und Antworten auf die Forschungsfragen dar. Es rechnet die Pipeline nicht neu;
die Rohdaten (826 MB und mehr) werden dafuer nicht gebraucht. Die Pipeline selbst steht
im README unter "Pipeline".

Start:   marimo edit notebooks/birdreports.py      (interaktiv)
         marimo run  notebooks/birdreports.py      (nur lesen)

Quellen (Zitierweise nach ZHAW-Leitfaden, APA 7):
  Reis, J. & Housley, M. (2022). Fundamentals of Data Engineering. O'Reilly Media.
  Holm, S. (1979). A simple sequentially rejective multiple test procedure.
    Scandinavian Journal of Statistics, 6(2), 65-70.
  Bonett, D. G. & Wright, T. A. (2000). Sample size requirements for estimating Pearson,
    Kendall and Spearman correlations. Psychometrika, 65, 23-28.
  Moran, P. A. P. (1950). Notes on continuous stochastic phenomena. Biometrika, 37, 17-23.
  Anselin, L. (1995). Local indicators of spatial association - LISA.
    Geographical Analysis, 27(2), 93-115.
  MacKinnon, J. G. & White, H. (1985). Some heteroskedasticity-consistent covariance matrix
    estimators with improved finite sample properties. Journal of Econometrics, 29, 305-325.
"""
import marimo

app = marimo.App(width="medium", app_title="Birdreports – Teil 1")


@app.cell
def _():
    import json
    import re
    from pathlib import Path

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    return Path, json, mo, np, pd, plt, re


@app.cell
def _(Path, json, pd):
    ROOT = Path(__file__).resolve().parent.parent

    def read_json(relative):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def entry(report, prefix):
        """Eintrag eines gespeicherten Berichts anhand des Titelanfangs."""
        return report[next(k for k in report if k.startswith(prefix))]

    def as_frame(report, prefix):
        d = entry(report, prefix)
        return pd.DataFrame(d["data"], index=d["index"], columns=d["columns"])

    return ROOT, as_frame, entry, read_json


@app.cell
def _(ROOT, pd, read_json):
    res_main = read_json("analysis_out/hypothesis_tests.json")
    res_all_years = read_json("analysis_out_sens_all_years/hypothesis_tests.json")
    res_5000m = read_json("analysis_out_sens_5000m/hypothesis_tests.json")
    profile = read_json("profile_out/profile.json")
    build_log = read_json("build_out/build_log.json")
    storage = read_json("storage_test_out/storage_test.json")
    download_log = read_json("ingest_out/download_log.json")
    cells = pd.read_parquet(ROOT / "build_out" / "analysis_cells.parquet")
    main_cells = cells[cells.in_main_analysis].copy()
    return (
        build_log,
        cells,
        download_log,
        main_cells,
        profile,
        res_5000m,
        res_all_years,
        res_main,
        storage,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # Birdreports: Wie vollständig bilden Citizen-Science-Plattformen die Brutverbreitung ab?

    **Data Engineering HS26, Projektarbeit Teil 1** · Marc Vogelmann, Muriele Stermcnik, Alen Rama

    Dieses Notebook ist das Serving-Artefakt von Teil 1. Es folgt dem Data-Engineering-Lebenszyklus
    nach Reis & Housley (2022) und liest die gespeicherten Ergebnisse der Pipeline. Der Code der
    Pipeline liegt in `src/`, die Befehle stehen im README.

    1. Konzeptionalisierung
    2. Entwurf des Lebenszyklus
    3. Ingestion
    4. Storage
    5. Transformation Teil 1: Analyse der Datengrundlage und Bereinigung
    6. Hypothesentests
    7. Sensitivität
    8. Beantwortung der Forschungsfragen
    9. Limitationen und Ausblick auf Teil 2
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Konzeptionalisierung

    **Problemstellung.** Auf eBird, iNaturalist und Observation.org melden Freiwillige jährlich
    Hunderttausende Schweizer Vogelbeobachtungen. Wer diese Daten für Verbreitungskarten oder
    Schutzentscheide nutzt, muss wissen, wo sie verlässlich sind. Als Vergleichsmassstab dient die
    Schweizerische Brutvogeldatenbank der Vogelwarte Sempach (geprüfte Brutnachweise pro Art und
    5×5-km-Quadrat). Sie ist keine unabhängige Erhebung, weil sie sich auch auf ornitho.ch stützt,
    taugt aber als Referenz.

    **Begriffe.** Eine *Abdeckung* liegt für eine Art in einem Quadrat vor, wenn die Vogelwarte dort
    einen Brutnachweis hat und eine Plattform die Art 2020–2024 in der Brutzeit (April bis Juli) im
    selben Quadrat meldet. Die *Abdeckungsquote* eines Quadrats ist der Anteil der Arten mit
    Brutnachweis, die so abgedeckt sind.

    | | Frage / Hypothese |
    |---|---|
    | **FF1** Landnutzung | Hängt die Abdeckungsquote eines Quadrats von seiner Landnutzung ab? |
    | H1 | Je höher der Siedlungsanteil, desto höher die Abdeckungsquote. |
    | H2 | Je höher der Anteil unproduktiver Fläche, desto niedriger die Abdeckungsquote. |
    | **FF2** Plattformen | Unterscheiden sich die Plattformen im Abdeckungsmuster? |
    | H3 | Die Abdeckungsquote von iNaturalist hängt stärker vom Siedlungsanteil ab als die von eBird. |

    **Methoden.** Alle Quellen werden auf ein 5-km-Raster in LV95 gebracht (`floor(E/5000)`,
    `floor(N/5000)`), und die Hypothesen werden auf Quadratebene getestet: Spearman-Korrelation für
    H1 und H2, multiple Regression mit dem Beobachtungsaufwand als Kontrolle, ein Interaktionsterm
    Plattform × Siedlung für H3, Holm-Korrektur über die drei Haupttests und Moran's I für die
    räumliche Autokorrelation.

    **Setzungen der Hauptanalyse.** Nur Referenznachweise mit letztem Brutjahr ab 2020 (die
    Datenbank führt pro Art und Quadrat nur das letzte Brutjahr, ältere Nachweise lassen offen, ob
    die Art im Beobachtungszeitraum noch dort brütet). iNaturalist-Meldungen mit einer
    Koordinatenungenauigkeit über 2'500 m entfallen. Quadrate unter 1'000 Hektaren (Randquadrate)
    und 10-km-Meldungen der Referenz bleiben draussen. Beide Setzungen werden in Abschnitt 7
    variiert.
    """)
    return


@app.cell
def _(ROOT, mo, re):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    diagram = re.search(r"```mermaid\n(.*?)```", readme, re.S).group(1)
    mo.vstack([
        mo.md(r"""
        ## 2. Entwurf des Data-Engineering-Lebenszyklus

        Der Entwurf folgt den fünf Phasen und den Unterströmungen nach Reis & Housley (2022).
        Wir priorisieren Reproduzierbarkeit und Einfachheit, akzeptieren dafür, dass die Daten
        nicht aktuell gehalten werden, und begrenzen das Risiko durch Rohdaten mit Abrufdatum,
        DOI und Prüfsumme. Ein Streaming- oder Lambda-Aufbau wäre bei einem einmaligen Batch mit
        rund 600'000 Meldungen nicht begründbar. Die Daten sind begrenzt (bounded) und kommen per
        Pull; wir laden zuerst und transformieren danach (ELT), damit die Rohdaten für die
        Prüfung unverändert bleiben. Der Entscheid ist umkehrbar, weil jede Schicht aus der
        vorherigen neu berechnet werden kann.

        Das Diagramm stammt aus dem README, damit es nur an einer Stelle gepflegt wird.
        """),
        mo.mermaid(diagram),
    ])
    return


@app.cell
def _(download_log, mo, pd):
    _rows = []
    for _name, _src in download_log["runs"][-1]["sources"].items():
        _rows.append({"Quelle": _name, **{k: v for k, v in _src.items()}})
    sources_table = pd.DataFrame(_rows)
    mo.vstack([
        mo.md(r"""
        ## 3. Ingestion

        Drei Quellen, alle ohne Schlüssel und per Pull:

        - **Plattformdaten:** GBIF Occurrence Download für die Schweiz, Vögel, 2020–2024,
          taxonomische Referenz Catalogue of Life (DOI 10.15468/dl.9qfxn7). Er enthält die drei
          Plattform-Datensätze eBird, Observation.org und iNaturalist.
        - **Referenz:** Darwin-Core-Archiv der Brutvogeldatenbank direkt von der Vogelwarte, ohne
          Jahresfilter (DOI 10.15468/jujcgr). Der Bezug über GBIF mit Jahresfilter wäre ungeeignet,
          weil `year` dort das letzte Brutjahr ist.
        - **Landnutzung:** Arealstatistik des BFS, «Aktueller Stand», 4'129'071 Stichprobenpunkte
          (ein Punkt pro Hektare).

        `src/download_data.py` lädt die Quellen und schreibt Datum, URL, DOI, HTTP-Status, Grösse
        und SHA-256-Prüfsumme in ein Protokoll. Letzter Eintrag des Protokolls:
        """),
        mo.ui.table(sources_table, selection=None),
    ])
    return


@app.cell
def _(mo, pd, storage):
    _rows = [
        ("Laden Arealstatistik (4,1 Mio. Zeilen), s", storage["duckdb: laden Arealstatistik"], storage["sqlite: laden Arealstatistik"]),
        ("Laden Plattformdaten (1,6 Mio. Zeilen), s", storage["duckdb: laden Plattformdaten"], storage["sqlite: laden Plattformdaten"]),
        ("Aggregation auf 5-km-Quadrate, s", storage["duckdb: Abfrage A (Quadrate)"], storage["sqlite: Abfrage A (Quadrate)"]),
        ("Zählung nach Datensatz, Jahr, Monat, s", storage["duckdb: Abfrage B (Datensatz/Jahr/Monat)"], storage["sqlite: Abfrage B (Datensatz/Jahr/Monat)"]),
        ("Dateigrösse der Datenbank, MB", storage["duckdb_file_mb"], storage["sqlite_file_mb"]),
    ]
    storage_table = pd.DataFrame(_rows, columns=["Messung", "DuckDB", "SQLite"])
    mo.vstack([
        mo.md(r"""
        ## 4. Storage

        **Einordnung.** Die Daten sind tabellarisch und werden über das Raster verknüpft und
        aggregiert (Joins, Gruppierungen, Anteile). Das spricht für das relationale Modell;
        Dokumenten-, Graph- und Zeitreihenmodelle brächten bei flachen Meldungen keinen Gewinn.
        Nach der Vorlesung handelt es sich um dateibasierte Speicherung (File Storage). Sharding,
        Replikation und CAP spielen keine Rolle, weil alles auf einem Rechner im Batch läuft.

        **Entscheid.** DuckDB als Analysedatenbank, Parquet für die bereinigten Tabellen. Wir
        priorisieren Einfachheit und Reproduzierbarkeit, akzeptieren dafür, dass die Lösung weder
        mehrere gleichzeitige Schreiber noch deutlich grössere Datenmengen trägt, und begrenzen das
        Risiko durch unveränderte Rohdaten, aus denen sich die Datenbank neu aufbauen lässt.

        **Messung** (`src/storage_test.py`, Einzelmessung auf einem Rechner). PostgreSQL mit PostGIS
        haben wir nicht gemessen, es braucht einen Server und wir brauchen keine Raumfunktionen,
        weil die Quadrate aus den LV95-Koordinaten gerechnet werden. Die SQLite-Datei läge mit
        273 MB über der GitHub-Grenze von 100 MB pro Datei.
        """),
        mo.ui.table(storage_table, selection=None),
    ])
    return


@app.cell
def _(as_frame, mo, profile):
    by_year = as_frame(profile, "Abdeckung nach letztem Brutjahr")
    threshold = as_frame(profile, "Abdeckung je Koordinatenschwelle")
    mo.vstack([
        mo.md(r"""
        ## 5. Transformation Teil 1

        ### 5.1 Initiale Analyse der Datengrundlage

        `src/profile_data.py` misst nur und verändert nichts. Zwei Befunde haben Setzungen der
        Konzeption bestimmt.

        **Alter der Referenznachweise.** Die Abdeckung hängt stark vom letzten Brutjahr ab. Bei
        Nachweisen bis 2019 liegt sie unter 18 %, bei Nachweisen ab 2020 bei rund 46 %. Bei
        älteren Nachweisen ist oft nicht mehr klar, ob die Art noch dort brütet. Darum zählt in
        der Hauptanalyse nur der Zeitraum ab 2020.
        """),
        mo.ui.table(by_year.rename(columns={
            "reference_pairs": "Referenzpaare", "ebird_pct": "eBird %",
            "inaturalist_pct": "iNaturalist %", "observation_org_pct": "Observation.org %",
            "any_pct": "alle %"}), selection=None),
        mo.md(r"""
        **Koordinatenungenauigkeit bei iNaturalist.** iNaturalist verschleiert Standorte teils
        grob; eBird liefert die Angabe gar nicht (die Koordinaten sind vorhanden, nur die
        Ungenauigkeit fehlt). Die Tabelle zeigt, wie die Abdeckung bei verschiedenen Schwellen
        reagiert. Der Unterschied zwischen 2'500 und 5'000 m ist klein; wir nehmen 2'500 m.
        """),
        mo.ui.table(threshold.rename(columns={
            "inaturalist_records": "iNaturalist-Meldungen", "ebird_pct": "eBird %",
            "inaturalist_pct": "iNaturalist %", "observation_org_pct": "Observation.org %"}),
            selection=None),
    ])
    return


@app.cell
def _(build_log, mo, pd):
    _p = build_log["parameters"]
    _rows = [
        ("Plattformmeldungen nach Filter (CH, 2020–2024, April–Juli)", build_log["platform_rows_after_filter"]),
        ("davon iNaturalist über 2'500 m Ungenauigkeit entfernt", build_log["inaturalist_rows_too_uncertain"]),
        ("Plattformmeldungen bereinigt", build_log["platform_rows_clean"]),
        ("Referenz: Art/Quadrat-Paare (CH)", build_log["reference_pairs_clean"]),
        ("davon 10-km-Meldungen (markiert, ausgeschlossen)", build_log["reference_pairs_10km"]),
        ("davon letztes Brutjahr vor 2020", build_log["reference_pairs_before_min_year"]),
        ("Referenz: Arten", build_log["reference_species"]),
        ("Quadrate insgesamt", build_log["analysis_cells_total"]),
        ("davon Randquadrate unter 1'000 ha", build_log["landuse_cells_below_threshold"]),
        ("Quadrate der Hauptanalyse", build_log["analysis_cells_main"]),
        ("Referenzpaare der Hauptanalyse", build_log["analysis_reference_pairs_main"]),
    ]
    cleaning_table = pd.DataFrame(_rows, columns=["Schritt", "Anzahl"])
    mo.vstack([
        mo.md(r"""
        ### 5.2 Initiale Datenbereinigung

        `src/build_analysis_table.py` bereinigt nach den Regeln der Konzeption, ohne die Rohdaten
        zu verändern:

        - **Plattformen:** nur die drei Dataset-Keys, Schweiz (LV95-Bbox), 2020–2024, April bis
          Juli, Art und Koordinate vorhanden, iNaturalist bis 2'500 m Ungenauigkeit.
          Beobachterkennungen werden mit einem Salt gehasht, bevor etwas geschrieben wird.
        - **Referenz:** nur Schweiz, Artnamen über `mappings/taxon_mapping.csv` auf die
          Catalogue-of-Life-Namen abgeglichen (16 Arten umbenannt, *Ficedula parva* hat keine
          Plattformmeldung), eine Zeile pro Art und Quadrat.
        - **Landnutzung:** Hektaren je 5-km-Quadrat nach den vier Hauptklassen AS_4
          (Siedlung, Landwirtschaft, bestockt, unproduktiv).
        - **Analysetabelle:** eine Zeile pro Quadrat mit Landnutzungsanteilen, Referenzarten,
          Treffern und Abdeckungsquote je Plattform sowie dem Beobachtungsaufwand (Meldungen und
          Beobachter) als Ersatzmass.
        """),
        mo.ui.table(cleaning_table, selection=None),
    ])
    return


@app.cell
def _(main_cells, mo):
    mo.vstack([
        mo.md(r"""
        ### 5.3 Die Analysetabelle

        Eine Zeile pro Quadrat der Hauptanalyse (Ausschnitt):
        """),
        mo.ui.table(main_cells[[
            "cell_id", "hectares", "share_settlement", "share_agriculture", "share_wooded",
            "share_unproductive", "reference_species", "coverage_ebird", "coverage_inaturalist",
            "coverage_observation_org", "coverage_any", "records", "observers"]].round(3).head(50),
            selection=None, page_size=10),
    ])
    return


@app.cell
def _(mo):
    metric = mo.ui.dropdown(
        options={
            "Abdeckung alle Plattformen": "coverage_any",
            "Abdeckung eBird": "coverage_ebird",
            "Abdeckung iNaturalist": "coverage_inaturalist",
            "Abdeckung Observation.org": "coverage_observation_org",
            "Siedlungsanteil": "share_settlement",
            "Anteil unproduktiv": "share_unproductive",
        },
        value="Abdeckung alle Plattformen", label="Karte zeigt: ")
    return (metric,)


@app.cell
def _(main_cells, metric, mo, plt):
    _fig, _ax = plt.subplots(figsize=(8, 5.2))
    # Koordinaten in km: 2'485 statt 2.485e6 auf den Achsen
    _sc = _ax.scatter(main_cells.e_center / 1000, main_cells.n_center / 1000,
                      c=main_cells[metric.value], s=9, marker="s", cmap="viridis", vmin=0)
    _ax.set_aspect("equal")
    _ax.ticklabel_format(useOffset=False, style="plain")
    _ax.set_xlabel("Ostwert LV95 (km)")
    _ax.set_ylabel("Nordwert LV95 (km)")
    _ax.set_title("5-km-Quadrate der Hauptanalyse")
    _cb = _fig.colorbar(_sc, ax=_ax, shrink=0.8)
    _cb.set_label(getattr(metric, "selected_key", metric.value))
    _fig.tight_layout()
    mo.vstack([
        mo.md(r"""
        ### 5.4 Karte der Quadrate

        Die Karte zeigt die Quadrate der Hauptanalyse nach Wahl der Grösse.
        """),
        metric,
        _fig,
    ])
    return


@app.cell
def _(as_frame, main_cells, mo, plt, res_main):
    _h12 = as_frame(res_main, "H1/H2")
    _fig, _axes = plt.subplots(1, 3, figsize=(13, 4))
    _axes[0].hexbin(main_cells.share_settlement, main_cells.coverage_any, gridsize=30,
                    bins="log", mincnt=1, cmap="viridis")
    _axes[0].set_xlabel("Siedlungsanteil")
    _axes[0].set_ylabel("Abdeckungsquote (alle Plattformen)")
    _axes[0].set_title("H1: Siedlung")
    _axes[1].hexbin(main_cells.share_unproductive, main_cells.coverage_any, gridsize=30,
                    bins="log", mincnt=1, cmap="viridis")
    _axes[1].set_xlabel("Anteil unproduktive Fläche")
    _axes[1].set_title("H2: unproduktiv")
    _axes[2].hexbin(main_cells.records.clip(lower=1), main_cells.coverage_any, gridsize=30,
                    xscale="log", bins="log", mincnt=1, cmap="viridis")
    _axes[2].set_xlabel("Meldungen im Quadrat (log)")
    _axes[2].set_title("Aufwand")
    _fig.tight_layout()
    h1 = _h12.loc["H1 Siedlung"]
    h2 = _h12.loc["H2 unproduktiv"]
    effort = _h12.loc["(zusaetzlich) effort_records"]
    mo.vstack([
        mo.md(rf"""
        ## 6. Hypothesentests

        Grundlage: {len(main_cells):,} Quadrate der Hauptanalyse. Mittlere Abdeckungsquote aller
        Plattformen {main_cells.coverage_any.mean():.1%}.

        ### 6.1 H1 und H2: Spearman-Korrelation

        Die rangbasierte Korrelation braucht keine Annahme über die Verteilung und ist für Anteile
        nahe 0 geeignet. Das Konfidenzintervall folgt Bonett & Wright (2000).

        | | rho | 95 %-KI | n |
        |---|---|---|---|
        | H1 Siedlung | {h1.rho:.3f} | [{h1.ci_low:.3f}; {h1.ci_high:.3f}] | {int(h1.n)} |
        | H2 unproduktiv | {h2.rho:.3f} | [{h2.ci_low:.3f}; {h2.ci_high:.3f}] | {int(h2.n)} |
        | (Aufwand, Meldungen) | {effort.rho:.3f} | [{effort.ci_low:.3f}; {effort.ci_high:.3f}] | {int(effort.n)} |

        Der Siedlungsanteil hängt klar positiv mit der Abdeckung zusammen. Zwischen unproduktiver
        Fläche und Abdeckung finden wir keinen Zusammenhang. Auffällig ist der Aufwand: Die Zahl der
        Meldungen im Quadrat hängt fast perfekt mit der Abdeckung zusammen.
        """),
        _fig,
    ])
    return effort, h1, h2


@app.cell
def _(as_frame, mo, res_main):
    _m1 = as_frame(res_main, "Modell 1")
    _m2 = as_frame(res_main, "Modell 2")
    _fit = as_frame(res_main, "Modellguete")
    mo.vstack([
        mo.md(rf"""
        ### 6.2 Multiple Regression mit Kontrolle des Aufwands

        Landwirtschaft ist die Referenzklasse (die vier Anteile summieren sich auf 1). Die
        Standardfehler sind heteroskedastie-robust (HC3, MacKinnon & White, 1985). Modell 1
        enthält nur die Landnutzung, Modell 2 zusätzlich den Aufwand (Meldungen und Beobachter,
        logarithmiert). R² steigt von {_fit.loc['Modell 1', 'R2']:.3f} auf
        {_fit.loc['Modell 2', 'R2']:.3f}.

        **Modell 1: Landnutzung ohne Kontrolle**
        """),
        mo.ui.table(_m1.round(4).reset_index(names="Term"), selection=None),
        mo.md(r"""
        **Modell 2: Landnutzung mit Aufwand**
        """),
        mo.ui.table(_m2.round(4).reset_index(names="Term"), selection=None),
        mo.md(r"""
        Mit der Kontrolle verschwindet der Effekt des Siedlungsanteils. Die Landnutzung wirkt also
        überwiegend über den Aufwand: Wo mehr Menschen wohnen, wird mehr gemeldet, und mehr
        Meldungen decken mehr Arten ab. Das widerlegt H1 nicht, sondern weist den Aufwand als
        Mediator aus. Beide Modelle werden berichtet.
        """),
    ])
    return


@app.cell
def _(as_frame, entry, main_cells, mo, np, plt, res_main):
    _h3 = entry(res_main, "H3:")
    _slopes = as_frame(res_main, "Steigung")
    _fig, _ax = plt.subplots(figsize=(6.5, 4.2))
    _bins = np.linspace(0, main_cells.share_settlement.quantile(0.98), 9)
    _grp = main_cells.assign(bin=np.digitize(main_cells.share_settlement, _bins))
    _mid = _grp.groupby("bin").share_settlement.mean()
    for _name, _label in [("coverage_ebird", "eBird"), ("coverage_inaturalist", "iNaturalist"),
                          ("coverage_observation_org", "Observation.org")]:
        _ax.plot(_mid.values, _grp.groupby("bin")[_name].mean().values, marker="o", label=_label)
    _ax.set_xlabel("Siedlungsanteil (Klassenmittel)")
    _ax.set_ylabel("mittlere Abdeckungsquote")
    _ax.set_title("Abdeckung nach Siedlungsanteil und Plattform")
    _ax.legend()
    _fig.tight_layout()
    mo.vstack([
        mo.md(rf"""
        ### 6.3 H3: Plattformen im Vergleich

        Modell 3 stapelt je Quadrat eine Zeile pro Plattform (eBird als Referenz, iNaturalist) und
        interagiert die Plattform mit allen Prädiktoren, damit auch der Aufwand je Plattform
        unterschiedlich wirken darf. Die Standardfehler sind nach Quadrat geclustert. Der
        Interaktionsterm Plattform × Siedlung ist die Differenz der Siedlungssteigung:

        **{_h3['coefficient']:+.3f}** [{_h3['ci_low']:.3f}; {_h3['ci_high']:.3f}],
        p = {_h3['p']:.2g} (n = {_h3['n_cells']:,} Quadrate, {_h3['n_rows']:,} Zeilen).

        Getrennte Modelle je Plattform (Aufwand kontrolliert) ergeben diese Steigungen des
        Siedlungsanteils:
        """),
        mo.ui.table(_slopes.round(4).reset_index(names="Plattform"), selection=None),
        mo.md(r"""
        Bei gleichem Aufwand nimmt die Abdeckung von eBird mit dem Siedlungsanteil leicht ab, die
        von iNaturalist zu. Für Observation.org lässt sich kein Zusammenhang nachweisen. Die
        Abbildung zeigt die unkontrollierten Klassenmittel.
        """),
        _fig,
    ])
    return


@app.cell
def _(as_frame, entry, mo, res_main):
    _holm = as_frame(res_main, "Holm-Korrektur")
    _mr = entry(res_main, "Moran's I der Residuen")
    _mc = entry(res_main, "Moran's I der Abdeckungsquote")
    mo.vstack([
        mo.md(rf"""
        ### 6.4 Mehrfachtests und räumliche Autokorrelation

        Über die drei Haupttests wird nach Holm (1979) korrigiert, Signifikanzniveau 5 %.
        """),
        mo.ui.table(_holm.reset_index(names="Test"), selection=None),
        mo.md(rf"""
        **Moran's I** (Rook-Nachbarschaft, zeilenstandardisiert, Permutationstest nach Anselin 1995
        mit {_mr['permutations']} Permutationen): Residuen von Modell 2 **{_mr['morans_i']:.3f}**
        (p = {_mr['p_permutation']}), Abdeckungsquote selbst {_mc['morans_i']:.3f}.
        Benachbarte Quadrate sind demnach nicht unabhängig. Die p-Werte sind vorsichtig zu lesen;
        die Effektstärken mit Konfidenzintervallen tragen die Aussage.
        """),
    ])
    return


@app.cell
def _(as_frame, entry, mo, pd, res_5000m, res_all_years, res_main):
    def summarise(res):
        _base = entry(res, "Datengrundlage")
        _h12 = as_frame(res, "H1/H2")
        _m2 = as_frame(res, "Modell 2")
        _h3 = entry(res, "H3:")
        _mi = entry(res, "Moran's I der Residuen")
        _h1, _h2 = _h12.loc["H1 Siedlung"], _h12.loc["H2 unproduktiv"]
        _s = _m2.loc["share_settlement"]
        return {
            "Quadrate": f"{_base['cells']:,}",
            "Referenzpaare": f"{_base['reference_pairs']:,}",
            "mittlere Abdeckung": f"{_base['coverage_any_mean']:.1%}",
            "H1 rho [KI]": f"{_h1.rho:.3f} [{_h1.ci_low:.3f}; {_h1.ci_high:.3f}]",
            "H2 rho [KI]": f"{_h2.rho:.3f} [{_h2.ci_low:.3f}; {_h2.ci_high:.3f}]",
            "H3 Interaktion [KI]": f"{_h3['coefficient']:+.3f} [{_h3['ci_low']:.3f}; {_h3['ci_high']:.3f}]",
            "Siedlung in Modell 2 [KI]": f"{_s.coefficient:.3f} [{_s.ci_low:.3f}; {_s.ci_high:.3f}]",
            "Moran's I (Residuen)": f"{_mi['morans_i']:.3f}",
        }

    sensitivity = pd.DataFrame({
        "Hauptanalyse (ab 2020, 2'500 m)": summarise(res_main),
        "alle Nachweise": summarise(res_all_years),
        "iNaturalist bis 5'000 m": summarise(res_5000m),
    })
    mo.vstack([
        mo.md(r"""
        ## 7. Sensitivität

        Die zwei Läufe verändern je eine Setzung der Hauptanalyse und schreiben in eigene Ordner
        (`build_out_sens_*`, `analysis_out_sens_*`). Die Aussagen zu H1, H2 und H3 bleiben in allen
        drei Läufen gleich. Die Schwelle für iNaturalist ändert praktisch nichts. Das Referenzalter
        verschiebt vor allem das Niveau der Abdeckung, weil ältere Nachweise häufiger als Lücke
        erscheinen.
        """),
        mo.ui.table(sensitivity.reset_index(names=""), selection=None),
    ])
    return


@app.cell
def _(as_frame, entry, mo, res_main):
    _h12 = as_frame(res_main, "H1/H2")
    _holm = as_frame(res_main, "Holm-Korrektur")
    _m2 = as_frame(res_main, "Modell 2")
    _h3 = entry(res_main, "H3:")
    _slopes = as_frame(res_main, "Steigung")
    _p1 = _holm.loc["H1 (Spearman Siedlung)", "p_holm"]
    _p2 = _holm.loc["H2 (Spearman unproduktiv)", "p_holm"]
    _p3 = _holm.loc["H3 (Interaktion)", "p_holm"]
    _s = _m2.loc["share_settlement"]
    _u = _m2.loc["share_unproductive"]
    mo.md(rf"""
    ## 8. Beantwortung der Forschungsfragen

    **FF1: Hängt die Abdeckungsquote von der Landnutzung ab?**
    Ja, aber nur für den Siedlungsanteil. Je mehr Siedlungsfläche ein Quadrat hat, desto höher ist
    die Abdeckung (H1: rho = {_h12.loc['H1 Siedlung', 'rho']:.2f}, Holm-p = {_p1:.1e}, gestützt).
    Für den Anteil unproduktiver Fläche finden wir keinen Zusammenhang (H2: rho =
    {_h12.loc['H2 unproduktiv', 'rho']:.3f}, Holm-p = {_p2:.2f}, nicht gestützt). Dieser Zusammenhang
    läuft fast vollständig über den Beobachtungsaufwand: Mit Kontrolle der Zahl der Meldungen und
    Beobachter ist der Koeffizient des Siedlungsanteils {_s.coefficient:.3f}
    [{_s.ci_low:.3f}; {_s.ci_high:.3f}] und nicht mehr von null verschieden. Die Landnutzung erklärt
    also, *wo gemeldet wird*, und der Aufwand erklärt, *wie viel abgedeckt wird*. Unter Kontrolle des
    Aufwands ist die Abdeckung in Quadraten mit mehr unproduktiver Fläche sogar etwas höher
    ({_u.coefficient:+.3f} [{_u.ci_low:.3f}; {_u.ci_high:.3f}]), also das Gegenteil von H2. Eine
    Erklärung (weniger Arten, die leichter erfasst werden) haben wir nicht geprüft.

    **FF2: Unterscheiden sich die Plattformen?**
    Ja. Die Abdeckung von iNaturalist hängt stärker vom Siedlungsanteil ab als die von eBird (H3:
    Interaktion {_h3['coefficient']:+.3f} [{_h3['ci_low']:.3f}; {_h3['ci_high']:.3f}], Holm-p =
    {_p3:.1e}, gestützt). Bei gleichem Aufwand steigt die Abdeckung von iNaturalist mit dem
    Siedlungsanteil ({_slopes.loc['inaturalist', 'slope_settlement']:+.3f}), die von eBird sinkt
    leicht ({_slopes.loc['ebird', 'slope_settlement']:+.3f}). Die Abdeckung insgesamt unterscheidet
    sich stark: eBird deckt im Mittel rund 37 % der Referenzpaare ab, iNaturalist und
    Observation.org je rund 5 %.

    **Robustheit.** Die Aussagen bleiben bei einer Schwelle von 5'000 m und bei Verwendung aller
    Referenznachweise gleich (Abschnitt 7).
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 9. Limitationen und Ausblick auf Teil 2

    Die Ergebnisse gelten für die Abdeckung relativ zur Vogelwarte-Referenz, nicht relativ zur
    tatsächlichen Verbreitung.

    - **Referenz nicht unabhängig:** Sie stützt sich auch auf ornitho.ch. Beobachter können auf
      mehreren Plattformen aktiv sein, die Abdeckung wird tendenziell überschätzt.
    - **Kein Zeitverlauf in der Referenz:** Pro Quadrat steht nur das letzte Brutjahr. Die
      Hauptanalyse zählt nur Nachweise ab 2020, was das Problem mindert, aber nicht beseitigt.
    - **Meldung ist kein Brutnachweis:** Eine Meldung in der Brutzeit kann einen Durchzügler oder
      Gast betreffen. Die Abdeckung wird dadurch tendenziell überschätzt.
    - **Aufwand nur angenähert:** GBIF-eBird enthält keine Checklisten. Die Kontrollvariable
      (Meldungen und Beobachter) ist ein Ersatzmass und eng mit dem Ergebnis verknüpft.
    - **Landnutzung zeitlich versetzt:** Die Arealstatistik stammt aus 2013–2020, die Meldungen
      aus 2020–2024.
    - **Raster-Generalisierung:** Die Referenz liegt nur auf 5 km vor. Innerhalb eines Quadrats
      ist keine Aussage möglich.
    - **Räumliche Autokorrelation:** Benachbarte Quadrate sind ähnlich (Moran's I), die p-Werte
      sind vorsichtig zu lesen.
    - **Lineares Modell für Anteile:** Die Abdeckungsquote ist bei iNaturalist und Observation.org
      ein Anteil nahe 0. Die lineare Regression ist dort nur eine Näherung; die Hauptaussagen
      tragen die rangbasierten Spearman-Tests.
    - **Lizenz:** Observation.org und Teile von iNaturalist sind CC BY-NC, eine kommerzielle
      Weiterverwendung ist ausgeschlossen.

    **Ausblick Teil 2.** Auf der Analysetabelle lässt sich ein Modell aufbauen, das die Abdeckung
    eines Quadrats vorhersagt. Vorgeschlagen ist der Vergleich zweier Klassifikationsmodelle
    (Option B). Für die Abdeckungsquote selbst wäre ein binomiales Modell mit der Zahl der
    Referenzarten als Nenner der passendere Ansatz.

    ## Quellen und Daten

    - Wechsler, S., Volet, B. & Schmid, H. (2023). *Swiss National Breeding Bird Databank*.
      Version 1.1. Swiss Ornithological Institute. https://doi.org/10.15468/jujcgr
    - GBIF.org (13. Oktober 2026). *GBIF Occurrence Download*. https://doi.org/10.15468/dl.9qfxn7
    - Bundesamt für Statistik. *Arealstatistik Schweiz* (Standardnomenklatur NOAS04).
      https://www.bfs.admin.ch/bfs/de/home/statistiken/raum-umwelt/erhebungen/area.html
    - Reis, J. & Housley, M. (2022). *Fundamentals of Data Engineering*. O'Reilly Media.
    - Statistische Verfahren: siehe Quellenverzeichnis am Anfang von `notebooks/birdreports.py`.
    """)
    return


if __name__ == "__main__":
    app.run()
