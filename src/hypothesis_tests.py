"""Transformation Teil 1, Schritt 3: Hypothesentests H1 bis H3.

Arbeitet auf der Analysetabelle aus src/build_analysis_table.py (eine Zeile pro
5-km-Quadrat) und testet die drei Hypothesen der Konzeption:

  H1  Je hoeher der Siedlungsanteil, desto hoeher die Abdeckungsquote.
  H2  Je hoeher der Anteil unproduktiver Flaeche, desto niedriger die Abdeckungsquote.
  H3  Die Abdeckungsquote von iNaturalist haengt staerker vom Siedlungsanteil ab
      als die von eBird (Interaktionsterm Plattform x Siedlung).

Vorgehen wie in der Konzeption festgelegt: Spearman-Korrelation einzeln fuer H1 und H2,
multiple Regression mit Landwirtschaft als Referenzklasse und dem Beobachtungsaufwand
als Kontrollvariable, Interaktionsterm fuer H3, Holm-Korrektur ueber die drei primaeren
Tests, Effektstaerken mit 95-Prozent-Konfidenzintervallen, und Moran's I auf den
Residuen zur Pruefung der raeumlichen Autokorrelation.

Bezeichner und Spaltennamen sind englisch, Kommentare und die Titel der Ausgabetabellen
deutsch.

Die Parameter der Analysetabelle (Referenzalter, Schwelle fuer iNaturalist) stehen im
build_log.json neben der Tabelle und werden mit ausgegeben. Sensitivitaetslaeufe entstehen,
indem build_analysis_table.py mit anderen Parametern in einen eigenen Ordner schreibt und
dieses Skript auf die dortige Tabelle zeigt.

Die Abdeckungsquote ist ein Anteil nahe 0 (Plattformen ausser eBird) und die Modelle sind
linear. Das ist eine bewusste Vereinfachung fuer Teil 1; die Grenzen stehen in der Konzeption
unter den Limitationen. H1 und H2 stuetzen sich primaer auf die rangbasierte Spearman-Korrelation.

Aufruf:
  python src/hypothesis_tests.py [build_out/analysis_cells.parquet] [OUT_DIR]

Quellen:
  Holm, S. (1979). A simple sequentially rejective multiple test procedure.
    Scandinavian Journal of Statistics, 6(2), 65-70.
  Bonett, D. G. & Wright, T. A. (2000). Sample size requirements for estimating
    Pearson, Kendall and Spearman correlations. Psychometrika, 65, 23-28.
    (Standardfehler 1.06/sqrt(n-3) fuer das Konfidenzintervall von Spearmans rho.)
  Moran, P. A. P. (1950). Notes on continuous stochastic phenomena. Biometrika, 37, 17-23.
  Permutationstest fuer Moran's I nach Anselin, L. (1995). Local indicators of spatial
    association - LISA. Geographical Analysis, 27(2), 93-115.
  Heteroskedastie-robuste Standardfehler (HC3) nach MacKinnon, J. G. & White, H. (1985).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import sparse, stats

SOURCE = Path(sys.argv[1] if len(sys.argv) > 1 else "build_out/analysis_cells.parquet")
OUT_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else "analysis_out")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALPHA = 0.05
PERMUTATIONS = 999
RNG = np.random.default_rng(20261018)
report = {}


def show(title, obj):
    print(f"\n=== {title}")
    print(obj.to_string() if isinstance(obj, (pd.DataFrame, pd.Series)) else obj)
    report[title] = (json.loads(obj.to_json(orient="split"))
                     if isinstance(obj, pd.DataFrame) else obj)


def spearman(x, y):
    """Spearmans rho mit 95-Prozent-Konfidenzintervall ueber die Fisher-z-Transformation."""
    rho, p = stats.spearmanr(x, y)
    n = len(x)
    se = 1.06 / np.sqrt(n - 3)                       # Bonett & Wright (2000)
    z = np.arctanh(rho)
    low, high = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    return {"rho": round(float(rho), 3), "ci_low": round(float(low), 3),
            "ci_high": round(float(high), 3), "p": float(p), "n": int(n)}


def holm(p_values):
    """Holm-Korrektur (1979): p sortieren, mit (m - i) multiplizieren, monoton halten."""
    names = list(p_values)
    p = np.array([p_values[k] for k in names], float)
    order = np.argsort(p)
    m = len(p)
    adjusted = np.empty(m)
    running_max = 0.0
    for rank, i in enumerate(order):
        running_max = max(running_max, (m - rank) * p[i])
        adjusted[i] = min(1.0, running_max)
    return {names[i]: float(adjusted[i]) for i in range(m)}


def coefficients(model, title):
    ci = model.conf_int()
    frame = pd.DataFrame({"coefficient": model.params.round(4),
                          "std_error": model.bse.round(4),
                          "ci_low": ci[0].round(4), "ci_high": ci[1].round(4),
                          "t": model.tvalues.round(2), "p": model.pvalues})
    show(title, frame)
    return frame


def neighbours(cells):
    """Rook-Nachbarschaft auf dem 5-km-Raster: gemeinsame Kante in Ost- oder Nordrichtung."""
    index = {cell: i for i, cell in enumerate(cells)}
    rows, cols = [], []
    for cell, i in index.items():
        for neighbour in (cell + 1000, cell - 1000, cell + 1, cell - 1):   # Ost, West, Nord, Sued
            j = index.get(neighbour)
            if j is not None:
                rows.append(i); cols.append(j)
    n = len(index)
    weights = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    degree = np.asarray(weights.sum(axis=1)).ravel()
    scale = np.divide(1.0, degree, out=np.zeros_like(degree), where=degree > 0)
    return sparse.diags(scale) @ weights, degree                           # zeilenstandardisiert


def morans_i(residuals, cells, title):
    """Moran's I der Residuen mit Permutationstest (zweiseitig)."""
    weights, degree = neighbours(list(cells))
    z = np.asarray(residuals, float) - np.mean(residuals)

    def statistic(values):
        return float(values @ (weights @ values) / (values @ values))

    observed = statistic(z)
    permuted = np.array([statistic(RNG.permutation(z)) for _ in range(PERMUTATIONS)])
    expected = -1.0 / (len(z) - 1)
    p = (np.sum(np.abs(permuted - expected) >= abs(observed - expected)) + 1) / (PERMUTATIONS + 1)
    result = {"morans_i": round(observed, 3), "expected": round(expected, 4),
              "p_permutation": round(float(p), 4), "permutations": PERMUTATIONS,
              "cells_without_neighbours": int((degree == 0).sum())}
    show(title, result)
    return result


