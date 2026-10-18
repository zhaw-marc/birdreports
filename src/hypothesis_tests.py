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

Aufruf:
  python src/hypothesis_tests.py [build_out/analyse_quadrate.parquet] [OUT_DIR]

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

QUELLE = Path(sys.argv[1] if len(sys.argv) > 1 else "build_out/analyse_quadrate.parquet")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "analysis_out")
OUT.mkdir(parents=True, exist_ok=True)

ALPHA = 0.05
PERMUTATIONEN = 999
RNG = np.random.default_rng(20261018)
report = {}


def show(titel, obj):
    print(f"\n=== {titel}")
    print(obj.to_string() if isinstance(obj, (pd.DataFrame, pd.Series)) else obj)
    report[titel] = (json.loads(obj.to_json(orient="split")) if isinstance(obj, pd.DataFrame)
                     else obj)


def spearman(x, y):
    """Spearmans rho mit 95-Prozent-Konfidenzintervall ueber die Fisher-z-Transformation."""
    rho, p = stats.spearmanr(x, y)
    n = len(x)
    se = 1.06 / np.sqrt(n - 3)                       # Bonett & Wright (2000)
    z = np.arctanh(rho)
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    return {"rho": round(float(rho), 3), "ci_unten": round(float(lo), 3),
            "ci_oben": round(float(hi), 3), "p": float(p), "n": int(n)}


def holm(p_werte):
    """Holm-Korrektur (1979): p sortieren, mit (m - i) multiplizieren, monoton halten."""
    namen = list(p_werte)
    p = np.array([p_werte[k] for k in namen], float)
    ordnung = np.argsort(p)
    m = len(p)
    angepasst = np.empty(m)
    bisher = 0.0
    for rang, i in enumerate(ordnung):
        bisher = max(bisher, (m - rang) * p[i])
        angepasst[i] = min(1.0, bisher)
    return {namen[i]: float(angepasst[i]) for i in range(m)}


def koeffizienten(modell, titel):
    ci = modell.conf_int()
    df = pd.DataFrame({"koeffizient": modell.params.round(4),
                       "std_fehler": modell.bse.round(4),
                       "ci_unten": ci[0].round(4), "ci_oben": ci[1].round(4),
                       "t": modell.tvalues.round(2), "p": modell.pvalues})
    show(titel, df)
    return df


def nachbarn(quadrate):
    """Rook-Nachbarschaft auf dem 5-km-Raster: gemeinsame Kante in Ost- oder Nordrichtung."""
    index = {q: i for i, q in enumerate(quadrate)}
    zeilen, spalten = [], []
    for q, i in index.items():
        for nachbar in (q + 1000, q - 1000, q + 1, q - 1):   # Ost, West, Nord, Sued
            j = index.get(nachbar)
            if j is not None:
                zeilen.append(i); spalten.append(j)
    n = len(index)
    W = sparse.csr_matrix((np.ones(len(zeilen)), (zeilen, spalten)), shape=(n, n))
    grad = np.asarray(W.sum(axis=1)).ravel()
    skala = np.divide(1.0, grad, out=np.zeros_like(grad), where=grad > 0)
    return sparse.diags(skala) @ W, grad                     # zeilenstandardisiert


def morans_i(residuen, quadrate, titel):
    """Moran's I der Residuen mit Permutationstest (zweiseitig)."""
    W, grad = nachbarn(list(quadrate))
    z = np.asarray(residuen, float) - np.mean(residuen)

    def I(v):
        return float(v @ (W @ v) / (v @ v))

    beobachtet = I(z)
    null = np.array([I(RNG.permutation(z)) for _ in range(PERMUTATIONEN)])
    erwartet = -1.0 / (len(z) - 1)
    p = (np.sum(np.abs(null - erwartet) >= abs(beobachtet - erwartet)) + 1) / (PERMUTATIONEN + 1)
    ergebnis = {"morans_i": round(beobachtet, 3), "erwartungswert": round(erwartet, 4),
                "p_permutation": round(float(p), 4), "permutationen": PERMUTATIONEN,
                "quadrate_ohne_nachbarn": int((grad == 0).sum())}
    show(titel, ergebnis)
    return ergebnis


# ---------------- Daten ----------------
d = pd.read_parquet(QUELLE)
d = d[d.in_hauptanalyse].copy()
d["log_meldungen"] = np.log1p(d.meldungen)
d["log_beobachter"] = np.log1p(d.beobachter)
show("Datengrundlage", {"quelle": str(QUELLE), "quadrate": len(d),
                        "referenzpaare": int(d.ref_arten.sum()),
                        "abdeckung_alle_drei_mittel": round(float(d.abdeckung_alle_drei.mean()), 3),
                        "abdeckung_alle_drei_median": round(float(d.abdeckung_alle_drei.median()), 3)})
