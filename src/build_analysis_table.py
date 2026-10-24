"""Transformation Teil 1, Schritt 2: Bereinigung und Analysetabelle.

Liest die drei Rohquellen, bereinigt sie nach den Regeln der Konzeption und schreibt
die bereinigten Tabellen sowie die Analysetabelle mit einer Zeile pro 5-km-Quadrat.
Das Skript veraendert die Rohdaten nicht; alle Ergebnisse landen im Ausgabeordner.

Bereinigungsregeln (Konzeption, Abschnitt "Vorgehen und Methoden"):
  Plattformen  nur die drei Dataset-Keys, Schweiz (LV95-Bbox), 2020-2024, April-Juli,
               Art vorhanden, Koordinate vorhanden; iNaturalist-Meldungen mit einer
               Koordinatenungenauigkeit ueber MAX_UNCERTAINTY (Standard 2500 m) entfallen;
               Beobachterkennung wird gehasht
  Referenz     Schweiz, Taxonabgleich ueber mappings/taxon_mapping.csv, je Art und
               Quadrat eine Zeile; 10-km-Meldungen (Ungenauigkeit 7070 m) werden
               markiert und aus der Hauptanalyse ausgeschlossen; in der Hauptanalyse zaehlen
               nur Nachweise mit letztem Brutjahr ab MIN_BREEDING_YEAR (Standard 2020)
  Landnutzung  Hektaren je 5-km-Quadrat nach den vier Hauptklassen AS_4

Bezeichner und Spaltennamen sind durchgehend englisch, Kommentare und Konsolenausgaben
deutsch. Die vier Landnutzungsklassen heissen settlement, agriculture, wooded und
unproductive (AS_4 = 1 bis 4).

Aufruf:
  python src/build_analysis_table.py LANDUSE.csv PLATFORM.csv VOGELWARTE/occurrence.txt \
      mappings/taxon_mapping.csv [OUT_DIR] [--min-breeding-year 2020] [--max-uncertainty 2500]

Sensitivitaetslaeufe (eigene Ausgabeordner, Hauptanalyse bleibt unberuehrt):
  --min-breeding-year 0       alle Brutnachweise statt nur ab 2020
  --max-uncertainty 5000      lockerere Schwelle fuer iNaturalist

Quellen:
  Raster und Koordinatensystem LV95 (EPSG:2056), Transformation ueber pyproj.
  AS_4-Codes (1 Siedlung, 2 Landwirtschaft, 3 bestockt, 4 unproduktiv) nach der
  Variablenbeschreibung der Arealstatistik des BFS, Standardnomenklatur NOAS04.
  Phasen und Unterstroemungen nach Reis, J. & Housley, M. (2022). Fundamentals of
  Data Engineering. Sebastopol: O'Reilly Media.
  Die Quadrat-ID und die Bbox sind aus src/profile_data.py uebernommen, damit die
  Zahlen beider Skripte vergleichbar bleiben.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from pyproj import Transformer

parser = argparse.ArgumentParser(description="Bereinigung und Analysetabelle pro 5-km-Quadrat")
parser.add_argument("landuse_csv")
parser.add_argument("platform_csv")
parser.add_argument("reference_txt")
parser.add_argument("mapping_csv")
parser.add_argument("out_dir", nargs="?", default="build_out")
parser.add_argument("--min-breeding-year", type=int, default=2020,
                    help="Referenz: aeltere letzte Brutjahre zaehlen nicht (0 = alle)")
parser.add_argument("--max-uncertainty", type=float, default=2500,
                    help="iNaturalist: Meldungen mit groesserer Ungenauigkeit (m) entfallen")
args = parser.parse_args()
LANDUSE_CSV, PLATFORM_CSV = args.landuse_csv, args.platform_csv
REFERENCE_TXT, MAPPING_CSV = args.reference_txt, args.mapping_csv
OUT_DIR = Path(args.out_dir)
OUT_DIR.mkdir(parents=True, exist_ok=True)
MIN_BREEDING_YEAR = args.min_breeding_year     # Hauptanalyse: Nachweise ab 2020
MAX_UNCERTAINTY = args.max_uncertainty         # Hauptanalyse: iNaturalist bis 2500 m

DATASET_KEYS = {"4fa7b334-ce0d-4e88-aaae-2e0c138d049e": "ebird",
                "8a863029-f435-446a-821e-275f4f641165": "observation_org",
                "50c9509d-22c7-4a22-a47d-8c48425ef4a7": "inaturalist"}
PLATFORMS = sorted(DATASET_KEYS.values())
LAND_CLASSES = {1: "settlement", 2: "agriculture", 3: "wooded", 4: "unproductive"}
TO_LV95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)
BBOX = (2485000, 2834000, 1075000, 1296000)   # grobe Ausdehnung der Schweiz in LV95
GRID_SIZE = 5000                               # Kantenlaenge der Quadrate in Metern
UNCERTAINTY_10KM = 7070                        # halbe Diagonale eines 10-km-Quadrats
MIN_HECTARES = 1000                            # Schwelle fuer Randquadrate
YEARS = (2020, 2024)
BREEDING_MONTHS = (4, 7)
# Der Salt verhindert das blosse Nachschlagen eines Namens im Hash, nicht mehr.
# Er steht im Repository, weil die Hashes sonst zwischen Laeufen nicht vergleichbar waeren.
SALT = b"birdreports-hs26"

log = {"started": time.strftime("%Y-%m-%d %H:%M:%S"),
       "inputs": {"landuse": LANDUSE_CSV, "platforms": PLATFORM_CSV,
                  "reference": REFERENCE_TXT, "taxon_mapping": MAPPING_CSV},
       "parameters": {"grid_size_m": GRID_SIZE, "years": list(YEARS),
                      "breeding_months": list(BREEDING_MONTHS), "min_hectares": MIN_HECTARES,
                      "excluded_uncertainty_m": UNCERTAINTY_10KM,
                      "min_breeding_year": MIN_BREEDING_YEAR,
                      "max_uncertainty_inaturalist_m": MAX_UNCERTAINTY}}
con = duckdb.connect()


def cell_id(east, north):
    """Quadrat-ID aus LV95-Koordinaten: Ostwert-Index * 1000 + Nordwert-Index."""
    return (np.floor(east / GRID_SIZE) * 1000 + np.floor(north / GRID_SIZE)).astype("int64")


def hash_observer(values):
    """Beobachterkennung pseudonymisieren (Unterstroemung Security der Konzeption)."""
    def digest(value):
        if not isinstance(value, str) or not value.strip():
            return None
        return hashlib.blake2s(value.strip().encode("utf-8"), key=SALT, digest_size=8).hexdigest()
    return values.map(digest)


def note(key, value):
    log[key] = value
    print(f"{key}: {value}", flush=True)


# ---------------- Plattformdaten ----------------
keys = ", ".join(f"'{k}'" for k in DATASET_KEYS)
platform = con.execute(f"""
    SELECT datasetKey, species, decimalLatitude AS lat, decimalLongitude AS lon,
           coordinateUncertaintyInMeters AS uncertainty_m, year, month,
           recordedBy, license
    FROM read_csv('{PLATFORM_CSV}', delim='\\t', quote='', header=true,
                  ignore_errors=true, sample_size=-1)
    WHERE datasetKey IN ({keys})
      AND year BETWEEN {YEARS[0]} AND {YEARS[1]}
      AND month BETWEEN {BREEDING_MONTHS[0]} AND {BREEDING_MONTHS[1]}
      AND species IS NOT NULL AND species <> ''
      AND decimalLatitude IS NOT NULL AND decimalLongitude IS NOT NULL