# ---------------- Daten ----------------
cells = pd.read_parquet(SOURCE)
cells = cells[cells.in_main_analysis].copy()
cells["log_records"] = np.log1p(cells.records)
cells["log_observers"] = np.log1p(cells.observers)
log_path = SOURCE.parent / "build_log.json"
parameters = (json.loads(log_path.read_text()).get("parameters", {}) if log_path.exists() else {})
show("Datengrundlage", {"source": str(SOURCE), "parameters": parameters, "cells": len(cells),
                        "reference_pairs": int(cells.reference_species.sum()),
                        "coverage_any_mean": round(float(cells.coverage_any.mean()), 3),
                        "coverage_any_median": round(float(cells.coverage_any.median()), 3)})
show("Verteilung der Variablen",
     cells[["coverage_any", "coverage_ebird", "coverage_inaturalist", "coverage_observation_org",
            "share_settlement", "share_agriculture", "share_wooded", "share_unproductive",
            "records", "observers", "reference_species"]].describe().round(3))

# ---------------- H1 und H2: Spearman ----------------
h1 = spearman(cells.share_settlement, cells.coverage_any)
h2 = spearman(cells.share_unproductive, cells.coverage_any)
additional = {"agriculture": spearman(cells.share_agriculture, cells.coverage_any),
              "wooded": spearman(cells.share_wooded, cells.coverage_any),
              "effort_records": spearman(cells.log_records, cells.coverage_any)}
show("H1/H2: Spearman-Korrelation mit der Abdeckungsquote (alle drei Plattformen)",
     pd.DataFrame({"H1 Siedlung": h1, "H2 unproduktiv": h2,
                   **{f"(zusaetzlich) {k}": v for k, v in additional.items()}}).T)

# ---------------- Multiple Regression (H1 und H2 gemeinsam) ----------------
# Die vier Anteile summieren sich auf 1; agriculture ist die Referenzklasse und wird
# darum weggelassen. Die Koeffizienten sind Abdeckungsunterschiede in Anteilspunkten,
# wenn eine Flaeche vollstaendig von Landwirtschaft auf die jeweilige Klasse wechselt.
model_1 = smf.ols("coverage_any ~ share_settlement + share_wooded + share_unproductive",
                  data=cells).fit(cov_type="HC3")
