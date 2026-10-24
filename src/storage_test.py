"""Storage-Evaluation: DuckDB gegen SQLite auf den Projektdaten.

Misst Ladezeit, Dateigroesse und Abfragezeit fuer zwei typische Aufgaben:
  A) Arealstatistik (4,1 Mio. Hektaren) auf 5-km-Quadrate aggregieren
  B) Plattformmeldungen (1,6 Mio.) nach Datensatz, Jahr und Monat zaehlen
Dazu Parquet: Export der Plattformdaten und Abfrage direkt auf der Datei.
Jede Messung laeuft einmal (Einzelmessung, keine Mittelwerte).

Bezeichner sind englisch, Kommentare und Konsolenausgaben deutsch.

Aufruf:
  python src/storage_test.py LANDUSE.csv PLATFORM.csv [OUT_DIR]
"""
import csv
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

LANDUSE_CSV, PLATFORM_CSV = sys.argv[1], sys.argv[2]
OUT_DIR = Path(sys.argv[3] if len(sys.argv) > 3 else "storage_test_out")
OUT_DIR.mkdir(parents=True, exist_ok=True)
results = {}


def timed(label, fn):
    start = time.perf_counter()
    value = fn()
    elapsed = time.perf_counter() - start
    results[label] = round(elapsed, 2)
    print(f"{label:<44}{elapsed:8.2f} s", flush=True)
    return value


def mb(path):
    return round(os.path.getsize(path) / 1e6, 1)


LANDUSE_COLS = ["RELI", "E_COORD", "N_COORD", "FJ", "AS_4"]
PLATFORM_COLS = ["gbifID", "datasetKey", "species", "decimalLatitude", "decimalLongitude",
                 "year", "month", "individualCount", "recordedBy"]

# ---------- DuckDB ----------
duck_path = OUT_DIR / "test.duckdb"
duck_path.unlink(missing_ok=True)
con = duckdb.connect(str(duck_path))
timed("duckdb: laden Arealstatistik", lambda: con.execute(
    f"CREATE TABLE landuse AS SELECT {', '.join(LANDUSE_COLS)} "
    f"FROM read_csv('{LANDUSE_CSV}', delim=';', header=true)"))
timed("duckdb: laden Plattformdaten", lambda: con.execute(
    f"CREATE TABLE platform AS SELECT {', '.join(PLATFORM_COLS)} "
    f"FROM read_csv('{PLATFORM_CSV}', delim='\\t', quote='', header=true, "
    f"ignore_errors=true, sample_size=-1)"))
query_a = ("SELECT E_COORD//5000 AS cell_e, N_COORD//5000 AS cell_n, AS_4, COUNT(*) AS n "
           "FROM landuse GROUP BY 1,2,3")
query_b = ("SELECT datasetKey, year, month, COUNT(*) AS n, COUNT(DISTINCT species) AS species "
           "FROM platform GROUP BY 1,2,3")
rows_a = timed("duckdb: Abfrage A (Quadrate)", lambda: con.execute(query_a).fetchall())
rows_b = timed("duckdb: Abfrage B (Datensatz/Jahr/Monat)", lambda: con.execute(query_b).fetchall())
results["duckdb_rows"] = {"landuse": con.execute("SELECT COUNT(*) FROM landuse").fetchone()[0],
                          "platform": con.execute("SELECT COUNT(*) FROM platform").fetchone()[0],
                          "query_a_groups": len(rows_a), "query_b_groups": len(rows_b)}
parquet_path = OUT_DIR / "platform.parquet"
timed("duckdb: Export Parquet",
      lambda: con.execute(f"COPY platform TO '{parquet_path}' (FORMAT PARQUET)"))
timed("duckdb: Abfrage B direkt auf Parquet", lambda: con.execute(
    f"SELECT datasetKey, year, month, COUNT(*), COUNT(DISTINCT species) "
    f"FROM read_parquet('{parquet_path}') GROUP BY 1,2,3").fetchall())
con.close()
results["duckdb_file_mb"] = mb(duck_path)
results["parquet_mb"] = mb(parquet_path)

# ---------- SQLite ----------
sqlite_path = OUT_DIR / "test.sqlite"
sqlite_path.unlink(missing_ok=True)
sqlite_con = sqlite3.connect(sqlite_path)


def load_sqlite(path, table, cols, sep):
    first = True
    for chunk in pd.read_csv(path, sep=sep, usecols=cols, chunksize=500_000, low_memory=False,
                             quoting=csv.QUOTE_NONE if sep == "\t" else csv.QUOTE_MINIMAL,
                             on_bad_lines="skip"):
        chunk.to_sql(table, sqlite_con, if_exists="replace" if first else "append", index=False)
        first = False
    sqlite_con.commit()


timed("sqlite: laden Arealstatistik",
      lambda: load_sqlite(LANDUSE_CSV, "landuse", LANDUSE_COLS, ";"))
timed("sqlite: laden Plattformdaten",
      lambda: load_sqlite(PLATFORM_CSV, "platform", PLATFORM_COLS, "\t"))
query_a_sqlite = ("SELECT E_COORD/5000 AS cell_e, N_COORD/5000 AS cell_n, AS_4, COUNT(*) AS n "
                  "FROM landuse GROUP BY 1,2,3")
rows_a_sqlite = timed("sqlite: Abfrage A (Quadrate)",
                      lambda: sqlite_con.execute(query_a_sqlite).fetchall())
rows_b_sqlite = timed("sqlite: Abfrage B (Datensatz/Jahr/Monat)",
                      lambda: sqlite_con.execute(query_b).fetchall())
results["sqlite_rows"] = {
    "landuse": sqlite_con.execute("SELECT COUNT(*) FROM landuse").fetchone()[0],
    "platform": sqlite_con.execute("SELECT COUNT(*) FROM platform").fetchone()[0],
    "query_a_groups": len(rows_a_sqlite), "query_b_groups": len(rows_b_sqlite)}
sqlite_con.close()
results["sqlite_file_mb"] = mb(sqlite_path)

print("\nGleiche Ergebnisse?  A:", len(rows_a) == len(rows_a_sqlite),
      " B:", len(rows_b) == len(rows_b_sqlite))
(OUT_DIR / "storage_test.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
