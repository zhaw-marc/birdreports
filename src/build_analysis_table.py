"""Transformation Teil 1, Schritt 2: Bereinigung und Analysetabelle.

Liest die drei Rohquellen, bereinigt sie nach den Regeln der Konzeption und schreibt
die bereinigten Tabellen sowie die Analysetabelle mit einer Zeile pro 5-km-Quadrat.
Das Skript veraendert die Rohdaten nicht; alle Ergebnisse landen im Ausgabeordner.

Bereinigungsregeln (Konzeption, Abschnitt "Vorgehen und Methoden"):
  Plattformen  nur die drei Dataset-Keys, Schweiz (LV95-Bbox), 2020-2024, April-Juli,
               Art vorhanden, Koordinate vorhanden; Beobachterkennung wird gehasht
  Referenz     Schweiz, Taxonabgleich ueber mappings/taxon_mapping.csv, je Art und
               Quadrat eine Zeile; 10-km-Meldungen (Ungenauigkeit 7070 m) werden
               markiert und aus der Hauptanalyse ausgeschlossen
  Landnutzung  Hektaren je 5-km-Quadrat nach den vier Hauptklassen AS_4

Aufruf:
  python src/build_analysis_table.py AREAL.csv PLATTFORM.csv VOGELWARTE/occurrence.txt \
      mappings/taxon_mapping.csv [OUT_DIR]

Quellen:
  Raster und Koordinatensystem LV95 (EPSG:2056), Transformation ueber pyproj.
  AS_4-Codes (1 Siedlung, 2 Landwirtschaft, 3 bestockt, 4 unproduktiv) nach der
  Variablenbeschreibung der Arealstatistik des BFS, Standardnomenklatur NOAS04.
  Phasen und Unterstroemungen nach Reis, J. & Housley, M. (2022). Fundamentals of
  Data Engineering. Sebastopol: O'Reilly Media.
  Die Quadrat-ID und die Bbox sind aus src/profile_data.py uebernommen, damit die
  Zahlen beider Skripte vergleichbar bleiben.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from pyproj import Transformer

AREAL, PLAT, REF, MAP = sys.argv[1:5]
OUT = Path(sys.argv[5] if len(sys.argv) > 5 else "build_out")
OUT.mkdir(parents=True, exist_ok=True)

KEYS = {"4fa7b334-ce0d-4e88-aaae-2e0c138d049e": "ebird",
        "8a863029-f435-446a-821e-275f4f641165": "observation_org",
        "50c9509d-22c7-4a22-a47d-8c48425ef4a7": "inaturalist"}
PLATTFORMEN = sorted(KEYS.values())
TO_LV95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)
BBOX = (2485000, 2834000, 1075000, 1296000)   # grobe Ausdehnung der Schweiz in LV95
RASTER = 5000                                  # Kantenlaenge der Quadrate in Metern
UNSICHER_10KM = 7070                           # halbe Diagonale eines 10-km-Quadrats
MIN_HEKTAREN = 1000                            # Schwelle fuer Randquadrate
JAHRE = (2020, 2024)
BRUTZEIT = (4, 7)
# Der Salt verhindert das blosse Nachschlagen eines Namens im Hash, nicht mehr.
# Er steht im Repository, weil die Hashes sonst zwischen Laeufen nicht vergleichbar waeren.
SALT = b"birdreports-hs26"

log = {"gestartet": time.strftime("%Y-%m-%d %H:%M:%S"),
       "eingaben": {"arealstatistik": AREAL, "plattformen": PLAT, "referenz": REF, "taxon_mapping": MAP},
       "parameter": {"raster_m": RASTER, "jahre": list(JAHRE), "brutzeit_monate": list(BRUTZEIT),
                     "min_hektaren": MIN_HEKTAREN, "ausgeschlossene_unsicherheit_m": UNSICHER_10KM}}
con = duckdb.connect()


def quadrat(e, n):
    """Quadrat-ID aus LV95-Koordinaten: Ostwert-Index * 1000 + Nordwert-Index."""
    return (np.floor(e / RASTER) * 1000 + np.floor(n / RASTER)).astype("int64")


def hash_beobachter(s):
    """Beobachterkennung pseudonymisieren (Unterstroemung Security der Konzeption)."""
    def h(v):
        if not isinstance(v, str) or not v.strip():
            return None
        return hashlib.blake2s(v.strip().encode("utf-8"), key=SALT, digest_size=8).hexdigest()
    return s.map(h)


def note(key, value):
    log[key] = value
    print(f"{key}: {value}", flush=True)


# ---------------- Plattformdaten ----------------
schluessel = ", ".join(f"'{k}'" for k in KEYS)
plat = con.execute(f"""
    SELECT datasetKey, species, decimalLatitude AS lat, decimalLongitude AS lon,
           coordinateUncertaintyInMeters AS unsicherheit_m, year AS jahr, month AS monat,
           recordedBy, license AS lizenz
    FROM read_csv('{PLAT}', delim='\\t', quote='', header=true, ignore_errors=true, sample_size=-1)
    WHERE datasetKey IN ({schluessel})
      AND year BETWEEN {JAHRE[0]} AND {JAHRE[1]}
      AND month BETWEEN {BRUTZEIT[0]} AND {BRUTZEIT[1]}
      AND species IS NOT NULL AND species <> ''
      AND decimalLatitude IS NOT NULL AND decimalLongitude IS NOT NULL