""").df()
note("platform_rows_after_filter", len(platform))

platform["platform"] = platform.datasetKey.map(DATASET_KEYS)
# iNaturalist verschleiert oder rundet Standorte teils grob. Fehlende Angaben bleiben erhalten.
too_vague = (platform.platform == "inaturalist") & (platform.uncertainty_m > MAX_UNCERTAINTY)
note("inaturalist_rows_too_uncertain", int(too_vague.sum()))
platform = platform[~too_vague].copy()
east, north = TO_LV95.transform(platform.lon.to_numpy(float), platform.lat.to_numpy(float))
platform["east"], platform["north"] = east, north
in_ch = (np.isfinite(east) & np.isfinite(north) & (east >= BBOX[0]) & (east <= BBOX[1])
         & (north >= BBOX[2]) & (north <= BBOX[3]))
note("platform_outside_bbox", int((~in_ch).sum()))
platform = platform[in_ch].copy()
platform["cell_id"] = cell_id(platform.east.to_numpy(), platform.north.to_numpy())
platform["observer_hash"] = hash_observer(platform.recordedBy)
platform = platform.drop(columns=["datasetKey", "recordedBy"])
note("platform_rows_clean", len(platform))
platform.to_parquet(OUT_DIR / "platform_clean.parquet", index=False)

# ---------------- Referenz (Vogelwarte) ----------------
reference = con.execute(f"""
    SELECT genus, specificEpithet, year AS last_breeding_year,
           decimalLatitude AS lat, decimalLongitude AS lon,
           coordinateUncertaintyInMeters AS uncertainty_m
    FROM read_csv('{REFERENCE_TXT}', delim='\\t', quote='', header=true,
                  ignore_errors=true, sample_size=-1)
    WHERE countryCode = 'CH' AND genus IS NOT NULL AND specificEpithet IS NOT NULL
      AND decimalLatitude IS NOT NULL AND decimalLongitude IS NOT NULL
