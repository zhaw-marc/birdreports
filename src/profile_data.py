"""Initiale Analyse der Datengrundlage (Transformation Teil 1, Schritt 1).

Misst nur, veraendert keine Daten. Alle Schwellen der Konzeption werden hier mit Zahlen
belegt: Koordinatenungenauigkeit, Randquadrate, Brutzeit, Artabgleich, erste Abdeckung.

Bezeichner und Spaltennamen sind englisch, Kommentare und die Titel der Ausgabetabellen
deutsch.

Aufruf:
  python src/profile_data.py LANDUSE.csv PLATFORM.csv VOGELWARTE/occurrence.txt \
      mappings/taxon_mapping.csv [OUT_DIR]
Abhaengigkeiten: duckdb, pandas, pyproj
"""
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from pyproj import Transformer

LANDUSE_CSV, PLATFORM_CSV, REFERENCE_TXT, MAPPING_CSV = sys.argv[1:5]
OUT_DIR = Path(sys.argv[5] if len(sys.argv) > 5 else "profile_out")
OUT_DIR.mkdir(exist_ok=True)
DATASET_KEYS = {"4fa7b334-ce0d-4e88-aaae-2e0c138d049e": "ebird",
                "8a863029-f435-446a-821e-275f4f641165": "observation_org",
                "50c9509d-22c7-4a22-a47d-8c48425ef4a7": "inaturalist"}
TO_LV95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)
BBOX = (2485000, 2834000, 1075000, 1296000)   # grobe Ausdehnung der Schweiz in LV95
report = {}


def show(title, frame):
    print(f"\n=== {title}")
    print(frame.to_string())
    report[title] = json.loads(frame.to_json(orient="split"))


def add_cell(frame):
    east, north = TO_LV95.transform(frame.decimalLongitude.to_numpy(float),
                                    frame.decimalLatitude.to_numpy(float))
    frame["east"], frame["north"] = east, north
    valid = np.isfinite(east) & np.isfinite(north)
    frame["cell_id"] = np.where(valid,
                                np.floor(np.nan_to_num(east) / 5000) * 1000
                                + np.floor(np.nan_to_num(north) / 5000), -1).astype("int64")
    frame["in_ch"] = (valid & (east >= BBOX[0]) & (east <= BBOX[1])
                      & (north >= BBOX[2]) & (north <= BBOX[3]))
    return frame


# ---------------- Plattformdaten ----------------
con = duckdb.connect()
cols = ("datasetKey, species, decimalLatitude, decimalLongitude, coordinateUncertaintyInMeters, "
        "year, month, individualCount, recordedBy, basisOfRecord, license")
platform = con.execute(f"SELECT {cols} FROM read_csv('{PLATFORM_CSV}', delim='\\t', quote='', "
                       f"header=true, ignore_errors=true, sample_size=-1)").df()
platform["platform"] = platform.datasetKey.map(DATASET_KEYS).fillna("other")
platform = add_cell(platform)
grouped = platform.groupby("platform")
uncertainty = grouped.coordinateUncertaintyInMeters
table = pd.DataFrame({
    "rows": grouped.size(),
    "missing_coordinate": grouped.decimalLatitude.apply(lambda s: int(s.isna().sum())),
    "missing_species": grouped.species.apply(lambda s: int(s.isna().sum())),
    "outside_ch_bbox": grouped.in_ch.apply(lambda s: int((~s).sum())),
    "missing_count_pct": grouped.individualCount.apply(lambda s: round(s.isna().mean() * 100, 1)),
    "distinct_observers": grouped.recordedBy.nunique(),
    "missing_observer_pct": grouped.recordedBy.apply(lambda s: round(s.isna().mean() * 100, 1)),
    "apr_jul_pct": grouped.month.apply(lambda s: round(s.between(4, 7).mean() * 100, 1)),
})
show("Plattformen: Grunddaten", table)
show("Plattformen: Koordinatenungenauigkeit (m)", pd.DataFrame({
    "missing_pct": uncertainty.apply(lambda s: round(s.isna().mean() * 100, 1)),
    "median": uncertainty.median(), "p90": uncertainty.quantile(0.9),
    "above_1000_pct": uncertainty.apply(lambda s: round((s > 1000).mean() * 100, 2)),
    "above_2500_pct": uncertainty.apply(lambda s: round((s > 2500).mean() * 100, 2)),
    "above_5000_pct": uncertainty.apply(lambda s: round((s > 5000).mean() * 100, 2))}))