""").df()
note("plattform_zeilen_nach_filter", len(plat))

plat["plattform"] = plat.datasetKey.map(KEYS)
e, n = TO_LV95.transform(plat.lon.to_numpy(float), plat.lat.to_numpy(float))
plat["E"], plat["N"] = e, n
in_ch = (np.isfinite(e) & np.isfinite(n) & (e >= BBOX[0]) & (e <= BBOX[1])
         & (n >= BBOX[2]) & (n <= BBOX[3]))
note("plattform_ausserhalb_bbox", int((~in_ch).sum()))
plat = plat[in_ch].copy()
plat["quadrat"] = quadrat(plat.E.to_numpy(), plat.N.to_numpy())
plat["beobachter_hash"] = hash_beobachter(plat.recordedBy)
plat = plat.drop(columns=["datasetKey", "recordedBy"])
note("plattform_zeilen_bereinigt", len(plat))
plat.to_parquet(OUT / "plattform_clean.parquet", index=False)

# ---------------- Referenz (Vogelwarte) ----------------
ref = con.execute(f"""
    SELECT genus, specificEpithet, year AS letztes_brutjahr,
           decimalLatitude AS lat, decimalLongitude AS lon,
           coordinateUncertaintyInMeters AS unsicherheit_m
    FROM read_csv('{REF}', delim='\\t', quote='', header=true, ignore_errors=true, sample_size=-1)
    WHERE countryCode = 'CH' AND genus IS NOT NULL AND specificEpithet IS NOT NULL
      AND decimalLatitude IS NOT NULL AND decimalLongitude IS NOT NULL
