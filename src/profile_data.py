"""Initiale Analyse der Datengrundlage (Transformation Teil 1, Schritt 1).

Misst nur, veraendert keine Daten. Alle Schwellen der Konzeption werden hier mit Zahlen
belegt: Koordinatenungenauigkeit, Randquadrate, Brutzeit, Artabgleich, erste Abdeckung.

Aufruf:
  python src/profile_data.py AREAL.csv PLATTFORM.csv VOGELWARTE/occurrence.txt mappings/taxon_mapping.csv [OUT_DIR]
Abhaengigkeiten: duckdb, pandas, pyproj  (pip install pyproj)
NICHT an den echten Daten getestet.
"""
import csv, json, sys
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from pyproj import Transformer

AREAL, PLAT, REF, MAP = sys.argv[1:5]
OUT = Path(sys.argv[5] if len(sys.argv) > 5 else "profile_out"); OUT.mkdir(exist_ok=True)
KEYS = {"4fa7b334-ce0d-4e88-aaae-2e0c138d049e": "ebird",
        "8a863029-f435-446a-821e-275f4f641165": "observation_org",
        "50c9509d-22c7-4a22-a47d-8c48425ef4a7": "inaturalist"}
TO_LV95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)
BBOX = (2485000, 2834000, 1075000, 1296000)   # grobe Ausdehnung der Schweiz in LV95
report = {}


def show(title, df):
    print(f"\n=== {title}"); print(df.to_string()); report[title] = json.loads(df.to_json(orient="split"))


def add_cell(df):
    e, n = TO_LV95.transform(df.decimalLongitude.to_numpy(float), df.decimalLatitude.to_numpy(float))
    df["E"], df["N"] = e, n
    ok = np.isfinite(e) & np.isfinite(n)
    df["cell"] = np.where(ok, np.floor(np.nan_to_num(e) / 5000) * 1000 + np.floor(np.nan_to_num(n) / 5000), -1).astype("int64")
    df["in_ch"] = ok & (e >= BBOX[0]) & (e <= BBOX[1]) & (n >= BBOX[2]) & (n <= BBOX[3])
    return df


# ---------------- Plattformdaten ----------------
con = duckdb.connect()
cols = ("datasetKey, species, decimalLatitude, decimalLongitude, coordinateUncertaintyInMeters, "
        "year, month, individualCount, recordedBy, basisOfRecord, license")
plat = con.execute(f"SELECT {cols} FROM read_csv('{PLAT}', delim='\\t', quote='', header=true, "
                   f"ignore_errors=true, sample_size=-1)").df()
plat["plattform"] = plat.datasetKey.map(KEYS).fillna("andere")
plat = add_cell(plat)
g = plat.groupby("plattform")
unc = g.coordinateUncertaintyInMeters
tab = pd.DataFrame({
    "zeilen": g.size(),
    "ohne_koordinate": g.decimalLatitude.apply(lambda s: int(s.isna().sum())),
    "ohne_art": g.species.apply(lambda s: int(s.isna().sum())),
    "ausserhalb_CH_bbox": g.in_ch.apply(lambda s: int((~s).sum())),
    "ohne_anzahl_%": g.individualCount.apply(lambda s: round(s.isna().mean() * 100, 1)),
    "beobachter_verschieden": g.recordedBy.nunique(),
    "ohne_beobachter_%": g.recordedBy.apply(lambda s: round(s.isna().mean() * 100, 1)),
    "apr_jul_%": g.month.apply(lambda s: round(s.between(4, 7).mean() * 100, 1)),
})
show("Plattformen: Grunddaten", tab)
show("Plattformen: Koordinatenungenauigkeit (m)", pd.DataFrame({
    "fehlt_%": unc.apply(lambda s: round(s.isna().mean() * 100, 1)),
    "median": unc.median(), "p90": unc.quantile(0.9),
    ">1000_%": unc.apply(lambda s: round((s > 1000).mean() * 100, 2)),
    ">2500_%": unc.apply(lambda s: round((s > 2500).mean() * 100, 2)),
    ">5000_%": unc.apply(lambda s: round((s > 5000).mean() * 100, 2))}))