show("Plattformen: Meldungen pro Jahr", pd.crosstab(platform.platform, platform.year))
show("Plattformen: Meldungen pro Monat", pd.crosstab(platform.platform, platform.month))
show("Plattformen: Lizenzen", pd.crosstab(platform.platform, platform.license))

analysis_rows = platform[platform.platform.isin(DATASET_KEYS.values()) & platform.in_ch
                         & platform.species.notna() & platform.year.between(2020, 2024)
                         & platform.month.between(4, 7)].copy()
print(f"\nPlattformdaten fuer die Analyse (CH, 2020-2024, April-Juli, mit Art): {len(analysis_rows)}")
report["platform_analysis_rows"] = len(analysis_rows)

# ---------------- Referenz ----------------
reference = pd.read_csv(REFERENCE_TXT, sep="\t", low_memory=False, usecols=[
    "countryCode", "genus", "specificEpithet", "year", "decimalLatitude", "decimalLongitude",
    "coordinateUncertaintyInMeters"])
reference = reference[reference.countryCode == "CH"].copy()
mapping_table = pd.read_csv(MAPPING_CSV)
mapping = {a: b for a, b in zip(mapping_table.vogelwarte_name, mapping_table.col_name)
           if isinstance(b, str) and b}
reference["species"] = (reference.genus + " " + reference.specificEpithet).map(
    lambda name: mapping.get(name, name))
reference = add_cell(reference)
offset = ((reference[reference.coordinateUncertaintyInMeters == 3535].east % 5000) - 2500).abs()
print(f"\nReferenz CH: {len(reference)} Zeilen, {reference.species.nunique()} Arten, "
      f"{reference.cell_id.nunique()} Quadrate")
print(f"Rasterpruefung: Median Abweichung der Quadratmitte {offset.median():.1f} m (erwartet nahe 0)")
report["reference"] = {"rows": len(reference), "species": int(reference.species.nunique()),
                       "cells": int(reference.cell_id.nunique()),
                       "grid_offset_median_m": float(offset.median())}
show("Referenz: Koordinatenungenauigkeit",
     reference.coordinateUncertaintyInMeters.value_counts().to_frame("rows"))
show("Referenz: letztes Brutjahr (Jahrzehnte)",
     pd.cut(reference.year, [0, 1999, 2009, 2019, 2030],
            labels=["bis 1999", "2000-2009", "2010-2019", "ab 2020"])
       .value_counts().sort_index().to_frame("rows"))
show("Referenz: Arten pro Quadrat",
     reference.groupby("cell_id").species.nunique().describe().round(1).to_frame("value"))
show("Referenz: doppelte Art/Quadrat-Paare",
     pd.DataFrame({"duplicates": [int(reference.duplicated(["species", "cell_id"]).sum())]}))
main_reference = reference[reference.coordinateUncertaintyInMeters != 7070]

# ---------------- Arealstatistik ----------------
landuse = con.execute(f"""SELECT (E_COORD//5000)*1000 + (N_COORD//5000) AS cell_id,
    COUNT(*) AS hectares,
    SUM((AS_4=1)::INT) AS settlement, SUM((AS_4=2)::INT) AS agriculture,
    SUM((AS_4=3)::INT) AS wooded, SUM((AS_4=4)::INT) AS unproductive
    FROM read_csv('{LANDUSE_CSV}', delim=';', header=true) GROUP BY 1""").df()
for land_class in ["settlement", "agriculture", "wooded", "unproductive"]:
    landuse["share_" + land_class] = landuse[land_class] / landuse.hectares
show("Arealstatistik: Hektaren pro 5-km-Quadrat", landuse.hectares.describe().round(1).to_frame("value"))
small_cells = landuse[landuse.hectares < 1000]
print(f"\nQuadrate gesamt: {len(landuse)}, davon unter 1000 ha: {len(small_cells)}")
report["landuse"] = {"cells": len(landuse), "below_1000_ha": len(small_cells)}
large_cells = set(landuse[landuse.hectares >= 1000].cell_id)
reference_cells = set(main_reference.cell_id)
print(f"Referenzquadrate (ohne 10-km-Zeilen): {len(reference_cells)}; "
      f"ohne Arealstatistik: {len(reference_cells - set(landuse.cell_id))}; "
      f"davon unter 1000 ha: {len(reference_cells & set(small_cells.cell_id))}")
report["cells"] = {"reference": len(reference_cells),
                   "without_landuse": len(reference_cells - set(landuse.cell_id)),
                   "below_1000_ha": len(reference_cells & set(small_cells.cell_id))}
print(f"Plattformquadrate mit Meldungen: {analysis_rows.cell_id.nunique()}; "
      f"davon nicht in der Referenz: {len(set(analysis_rows.cell_id) - reference_cells)}")