show("Verteilung der Variablen", d[["abdeckung_alle_drei", "abdeckung_ebird", "abdeckung_inaturalist",
                                    "abdeckung_observation_org", "anteil_siedlung",
                                    "anteil_landwirtschaft", "anteil_bestockt", "anteil_unproduktiv",
                                    "meldungen", "beobachter", "ref_arten"]].describe().round(3))

# ---------------- H1 und H2: Spearman ----------------
h1 = spearman(d.anteil_siedlung, d.abdeckung_alle_drei)
h2 = spearman(d.anteil_unproduktiv, d.abdeckung_alle_drei)
weitere = {"landwirtschaft": spearman(d.anteil_landwirtschaft, d.abdeckung_alle_drei),
           "bestockt": spearman(d.anteil_bestockt, d.abdeckung_alle_drei),
           "aufwand_meldungen": spearman(d.log_meldungen, d.abdeckung_alle_drei)}
show("H1/H2: Spearman-Korrelation mit der Abdeckungsquote (alle drei Plattformen)",
     pd.DataFrame({"H1 Siedlung": h1, "H2 unproduktiv": h2, **{f"(zusaetzlich) {k}": v
                                                               for k, v in weitere.items()}}).T)

# ---------------- Multiple Regression (H1 und H2 gemeinsam) ----------------
# Die vier Anteile summieren sich auf 1; Landwirtschaft ist die Referenzklasse und
# wird darum weggelassen. Die Koeffizienten sind Abdeckungsunterschiede in Anteilspunkten,
# wenn eine Flaeche vollstaendig von Landwirtschaft auf die jeweilige Klasse wechselt.
m1 = smf.ols("abdeckung_alle_drei ~ anteil_siedlung + anteil_bestockt + anteil_unproduktiv",
             data=d).fit(cov_type="HC3")
koeffizienten(m1, "Modell 1: Landnutzung ohne Kontrolle (HC3)")
m2 = smf.ols("abdeckung_alle_drei ~ anteil_siedlung + anteil_bestockt + anteil_unproduktiv"
             " + log_meldungen + log_beobachter", data=d).fit(cov_type="HC3")
koeffizienten(m2, "Modell 2: Landnutzung mit Beobachtungsaufwand als Kontrolle (HC3)")
show("Modellguete", pd.DataFrame({
    "Modell 1": {"n": int(m1.nobs), "R2": round(m1.rsquared, 3), "R2_adj": round(m1.rsquared_adj, 3)},
    "Modell 2": {"n": int(m2.nobs), "R2": round(m2.rsquared, 3), "R2_adj": round(m2.rsquared_adj, 3)},
}).T)

# ---------------- H3: Interaktion Plattform x Siedlung ----------------
# Lange Form: je Quadrat eine Zeile pro Plattform, eBird ist die Referenzkategorie.
lang = pd.concat([
    d.assign(plattform=pl, abdeckung=d[f"abdeckung_{pl}"],
             log_meldungen_pl=np.log1p(d[f"meldungen_{pl}"]),
             log_beobachter_pl=np.log1p(d[f"beobachter_{pl}"]))
    for pl in ["ebird", "inaturalist"]], ignore_index=True)
lang["plattform"] = pd.Categorical(lang.plattform, categories=["ebird", "inaturalist"])
# Die Plattform wird mit allen Pradiktoren interagiert, nicht nur mit dem Siedlungsanteil.
# Nur so darf auch der Aufwand je Plattform unterschiedlich wirken; das ist noetig, weil die
# Abdeckung von eBird (Mittel 0,31) und iNaturalist (0,05) auf ganz verschiedenem Niveau liegt.
# Mit einem gemeinsamen Aufwandskoeffizienten kehrt sich das Vorzeichen der Interaktion um.
m3 = smf.ols("abdeckung ~ plattform * (anteil_siedlung + anteil_bestockt + anteil_unproduktiv"
             " + log_meldungen_pl + log_beobachter_pl)", data=lang
             ).fit(cov_type="cluster", cov_kwds={"groups": lang.quadrat})
k3 = koeffizienten(m3, "Modell 3: H3, Plattform x Landnutzung und Aufwand (geclustert nach Quadrat)")
term = "plattform[T.inaturalist]:anteil_siedlung"
h3 = {"koeffizient": float(m3.params[term]), "ci_unten": float(m3.conf_int().loc[term, 0]),
      "ci_oben": float(m3.conf_int().loc[term, 1]), "p": float(m3.pvalues[term]),
      "n_zeilen": int(m3.nobs), "n_quadrate": int(lang.quadrat.nunique())}
show("H3: Interaktionsterm (Differenz der Siedlungssteigung iNaturalist minus eBird)",
     {k: (float(f"{v:.4g}") if isinstance(v, float) else v) for k, v in h3.items()})