show("Plattformen: Meldungen pro Jahr", pd.crosstab(plat.plattform, plat.year))
show("Plattformen: Meldungen pro Monat", pd.crosstab(plat.plattform, plat.month))
show("Plattformen: Lizenzen", pd.crosstab(plat.plattform, plat.license))

P = plat[plat.plattform.isin(KEYS.values()) & plat.in_ch & plat.species.notna()
         & plat.year.between(2020, 2024) & plat.month.between(4, 7)].copy()
print(f"\nPlattformdaten fuer die Analyse (CH, 2020-2024, April-Juli, mit Art): {len(P)}")
report["plattform_analysezeilen"] = len(P)

# ---------------- Referenz ----------------
ref = pd.read_csv(REF, sep="\t", low_memory=False, usecols=[
    "countryCode", "genus", "specificEpithet", "year", "decimalLatitude", "decimalLongitude",
    "coordinateUncertaintyInMeters"])
ref = ref[ref.countryCode == "CH"].copy()
m = pd.read_csv(MAP)
mapping = {a: b for a, b in zip(m.vogelwarte_name, m.col_name) if isinstance(b, str) and b}
ref["species"] = (ref.genus + " " + ref.specificEpithet).map(lambda n: mapping.get(n, n))
ref = add_cell(ref)
off = ((ref[ref.coordinateUncertaintyInMeters == 3535].E % 5000) - 2500).abs()
print(f"\nReferenz CH: {len(ref)} Zeilen, {ref.species.nunique()} Arten, {ref.cell.nunique()} Quadrate")
print(f"Rasterpruefung: Median Abweichung der Quadratmitte {off.median():.1f} m (erwartet nahe 0)")
report["referenz"] = {"zeilen": len(ref), "arten": int(ref.species.nunique()), "quadrate": int(ref.cell.nunique()),
                      "raster_abweichung_median_m": float(off.median())}
show("Referenz: Koordinatenungenauigkeit", ref.coordinateUncertaintyInMeters.value_counts().to_frame("zeilen"))
show("Referenz: letztes Brutjahr (Jahrzehnte)", pd.cut(ref.year, [0, 1999, 2009, 2019, 2030],
     labels=["bis 1999", "2000-2009", "2010-2019", "ab 2020"]).value_counts().sort_index().to_frame("zeilen"))
per_cell = ref.groupby("cell").species.nunique()
show("Referenz: Arten pro Quadrat", per_cell.describe().round(1).to_frame("wert"))
show("Referenz: doppelte Art/Quadrat-Paare", pd.DataFrame({"doppelt": [int(ref.duplicated(["species", "cell"]).sum())]}))
R = ref[ref.coordinateUncertaintyInMeters != 7070]

# ---------------- Arealstatistik ----------------
cells = con.execute(f"""SELECT (E_COORD//5000)*1000 + (N_COORD//5000) AS cell, COUNT(*) AS n_ha,
    SUM((AS_4=1)::INT) AS siedlung, SUM((AS_4=2)::INT) AS landwirtschaft,
    SUM((AS_4=3)::INT) AS bestockt, SUM((AS_4=4)::INT) AS unproduktiv
    FROM read_csv('{AREAL}', delim=';', header=true) GROUP BY 1""").df()
for c in ["siedlung", "landwirtschaft", "bestockt", "unproduktiv"]:
    cells[c + "_anteil"] = cells[c] / cells.n_ha
show("Arealstatistik: Hektaren pro 5-km-Quadrat", cells.n_ha.describe().round(1).to_frame("wert"))
small = cells[cells.n_ha < 1000]
print(f"\nQuadrate gesamt: {len(cells)}, davon unter 1000 ha: {len(small)}")
report["areal"] = {"quadrate": len(cells), "unter_1000_ha": len(small)}
ok_cells = set(cells[cells.n_ha >= 1000].cell)
ref_cells = set(R.cell)
print(f"Referenzquadrate (ohne 10-km-Zeilen): {len(ref_cells)}; ohne Arealstatistik: {len(ref_cells - set(cells.cell))}; "
      f"davon unter 1000 ha: {len(ref_cells & set(small.cell))}")
report["quadrate"] = {"referenz": len(ref_cells), "ohne_areal": len(ref_cells - set(cells.cell)),
                      "unter_1000_ha": len(ref_cells & set(small.cell))}