coefficients(model_1, "Modell 1: Landnutzung ohne Kontrolle (HC3)")
model_2 = smf.ols("coverage_any ~ share_settlement + share_wooded + share_unproductive"
                  " + log_records + log_observers", data=cells).fit(cov_type="HC3")
coefficients(model_2, "Modell 2: Landnutzung mit Beobachtungsaufwand als Kontrolle (HC3)")
show("Modellguete", pd.DataFrame({
    "Modell 1": {"n": int(model_1.nobs), "R2": round(model_1.rsquared, 3),
                 "R2_adj": round(model_1.rsquared_adj, 3)},
    "Modell 2": {"n": int(model_2.nobs), "R2": round(model_2.rsquared, 3),
                 "R2_adj": round(model_2.rsquared_adj, 3)}}).T)

# ---------------- H3: Interaktion Plattform x Siedlung ----------------
# Lange Form: je Quadrat eine Zeile pro Plattform, eBird ist die Referenzkategorie.
# Die Plattform wird mit allen Praediktoren interagiert, nicht nur mit dem Siedlungsanteil.
# Nur so darf auch der Aufwand je Plattform unterschiedlich wirken; das ist noetig, weil die
# Abdeckung von eBird und iNaturalist auf ganz verschiedenem Niveau liegt.
# Mit einem gemeinsamen Aufwandskoeffizienten kehrt sich das Vorzeichen der Interaktion um.
long = pd.concat([
    cells.assign(platform=name, coverage=cells[f"coverage_{name}"],
                 log_records_platform=np.log1p(cells[f"records_{name}"]),
                 log_observers_platform=np.log1p(cells[f"observers_{name}"]))
    for name in ["ebird", "inaturalist"]], ignore_index=True)
long["platform"] = pd.Categorical(long.platform, categories=["ebird", "inaturalist"])
model_3 = smf.ols("coverage ~ platform * (share_settlement + share_wooded + share_unproductive"
                  " + log_records_platform + log_observers_platform)", data=long
                  ).fit(cov_type="cluster", cov_kwds={"groups": long.cell_id})
coefficients(model_3, "Modell 3: H3, Plattform x Landnutzung und Aufwand (geclustert nach Quadrat)")
term = "platform[T.inaturalist]:share_settlement"
h3 = {"coefficient": float(model_3.params[term]),
      "ci_low": float(model_3.conf_int().loc[term, 0]),
      "ci_high": float(model_3.conf_int().loc[term, 1]), "p": float(model_3.pvalues[term]),
      "n_rows": int(model_3.nobs), "n_cells": int(long.cell_id.nunique())}
show("H3: Interaktionsterm (Differenz der Siedlungssteigung iNaturalist minus eBird)",
     {k: (float(f"{v:.4g}") if isinstance(v, float) else v) for k, v in h3.items()})

# Zum Vergleich getrennte Steigungen je Plattform.
separate = {}
for name in ["ebird", "inaturalist", "observation_org"]:
    model_p = smf.ols(f"coverage_{name} ~ share_settlement + share_wooded + share_unproductive"
                      f" + np.log1p(records_{name}) + np.log1p(observers_{name})",
                      data=cells).fit(cov_type="HC3")
    ci = model_p.conf_int().loc["share_settlement"]
    separate[name] = {"slope_settlement": round(float(model_p.params["share_settlement"]), 4),
                      "ci_low": round(float(ci[0]), 4), "ci_high": round(float(ci[1]), 4),
                      "p": float(model_p.pvalues["share_settlement"]),
                      "R2": round(model_p.rsquared, 3)}
show("Steigung des Siedlungsanteils je Plattform (eigene Modelle, HC3)", pd.DataFrame(separate).T)

# ---------------- Holm-Korrektur ueber die drei primaeren Tests ----------------
raw_p = {"H1 (Spearman Siedlung)": h1["p"], "H2 (Spearman unproduktiv)": h2["p"],
         "H3 (Interaktion)": h3["p"]}
adjusted_p = holm(raw_p)
show("Holm-Korrektur ueber die drei primaeren Tests", pd.DataFrame({
    "p_raw": raw_p, "p_holm": adjusted_p,
    "signifikant_5%": {k: bool(v < ALPHA) for k, v in adjusted_p.items()}}))