# Zum Vergleich getrennte Steigungen je Plattform.
getrennt = {}
for pl in ["ebird", "inaturalist", "observation_org"]:
    mp = smf.ols(f"abdeckung_{pl} ~ anteil_siedlung + anteil_bestockt + anteil_unproduktiv"
                 f" + np.log1p(meldungen_{pl}) + np.log1p(beobachter_{pl})", data=d).fit(cov_type="HC3")
    ci = mp.conf_int().loc["anteil_siedlung"]
    getrennt[pl] = {"steigung_siedlung": round(float(mp.params["anteil_siedlung"]), 4),
                    "ci_unten": round(float(ci[0]), 4), "ci_oben": round(float(ci[1]), 4),
                    "p": float(mp.pvalues["anteil_siedlung"]), "R2": round(mp.rsquared, 3)}
show("Steigung des Siedlungsanteils je Plattform (eigene Modelle, HC3)", pd.DataFrame(getrennt).T)

# ---------------- Holm-Korrektur ueber die drei primaeren Tests ----------------
roh = {"H1 (Spearman Siedlung)": h1["p"], "H2 (Spearman unproduktiv)": h2["p"],
       "H3 (Interaktion)": h3["p"]}
korrigiert = holm(roh)
show("Holm-Korrektur ueber die drei primaeren Tests", pd.DataFrame({
    "p_roh": roh, "p_holm": korrigiert,
    "signifikant_5%": {k: bool(v < ALPHA) for k, v in korrigiert.items()}}))

# ---------------- Raeumliche Autokorrelation ----------------
moran_m2 = morans_i(m2.resid, d.quadrat, "Moran's I der Residuen von Modell 2")
moran_roh = morans_i(d.abdeckung_alle_drei - d.abdeckung_alle_drei.mean(), d.quadrat,
                     "Moran's I der Abdeckungsquote selbst (zum Vergleich)")

# ---------------- Antwort auf die Forschungsfragen ----------------
def richtung(koef, p):
    if p >= ALPHA:
        return "kein Zusammenhang nachweisbar"
    return "positiver Zusammenhang" if koef > 0 else "negativer Zusammenhang"

antwort = {
    "FF1 (Landnutzung)": {
        "H1 Siedlung": f"rho = {h1['rho']} [{h1['ci_unten']}, {h1['ci_oben']}], "
                       f"p_holm = {korrigiert['H1 (Spearman Siedlung)']:.3g} -> "
                       f"{richtung(h1['rho'], korrigiert['H1 (Spearman Siedlung)'])}",
        "H2 unproduktiv": f"rho = {h2['rho']} [{h2['ci_unten']}, {h2['ci_oben']}], "
                          f"p_holm = {korrigiert['H2 (Spearman unproduktiv)']:.3g} -> "
                          f"{richtung(h2['rho'], korrigiert['H2 (Spearman unproduktiv)'])}",
        "mit Kontrolle des Aufwands": "siehe Modell 2: Koeffizient Siedlung "
                                      f"{m2.params['anteil_siedlung']:.3f} "
                                      f"[{m2.conf_int().loc['anteil_siedlung', 0]:.3f}, "
                                      f"{m2.conf_int().loc['anteil_siedlung', 1]:.3f}], "
                                      f"unproduktiv {m2.params['anteil_unproduktiv']:.3f} "
                                      f"[{m2.conf_int().loc['anteil_unproduktiv', 0]:.3f}, "
                                      f"{m2.conf_int().loc['anteil_unproduktiv', 1]:.3f}]",
        "Hinweis zur Kontrolle": "Der Aufwand allein erklaert die Abdeckung fast vollstaendig "
                                 f"(Spearman log_meldungen {weitere['aufwand_meldungen']['rho']}, "
                                 f"R2 von Modell 1 {m1.rsquared:.3f} auf {m2.rsquared:.3f}). "
                                 "Die Landnutzung wirkt damit weitgehend ueber den Aufwand. "
                                 "Modell 2 schaetzt den Rest nach Herausrechnen des Aufwands und "
                                 "ist nicht als Widerlegung von H1 zu lesen, sondern als Hinweis "
                                 "auf einen Mediator.",
    },
    "FF2 (Plattformen)": {
        "H3 Interaktion": f"{h3['koeffizient']:.3f} [{h3['ci_unten']:.3f}, {h3['ci_oben']:.3f}], "
                          f"p_holm = {korrigiert['H3 (Interaktion)']:.3g}. Der Wert ist die "
                          "Differenz der Siedlungssteigung (iNaturalist minus eBird); positiv "
                          "stuetzt H3.",
        "H3 gestuetzt": bool(korrigiert["H3 (Interaktion)"] < ALPHA and h3["koeffizient"] > 0),
        "Steigungen einzeln": {k: v["steigung_siedlung"] for k, v in getrennt.items()},
    },
    "Limitation": f"Moran's I der Residuen von Modell 2: {moran_m2['morans_i']} "
                  f"(p = {moran_m2['p_permutation']}). Benachbarte Quadrate sind nicht unabhaengig; "
                  "die p-Werte sind entsprechend vorsichtig zu lesen.",
}
show("Antwort auf die Forschungsfragen", antwort)

(OUT / "hypothesis_tests.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
print(f"\nGespeichert: {OUT / 'hypothesis_tests.json'}")