""").df()
note("referenz_zeilen_ch", len(ref))

m = pd.read_csv(MAP)
mapping = {a: b for a, b in zip(m.vogelwarte_name, m.col_name) if isinstance(b, str) and b}
ref["vogelwarte_name"] = ref.genus + " " + ref.specificEpithet
ref["species"] = ref.vogelwarte_name.map(lambda s: mapping.get(s, s))
note("referenz_umbenannte_arten", int(ref.loc[ref.species != ref.vogelwarte_name, "species"].nunique()))
e, n = TO_LV95.transform(ref.lon.to_numpy(float), ref.lat.to_numpy(float))
ref["E"], ref["N"] = e, n
ref["quadrat"] = quadrat(e, n)
ref["zehn_km"] = ref.unsicherheit_m == UNSICHER_10KM

# Je Art und Quadrat bleibt eine Zeile: juengstes Brutjahr, kleinste Ungenauigkeit.
ref = (ref.sort_values(["unsicherheit_m", "letztes_brutjahr"], ascending=[True, False])
         .drop_duplicates(["species", "quadrat"])
         .loc[:, ["species", "quadrat", "letztes_brutjahr", "unsicherheit_m", "zehn_km", "E", "N"]]
         .reset_index(drop=True))
note("referenz_paare_bereinigt", len(ref))
note("referenz_paare_10km", int(ref.zehn_km.sum()))
note("referenz_arten", int(ref.species.nunique()))
ref.to_parquet(OUT / "referenz_clean.parquet", index=False)

# ---------------- Landnutzung (Arealstatistik) ----------------
land = con.execute(f"""
    SELECT (E_COORD // {RASTER}) * 1000 + (N_COORD // {RASTER}) AS quadrat,
           COUNT(*) AS hektaren,
           SUM((AS_4 = 1)::INT) AS ha_siedlung,
           SUM((AS_4 = 2)::INT) AS ha_landwirtschaft,
           SUM((AS_4 = 3)::INT) AS ha_bestockt,
           SUM((AS_4 = 4)::INT) AS ha_unproduktiv
    FROM read_csv('{AREAL}', delim=';', header=true)
    GROUP BY 1
""").df()
for k in ["siedlung", "landwirtschaft", "bestockt", "unproduktiv"]:
    land[f"anteil_{k}"] = land[f"ha_{k}"] / land.hektaren
note("landnutzung_quadrate", len(land))
note("landnutzung_quadrate_unter_schwelle", int((land.hektaren < MIN_HEKTAREN).sum()))
land.to_parquet(OUT / "landnutzung_cells.parquet", index=False)

# ---------------- Analysetabelle: eine Zeile pro Quadrat ----------------
haupt = ref[~ref.zehn_km]                      # Referenzpaare der Hauptanalyse
paare = haupt[["species", "quadrat"]].drop_duplicates()
meld = plat[["species", "quadrat", "plattform"]].drop_duplicates()

tab = land.set_index("quadrat").copy()
tab["ref_arten"] = paare.groupby("quadrat").size()
tab["ref_arten_inkl_10km"] = ref[["species", "quadrat"]].drop_duplicates().groupby("quadrat").size()
tab["letztes_brutjahr_median"] = haupt.groupby("quadrat").letztes_brutjahr.median()

# Treffer: Art/Quadrat-Paar der Referenz, das die Plattform im Zeitraum gemeldet hat.
for pl in PLATTFORMEN:
    treffer = paare.merge(meld[meld.plattform == pl], on=["species", "quadrat"])
    tab[f"treffer_{pl}"] = treffer.groupby("quadrat").size()
alle = paare.merge(meld[["species", "quadrat"]].drop_duplicates(), on=["species", "quadrat"])
tab["treffer_alle_drei"] = alle.groupby("quadrat").size()

# Beobachtungsaufwand je Quadrat (Ersatzmass, siehe Konzeption Punkt 4).
g = plat.groupby("quadrat")
tab["meldungen"] = g.size()
tab["beobachter"] = g.beobachter_hash.nunique()
for pl in PLATTFORMEN:
    gp = plat[plat.plattform == pl].groupby("quadrat")
    tab[f"meldungen_{pl}"] = gp.size()
    tab[f"beobachter_{pl}"] = gp.beobachter_hash.nunique()

zaehler = [c for c in tab.columns if c.startswith(("treffer_", "meldungen", "beobachter", "ref_arten"))]
tab[zaehler] = tab[zaehler].fillna(0).astype("int64")

for pl in PLATTFORMEN + ["alle_drei"]:
    tab[f"abdeckung_{pl}"] = np.where(tab.ref_arten > 0, tab[f"treffer_{pl}"] / tab.ref_arten, np.nan)

tab["randquadrat"] = tab.hektaren < MIN_HEKTAREN
tab["in_hauptanalyse"] = (~tab.randquadrat) & (tab.ref_arten > 0)
tab = tab.reset_index()
tab["E_min"] = (tab.quadrat // 1000) * RASTER
tab["N_min"] = (tab.quadrat % 1000) * RASTER
tab["E_mitte"] = tab.E_min + RASTER / 2
tab["N_mitte"] = tab.N_min + RASTER / 2

spalten = (["quadrat", "E_min", "N_min", "E_mitte", "N_mitte", "hektaren",
            "anteil_siedlung", "anteil_landwirtschaft", "anteil_bestockt", "anteil_unproduktiv",
            "ref_arten", "ref_arten_inkl_10km", "letztes_brutjahr_median"]
           + [f"treffer_{p}" for p in PLATTFORMEN] + ["treffer_alle_drei"]
           + [f"abdeckung_{p}" for p in PLATTFORMEN] + ["abdeckung_alle_drei"]
           + ["meldungen", "beobachter"]
           + [f"meldungen_{p}" for p in PLATTFORMEN] + [f"beobachter_{p}" for p in PLATTFORMEN]
           + ["randquadrat", "in_hauptanalyse"])
tab = tab[spalten].sort_values("quadrat").reset_index(drop=True)

note("analyse_quadrate_gesamt", len(tab))
note("analyse_quadrate_hauptanalyse", int(tab.in_hauptanalyse.sum()))
note("analyse_referenzpaare_hauptanalyse", int(tab.loc[tab.in_hauptanalyse, "ref_arten"].sum()))
for pl in PLATTFORMEN + ["alle_drei"]:
    h = tab[tab.in_hauptanalyse]
    note(f"abdeckung_{pl}_mittel_prozent", round(float(h[f"abdeckung_{pl}"].mean()) * 100, 1))

tab.to_csv(OUT / "analyse_quadrate.csv", index=False)
tab.to_parquet(OUT / "analyse_quadrate.parquet", index=False)

# ---------------- Analysedatenbank ----------------
db = OUT / "birdreports.duckdb"
db.unlink(missing_ok=True)
adb = duckdb.connect(str(db))
for name, df in [("plattform_clean", plat), ("referenz_clean", ref),
                 ("landnutzung_cells", land), ("analyse_quadrate", tab)]:
    adb.register("df_tmp", df)
    adb.execute(f"CREATE TABLE {name} AS SELECT * FROM df_tmp")
    adb.unregister("df_tmp")
adb.close()
note("analysedatenbank_mb", round(db.stat().st_size / 1e6, 1))

log["beendet"] = time.strftime("%Y-%m-%d %H:%M:%S")
(OUT / "build_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False, default=str))
print(f"\nGeschrieben nach {OUT}/: plattform_clean.parquet, referenz_clean.parquet, "
      f"landnutzung_cells.parquet, analyse_quadrate.csv/.parquet, birdreports.duckdb, build_log.json")