# ---------------- Artabgleich und erste Abdeckung (Vorschau, keine Hypothesentests) ----------------
reference_species = set(main_reference.species)
rows = []
for name, part in analysis_rows.groupby("platform"):
    rows.append({"platform": name, "records": len(part),
                 "species_in_reference_pct": round(part.species.isin(reference_species).mean() * 100, 1)})
show("Plattformen: Meldungen mit Art aus der Referenz", pd.DataFrame(rows).set_index("platform"))

pairs = main_reference[main_reference.cell_id.isin(large_cells)][["species", "cell_id"]].drop_duplicates()
coverage = {}
for name, part in analysis_rows.groupby("platform"):
    hits = pairs.merge(part[["species", "cell_id"]].drop_duplicates(), on=["species", "cell_id"])
    coverage[name] = round(len(hits) / len(pairs) * 100, 1)
hits_any = pairs.merge(analysis_rows[["species", "cell_id"]].drop_duplicates(),
                       on=["species", "cell_id"])
coverage["any"] = round(len(hits_any) / len(pairs) * 100, 1)
show("Erste Abdeckung (Anteil Art/Quadrat-Paare der Referenz mit Meldung, %)",
     pd.DataFrame({"coverage_pct": coverage, "reference_pairs": len(pairs)}))
per_cell = (hits_any.groupby("cell_id").size().reindex(pairs.cell_id.unique(), fill_value=0)
            / pairs.groupby("cell_id").size())
show("Abdeckungsquote pro Quadrat (alle drei), Verteilung",
     (per_cell * 100).describe().round(1).to_frame("value"))

# ---------------- Entscheidungsgrundlagen ----------------
# 1) Abdeckung nach letztem Brutjahr der Referenz
main_cells = main_reference[main_reference.cell_id.isin(large_cells)].copy()
main_cells["breeding_year"] = pd.cut(main_cells.year, [0, 1999, 2009, 2019, 2030],
                                     labels=["bis 1999", "2000-2009", "2010-2019", "ab 2020"])
by_year = main_cells[["species", "cell_id", "breeding_year"]].drop_duplicates()
pairs_by_platform = {name: part[["species", "cell_id"]].drop_duplicates()
                     for name, part in analysis_rows.groupby("platform")}
pairs_any = analysis_rows[["species", "cell_id"]].drop_duplicates()
rows = []
for key, part in by_year.groupby("breeding_year", observed=True):
    row = {"reference_pairs": len(part)}
    for name, platform_pairs in pairs_by_platform.items():
        row[name + "_pct"] = round(
            len(part.merge(platform_pairs, on=["species", "cell_id"])) / len(part) * 100, 1)
    row["any_pct"] = round(len(part.merge(pairs_any, on=["species", "cell_id"])) / len(part) * 100, 1)
    rows.append(pd.Series(row, name=str(key)))
show("Abdeckung nach letztem Brutjahr der Referenz", pd.DataFrame(rows))

# 2) Wirkung der Koordinatenschwelle (iNaturalist-Meldungen mit grosser Ungenauigkeit)
rows = []
for threshold in [None, 5000, 2500, 1000]:
    filtered = analysis_rows if threshold is None else analysis_rows[
        ~((analysis_rows.platform == "inaturalist")
          & (analysis_rows.coordinateUncertaintyInMeters > threshold))]
    row = {"inaturalist_records": int((filtered.platform == "inaturalist").sum())}
    for name, part in filtered.groupby("platform"):
        hits = pairs.merge(part[["species", "cell_id"]].drop_duplicates(), on=["species", "cell_id"])
        row[name + "_pct"] = round(len(hits) / len(pairs) * 100, 2)
    rows.append(pd.Series(row, name="ohne Schwelle" if threshold is None
                          else f"iNat > {threshold} m entfernt"))
show("Abdeckung je Koordinatenschwelle (iNaturalist)", pd.DataFrame(rows))

# 3) Observation.org: Meldungen im Juli nach Beobachter (Auffaelligkeit)
july = platform[(platform.platform == "observation_org") & (platform.month == 7)]
print(f"\nObservation.org Juli: {len(july)} Meldungen, "
      f"verschiedene Beobachter: {july.recordedBy.nunique()}")
print("Anteil der fuenf aktivsten Beobachter (%):",
      (july.recordedBy.value_counts(normalize=True).head(5) * 100).round(1).tolist())

(OUT_DIR / "profile.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
print(f"\nGespeichert: {OUT_DIR / 'profile.json'}")
