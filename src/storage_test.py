"""Storage-Evaluation: DuckDB gegen SQLite auf den Projektdaten.

Aufruf:
  python storage_test.py AREALSTATISTIK.csv PLATTFORM.csv [OUT_DIR]

Misst Ladezeit, Dateigroesse und Abfragezeit fuer zwei typische Aufgaben:
  A) Arealstatistik (4,1 Mio. Hektaren) auf 5-km-Quadrate aggregieren
  B) Plattformmeldungen (1,6 Mio.) nach Datensatz, Jahr und Monat zaehlen
Dazu Parquet: Export der Plattformdaten und Abfrage direkt auf der Datei.
Jede Messung laeuft einmal (Einzelmessung, keine Mittelwerte).
"""
import csv, json, os, sqlite3, sys, time
from pathlib import Path
import duckdb
import pandas as pd

AREAL, PLAT = sys.argv[1], sys.argv[2]
OUT = Path(sys.argv[3] if len(sys.argv) > 3 else "storage_test_out")
OUT.mkdir(parents=True, exist_ok=True)
res = {}


def timed(label, fn):
    t = time.perf_counter(); r = fn(); dt = time.perf_counter() - t
    res[label] = round(dt, 2); print(f"{label:<44}{dt:8.2f} s", flush=True)
    return r


def mb(p): return round(os.path.getsize(p) / 1e6, 1)


AREAL_COLS = ["RELI", "E_COORD", "N_COORD", "FJ", "AS_4"]
PLAT_COLS = ["gbifID", "datasetKey", "species", "decimalLatitude", "decimalLongitude",
             "year", "month", "individualCount", "recordedBy"]

# ---------- DuckDB ----------
dpath = OUT / "test.duckdb"
if dpath.exists(): dpath.unlink()
con = duckdb.connect(str(dpath))
timed("duckdb: laden Arealstatistik", lambda: con.execute(
    f"CREATE TABLE areal AS SELECT {', '.join(AREAL_COLS)} FROM read_csv('{AREAL}', delim=';', header=true)"))
timed("duckdb: laden Plattformdaten", lambda: con.execute(
    f"CREATE TABLE plat AS SELECT {', '.join(PLAT_COLS)} FROM read_csv('{PLAT}', delim='\\t', quote='', header=true, "
    f"ignore_errors=true, sample_size=-1)"))
qa = ("SELECT E_COORD//5000 AS zx, N_COORD//5000 AS zy, AS_4, COUNT(*) AS n FROM areal GROUP BY 1,2,3")
qb = ("SELECT datasetKey, year, month, COUNT(*) AS n, COUNT(DISTINCT species) AS arten FROM plat GROUP BY 1,2,3")
ra = timed("duckdb: Abfrage A (Quadrate)", lambda: con.execute(qa).fetchall())
rb = timed("duckdb: Abfrage B (Datensatz/Jahr/Monat)", lambda: con.execute(qb).fetchall())
res["duckdb_zeilen"] = {"areal": con.execute("select count(*) from areal").fetchone()[0],
                         "plat": con.execute("select count(*) from plat").fetchone()[0],
                         "abfrageA_gruppen": len(ra), "abfrageB_gruppen": len(rb)}
pq = OUT / "plattform.parquet"
timed("duckdb: Export Parquet", lambda: con.execute(f"COPY plat TO '{pq}' (FORMAT PARQUET)"))
timed("duckdb: Abfrage B direkt auf Parquet", lambda: con.execute(
    f"SELECT datasetKey, year, month, COUNT(*), COUNT(DISTINCT species) FROM read_parquet('{pq}') GROUP BY 1,2,3").fetchall())
con.close()
res["duckdb_dateigroesse_mb"] = mb(dpath); res["parquet_mb"] = mb(pq)

# ---------- SQLite ----------
spath = OUT / "test.sqlite"
if spath.exists(): spath.unlink()
sq = sqlite3.connect(spath)


def load_sqlite(path, table, cols, sep):
    first = True
    for chunk in pd.read_csv(path, sep=sep, usecols=cols, chunksize=500_000, low_memory=False,
                             quoting=csv.QUOTE_NONE if sep == "\t" else csv.QUOTE_MINIMAL,
                             on_bad_lines="skip"):
        chunk.to_sql(table, sq, if_exists="replace" if first else "append", index=False); first = False
    sq.commit()


timed("sqlite: laden Arealstatistik", lambda: load_sqlite(AREAL, "areal", AREAL_COLS, ";"))
timed("sqlite: laden Plattformdaten", lambda: load_sqlite(PLAT, "plat", PLAT_COLS, "\t"))
qa_s = "SELECT E_COORD/5000 AS zx, N_COORD/5000 AS zy, AS_4, COUNT(*) AS n FROM areal GROUP BY 1,2,3"
qb_s = qb
ra_s = timed("sqlite: Abfrage A (Quadrate)", lambda: sq.execute(qa_s).fetchall())
rb_s = timed("sqlite: Abfrage B (Datensatz/Jahr/Monat)", lambda: sq.execute(qb_s).fetchall())
res["sqlite_zeilen"] = {"areal": sq.execute("select count(*) from areal").fetchone()[0],
                         "plat": sq.execute("select count(*) from plat").fetchone()[0],
                         "abfrageA_gruppen": len(ra_s), "abfrageB_gruppen": len(rb_s)}
sq.close(); res["sqlite_dateigroesse_mb"] = mb(spath)

print("\nGleiche Ergebnisse?  A:", len(ra) == len(ra_s), " B:", len(rb) == len(rb_s))
(OUT / "storage_test.json").write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=2))