# ---------------- Raeumliche Autokorrelation ----------------
moran_model_2 = morans_i(model_2.resid, cells.cell_id, "Moran's I der Residuen von Modell 2")
moran_raw = morans_i(cells.coverage_any - cells.coverage_any.mean(), cells.cell_id,
                     "Moran's I der Abdeckungsquote selbst (zum Vergleich)")


# ---------------- Antwort auf die Forschungsfragen ----------------
def direction(coefficient, p):
    if p >= ALPHA:
        return "kein Zusammenhang nachweisbar"
    return "positiver Zusammenhang" if coefficient > 0 else "negativer Zusammenhang"


answer = {
    "FF1 (Landnutzung)": {
        "H1 Siedlung": f"rho = {h1['rho']} [{h1['ci_low']}, {h1['ci_high']}], "
                       f"p_holm = {adjusted_p['H1 (Spearman Siedlung)']:.3g} -> "
                       f"{direction(h1['rho'], adjusted_p['H1 (Spearman Siedlung)'])}",
        "H2 unproduktiv": f"rho = {h2['rho']} [{h2['ci_low']}, {h2['ci_high']}], "
                          f"p_holm = {adjusted_p['H2 (Spearman unproduktiv)']:.3g} -> "
                          f"{direction(h2['rho'], adjusted_p['H2 (Spearman unproduktiv)'])}",
        "mit Kontrolle des Aufwands": "siehe Modell 2: Koeffizient Siedlung "
                                      f"{model_2.params['share_settlement']:.3f} "
                                      f"[{model_2.conf_int().loc['share_settlement', 0]:.3f}, "
                                      f"{model_2.conf_int().loc['share_settlement', 1]:.3f}], "
                                      f"unproduktiv {model_2.params['share_unproductive']:.3f} "
                                      f"[{model_2.conf_int().loc['share_unproductive', 0]:.3f}, "
                                      f"{model_2.conf_int().loc['share_unproductive', 1]:.3f}]",
        "Hinweis zur Kontrolle": "Der Aufwand allein erklaert die Abdeckung fast vollstaendig "
                                 f"(Spearman log_records {additional['effort_records']['rho']}, "
                                 f"R2 von Modell 1 {model_1.rsquared:.3f} auf "
                                 f"{model_2.rsquared:.3f}). Die Landnutzung wirkt damit "
                                 "weitgehend ueber den Aufwand. Modell 2 schaetzt den Rest nach "
                                 "Herausrechnen des Aufwands und ist nicht als Widerlegung von "
                                 "H1 zu lesen, sondern als Hinweis auf einen Mediator.",
    },
    "FF2 (Plattformen)": {
        "H3 Interaktion": f"{h3['coefficient']:.3f} [{h3['ci_low']:.3f}, {h3['ci_high']:.3f}], "
                          f"p_holm = {adjusted_p['H3 (Interaktion)']:.3g}. Der Wert ist die "
                          "Differenz der Siedlungssteigung (iNaturalist minus eBird); positiv "
                          "stuetzt H3.",
        "H3 gestuetzt": bool(adjusted_p["H3 (Interaktion)"] < ALPHA and h3["coefficient"] > 0),
        "Steigungen einzeln": {k: v["slope_settlement"] for k, v in separate.items()},
    },
    "Modellgrenze": "Die Abdeckungsquote ist ein Anteil, bei iNaturalist und Observation.org "
                    "nahe 0. Die lineare Regression ist dafuer nur eine Naeherung; primaer "
                    "tragen die rangbasierten Spearman-Tests. Ein binomiales Modell ist fuer "
                    "Teil 2 vorgesehen.",
    "Limitation": f"Moran's I der Residuen von Modell 2: {moran_model_2['morans_i']} "
                  f"(p = {moran_model_2['p_permutation']}). Benachbarte Quadrate sind nicht "
                  "unabhaengig; die p-Werte sind entsprechend vorsichtig zu lesen.",
}
show("Antwort auf die Forschungsfragen", answer)

(OUT_DIR / "hypothesis_tests.json").write_text(
    json.dumps(report, indent=1, ensure_ascii=False, default=str))
print(f"\nGespeichert: {OUT_DIR / 'hypothesis_tests.json'}")