""").df()
note("reference_rows_ch", len(reference))

mapping_table = pd.read_csv(MAPPING_CSV)
mapping = {a: b for a, b in zip(mapping_table.vogelwarte_name, mapping_table.col_name)
           if isinstance(b, str) and b}
reference["vogelwarte_name"] = reference.genus + " " + reference.specificEpithet
reference["species"] = reference.vogelwarte_name.map(lambda s: mapping.get(s, s))
note("reference_renamed_species",
     int(reference.loc[reference.species != reference.vogelwarte_name, "species"].nunique()))
east, north = TO_LV95.transform(reference.lon.to_numpy(float), reference.lat.to_numpy(float))
reference["east"], reference["north"] = east, north
reference["cell_id"] = cell_id(east, north)
reference["ten_km"] = reference.uncertainty_m == UNCERTAINTY_10KM

# Je Art und Quadrat bleibt eine Zeile: juengstes Brutjahr, kleinste Ungenauigkeit.
reference = (reference.sort_values(["uncertainty_m", "last_breeding_year"], ascending=[True, False])
                      .drop_duplicates(["species", "cell_id"])
                      .loc[:, ["species", "cell_id", "last_breeding_year", "uncertainty_m",
                               "ten_km", "east", "north"]]
                      .reset_index(drop=True))
note("reference_pairs_clean", len(reference))
note("reference_pairs_10km", int(reference.ten_km.sum()))
note("reference_species", int(reference.species.nunique()))
reference.to_parquet(OUT_DIR / "reference_clean.parquet", index=False)

# ---------------- Landnutzung (Arealstatistik) ----------------
landuse = con.execute(f"""
    SELECT (E_COORD // {GRID_SIZE}) * 1000 + (N_COORD // {GRID_SIZE}) AS cell_id,
           COUNT(*) AS hectares,
           SUM((AS_4 = 1)::INT) AS ha_settlement,
           SUM((AS_4 = 2)::INT) AS ha_agriculture,
           SUM((AS_4 = 3)::INT) AS ha_wooded,
           SUM((AS_4 = 4)::INT) AS ha_unproductive
    FROM read_csv('{LANDUSE_CSV}', delim=';', header=true)
    GROUP BY 1
""").df()
for land_class in LAND_CLASSES.values():
    landuse[f"share_{land_class}"] = landuse[f"ha_{land_class}"] / landuse.hectares
note("landuse_cells", len(landuse))
note("landuse_cells_below_threshold", int((landuse.hectares < MIN_HECTARES).sum()))
landuse.to_parquet(OUT_DIR / "landuse_cells.parquet", index=False)

# ---------------- Analysetabelle: eine Zeile pro Quadrat ----------------
recent = reference.last_breeding_year >= MIN_BREEDING_YEAR
note("reference_pairs_before_min_year", int((~recent).sum()))
main_reference = reference[(~reference.ten_km) & recent]   # Referenzpaare der Hauptanalyse
pairs = main_reference[["species", "cell_id"]].drop_duplicates()
records = platform[["species", "cell_id", "platform"]].drop_duplicates()

table = landuse.set_index("cell_id").copy()
table["reference_species"] = pairs.groupby("cell_id").size()
table["reference_species_incl_10km"] = (reference[recent][["species", "cell_id"]]
                                        .drop_duplicates().groupby("cell_id").size())
table["last_breeding_year_median"] = main_reference.groupby("cell_id").last_breeding_year.median()

# Treffer: Art/Quadrat-Paar der Referenz, das die Plattform im Zeitraum gemeldet hat.
for name in PLATFORMS:
    hits = pairs.merge(records[records.platform == name], on=["species", "cell_id"])
    table[f"hits_{name}"] = hits.groupby("cell_id").size()
hits_any = pairs.merge(records[["species", "cell_id"]].drop_duplicates(), on=["species", "cell_id"])
table["hits_any"] = hits_any.groupby("cell_id").size()

# Beobachtungsaufwand je Quadrat (Ersatzmass, siehe Konzeption Punkt 4).
grouped = platform.groupby("cell_id")
table["records"] = grouped.size()
table["observers"] = grouped.observer_hash.nunique()
for name in PLATFORMS:
    per_platform = platform[platform.platform == name].groupby("cell_id")
    table[f"records_{name}"] = per_platform.size()
    table[f"observers_{name}"] = per_platform.observer_hash.nunique()

counters = [c for c in table.columns
            if c.startswith(("hits_", "records", "observers", "reference_species"))]
table[counters] = table[counters].fillna(0).astype("int64")

for name in PLATFORMS + ["any"]:
    table[f"coverage_{name}"] = np.where(table.reference_species > 0,
                                         table[f"hits_{name}"] / table.reference_species, np.nan)

table["edge_cell"] = table.hectares < MIN_HECTARES
table["in_main_analysis"] = (~table.edge_cell) & (table.reference_species > 0)
table = table.reset_index()
table["e_min"] = (table.cell_id // 1000) * GRID_SIZE
table["n_min"] = (table.cell_id % 1000) * GRID_SIZE
table["e_center"] = table.e_min + GRID_SIZE / 2
table["n_center"] = table.n_min + GRID_SIZE / 2

columns = (["cell_id", "e_min", "n_min", "e_center", "n_center", "hectares"]
           + [f"share_{c}" for c in LAND_CLASSES.values()]
           + ["reference_species", "reference_species_incl_10km", "last_breeding_year_median"]
           + [f"hits_{p}" for p in PLATFORMS] + ["hits_any"]
           + [f"coverage_{p}" for p in PLATFORMS] + ["coverage_any"]
           + ["records", "observers"]
           + [f"records_{p}" for p in PLATFORMS] + [f"observers_{p}" for p in PLATFORMS]
           + ["edge_cell", "in_main_analysis"])
table = table[columns].sort_values("cell_id").reset_index(drop=True)

note("analysis_cells_total", len(table))
note("analysis_cells_main", int(table.in_main_analysis.sum()))
note("analysis_reference_pairs_main", int(table.loc[table.in_main_analysis, "reference_species"].sum()))
main = table[table.in_main_analysis]
for name in PLATFORMS + ["any"]:
    note(f"coverage_{name}_mean_percent", round(float(main[f"coverage_{name}"].mean()) * 100, 1))

table.to_csv(OUT_DIR / "analysis_cells.csv", index=False)
table.to_parquet(OUT_DIR / "analysis_cells.parquet", index=False)

# ---------------- Analysedatenbank ----------------
db_path = OUT_DIR / "birdreports.duckdb"
db_path.unlink(missing_ok=True)
analysis_db = duckdb.connect(str(db_path))
for name, frame in [("platform_clean", platform), ("reference_clean", reference),
                    ("landuse_cells", landuse), ("analysis_cells", table)]:
    analysis_db.register("tmp_frame", frame)
    analysis_db.execute(f"CREATE TABLE {name} AS SELECT * FROM tmp_frame")
    analysis_db.unregister("tmp_frame")
analysis_db.close()
note("analysis_database_mb", round(db_path.stat().st_size / 1e6, 1))

log["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
(OUT_DIR / "build_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False, default=str))
print(f"\nGeschrieben nach {OUT_DIR}/: platform_clean.parquet, reference_clean.parquet, "
      f"landuse_cells.parquet, analysis_cells.csv/.parquet, birdreports.duckdb, build_log.json")