print(f"Plattformquadrate mit Meldungen: {P.cell.nunique()}; davon nicht in der Referenz: {len(set(P.cell) - ref_cells)}")

# ---------------- Artabgleich und erste Abdeckung (Vorschau, keine Hypothesentests) ----------------
ref_species = set(R.species)
rows = []
for pl, d in P.groupby("plattform"):
    rows.append({"plattform": pl, "meldungen": len(d),
                 "anteil_art_in_referenz_%": round(d.species.isin(ref_species).mean() * 100, 1)})
show("Plattformen: Meldungen mit Art aus der Referenz", pd.DataFrame(rows).set_index("plattform"))

pairs = R[R.cell.isin(ok_cells)][["species", "cell"]].drop_duplicates()
res = {}
for pl, d in P.groupby("plattform"):
    hit = pairs.merge(d[["species", "cell"]].drop_duplicates(), on=["species", "cell"])
    res[pl] = round(len(hit) / len(pairs) * 100, 1)
hit_all = pairs.merge(P[["species", "cell"]].drop_duplicates(), on=["species", "cell"])
res["alle_drei"] = round(len(hit_all) / len(pairs) * 100, 1)
show("Erste Abdeckung (Anteil Art/Quadrat-Paare der Referenz mit Meldung, %)",
     pd.DataFrame({"abdeckung_%": res, "referenzpaare": len(pairs)}))
cov = hit_all.groupby("cell").size().reindex(pairs.cell.unique(), fill_value=0) / pairs.groupby("cell").size()
show("Abdeckungsquote pro Quadrat (alle drei), Verteilung", (cov * 100).describe().round(1).to_frame("wert"))

# ---------------- Entscheidungsgrundlagen ----------------
# 1) Abdeckung nach letztem Brutjahr der Referenz
R2 = R[R.cell.isin(ok_cells)].copy()
R2["brutjahr"] = pd.cut(R2.year, [0, 1999, 2009, 2019, 2030],
                        labels=["bis 1999", "2000-2009", "2010-2019", "ab 2020"])
pp = R2[["species", "cell", "brutjahr"]].drop_duplicates()
P_by = {pl: d[["species", "cell"]].drop_duplicates() for pl, d in P.groupby("plattform")}
P_all = P[["species", "cell"]].drop_duplicates()
rows = []
for k, d in pp.groupby("brutjahr", observed=True):
    row = {"referenzpaare": len(d)}
    for pl, pdf in P_by.items():
        row[pl + "_%"] = round(len(d.merge(pdf, on=["species", "cell"])) / len(d) * 100, 1)
    row["alle_drei_%"] = round(len(d.merge(P_all, on=["species", "cell"])) / len(d) * 100, 1)
    rows.append(pd.Series(row, name=str(k)))
show("Abdeckung nach letztem Brutjahr der Referenz", pd.DataFrame(rows))

# 2) Wirkung der Koordinatenschwelle (iNaturalist-Meldungen mit grosser Ungenauigkeit)
rows = []
for schwelle in [None, 5000, 2500, 1000]:
    Pf = P if schwelle is None else P[~((P.plattform == "inaturalist") & (P.coordinateUncertaintyInMeters > schwelle))]
    row = {"inaturalist_meldungen": int((Pf.plattform == "inaturalist").sum())}
    for pl, d in Pf.groupby("plattform"):
        hit = pairs.merge(d[["species", "cell"]].drop_duplicates(), on=["species", "cell"])
        row[pl + "_%"] = round(len(hit) / len(pairs) * 100, 2)
    rows.append(pd.Series(row, name="ohne Schwelle" if schwelle is None else f"iNat > {schwelle} m entfernt"))
show("Abdeckung je Koordinatenschwelle (iNaturalist)", pd.DataFrame(rows))

# 3) Observation.org: Meldungen im Juli nach Tag (Auffaelligkeit)
oj = plat[(plat.plattform == "observation_org") & (plat.month == 7)]
print(f"\nObservation.org Juli: {len(oj)} Meldungen, verschiedene Beobachter: {oj.recordedBy.nunique()}")
print("Top-5-Beobachter Anteil (%):", (oj.recordedBy.value_counts(normalize=True).head(5) * 100).round(1).to_dict())

(OUT / "profile.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
print(f"\nGespeichert: {OUT / 'profile.json'}")
