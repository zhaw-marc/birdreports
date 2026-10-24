"""Ingestion: laedt die drei Rohquellen reproduzierbar nach data/.

Jeder Lauf schreibt Datum, Quell-URL, DOI, HTTP-Status, Groesse und SHA-256-Pruefsumme
nach ingest_out/download_log.json. Damit ist belegbar, welche Fassung einer Quelle in die
Auswertung eingegangen ist; die Rohdaten selbst bleiben wegen ihrer Groesse ausserhalb
des Repositorys.

Bezeichner und Protokollfelder sind englisch, Kommentare und Konsolenausgaben deutsch.

Quellen und Zielpfade:
  platforms   GBIF-Download 0024005-260928105237408 (SIMPLE_CSV, ca. 175 MB gepackt,
              1'595'325 Datensaetze), DOI 10.15468/dl.9qfxn7
              -> data/0024005-260928105237408.csv
  reference   Darwin-Core-Archiv der Brutvogeldatenbank vom IPT der Vogelwarte,
              DOI des Datensatzes 10.15468/jujcgr
              -> data/dwca-soi_aves-v1/{occurrence.txt, meta.xml, eml.xml}
  landuse     Arealstatistik "Aktueller Stand" des BFS, Asset ag-b-00.03-37-area-current-csv
              -> data/ag-b-00/

Aufruf:
  python src/download_data.py                     # alles, vorhandene Dateien bleiben
  python src/download_data.py --only platforms    # nur eine Quelle
  python src/download_data.py --force             # erneut laden und ueberschreiben
  python src/download_data.py --fallback          # Plattformdaten ueber die Search-API

Fallback: GBIF haelt erzeugte Downloads nicht unbegrenzt vor. Ist der Download nicht mehr
abrufbar, laedt --fallback dieselben Filter ueber die Search-API (/occurrence/search) und
schreibt eine gleichnamige Tabelle mit den Spalten, die die Pipeline liest. Die Search-API
liefert hoechstens 100'000 Treffer pro Abfrage, darum wird nach Datensatz, Jahr und Monat
aufgeteilt. Die Ergebnisse sind nicht byteidentisch mit dem Download: Die Suche arbeitet mit
der GBIF-Backbone-Taxonomie, der Download mit dem Catalogue of Life, und zwischenzeitliche
Korrekturen bei GBIF sind enthalten. Der Lauf wird im Protokoll als "search_api" vermerkt.

Quellen:
  GBIF-API, Endpunkte /occurrence/download/{key}, /dataset/{key}/endpoint und
  /occurrence/search, dokumentiert unter https://techdocs.gbif.org/en/openapi/
  Arealstatistik des BFS ueber opendata.swiss, Paket arealstatistik-aktueller-stand-csv,
  Asset-Landingpage https://www.bfs.admin.ch/asset/de/ag-b-00.03-37-area-current-csv
"""
import argparse
import csv
import hashlib
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

GBIF_API = "https://api.gbif.org/v1"
DOWNLOAD_KEY = "0024005-260928105237408"
DOWNLOAD_DOI = "10.15468/dl.9qfxn7"
REFERENCE_DATASET = "63f077c9-96a0-49de-b3ea-2aa565ee1098"
REFERENCE_DOI = "10.15468/jujcgr"
BFS_ASSET_URL = "https://dam-api.bfs.admin.ch/hub/api/dam/assets/32376220/appendix"
BFS_ASSET_ID = "ag-b-00.03-37-area-current-csv"
BFS_LANDING = "https://www.bfs.admin.ch/asset/de/ag-b-00.03-37-area-current-csv"
PLATFORMS = {"ebird": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e",
             "observation_org": "8a863029-f435-446a-821e-275f4f641165",
             "inaturalist": "50c9509d-22c7-4a22-a47d-8c48425ef4a7"}
AVES_CLASS_KEY = 212                 # GBIF-Backbone, Klasse Aves
YEARS = range(2020, 2025)
PAGE_SIZE = 300                      # Treffer pro Abfrage der Search-API
COLUMNS = ["gbifID", "datasetKey", "species", "decimalLatitude", "decimalLongitude",
           "coordinateUncertaintyInMeters", "year", "month", "day", "individualCount",
           "recordedBy", "basisOfRecord", "license", "countryCode"]
USER_AGENT = "birdreports/1.0 (ZHAW Data Engineering HS26; vogmar04@students.zhaw.ch)"


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download_file(url, target, attempts=3):
    """Laedt eine Datei und liefert Status, Groesse und SHA-256."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response, open(partial, "wb") as f:
                status = response.status
                total = int(response.headers.get("Content-Length") or 0)
                digest = hashlib.sha256()
                loaded = 0
                while chunk := response.read(1 << 20):
                    f.write(chunk)
                    digest.update(chunk)
                    loaded += len(chunk)
                    if total:
                        print(f"\r  {loaded / 1e6:8.1f} / {total / 1e6:.1f} MB", end="", flush=True)
                    else:
                        print(f"\r  {loaded / 1e6:8.1f} MB", end="", flush=True)
            print()
            partial.replace(target)
            return {"http_status": status, "bytes": loaded, "sha256": digest.hexdigest()}
        except (urllib.error.URLError, TimeoutError) as error:
            partial.unlink(missing_ok=True)
            if attempt == attempts:
                raise
            wait = 5 * attempt
            print(f"  Fehlversuch {attempt}/{attempts} ({error}), neuer Versuch in {wait} s")
            time.sleep(wait)


def extract(zip_path, target_dir, delete_zip=True):
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        for name in names:
            # flach entpacken, damit die Ablage unabhaengig von der Zip-Struktur gleich aussieht
            with archive.open(name) as source, open(target_dir / Path(name).name, "wb") as f:
                shutil.copyfileobj(source, f)
    if delete_zip:
        zip_path.unlink()
    return [Path(n).name for n in names]


# ---------------- Quelle 1: Plattformdaten ----------------
def platforms(data_dir: Path, force: bool, fallback: bool):
    target = data_dir / f"{DOWNLOAD_KEY}.csv"
    if target.exists() and not force:
        return {"status": "present", "key": DOWNLOAD_KEY, "doi": DOWNLOAD_DOI,
                "path": str(target), "bytes": target.stat().st_size}

    meta = fetch_json(f"{GBIF_API}/occurrence/download/{DOWNLOAD_KEY}")
    entry = {"source": "GBIF Occurrence Download", "key": DOWNLOAD_KEY,
             "doi": meta.get("doi"), "download_status": meta.get("status"),
             "created": meta.get("created"), "records": meta.get("totalRecords"),
             "license": meta.get("license"), "format": (meta.get("request") or {}).get("format")}
    print(f"GBIF-Download {DOWNLOAD_KEY}: Status {entry['download_status']}, "
          f"{entry['records']} Datensaetze, DOI {entry['doi']}")

    if fallback or entry["download_status"] != "SUCCEEDED":
        if not fallback:
            print("  Download nicht abrufbar, weiche auf die Search-API aus.")
        entry.update(search_api(target))
        entry["origin"] = "search_api"
        return entry

    zip_path = data_dir / f"{DOWNLOAD_KEY}.zip"
    entry["url"] = meta.get("downloadLink")
    entry.update(download_file(entry["url"], zip_path))
    extracted = extract(zip_path, data_dir)
    # Der SIMPLE_CSV-Export enthaelt genau eine Tabelle, die Endung lautet .csv,
    # der Inhalt ist tabulatorgetrennt.
    tables = [n for n in extracted if n.endswith((".csv", ".txt"))]
    if tables and not target.exists():
        (data_dir / tables[0]).rename(target)
    entry["origin"] = "download"
    entry["path"] = str(target)
    entry["extracted"] = extracted
    return entry


def search_api(target: Path):
    """Fallback: dieselben Filter ueber /occurrence/search, aufgeteilt nach Datensatz, Jahr, Monat."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    rows = 0
    queries = 0
    with open(partial, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t",
                                extrasaction="ignore", restval="")
        writer.writeheader()
        for name, dataset_key in PLATFORMS.items():
            for year in YEARS:
                for month in range(1, 13):
                    offset = 0
                    while True:
                        query = urllib.parse.urlencode({
                            "country": "CH", "classKey": AVES_CLASS_KEY,
                            "occurrenceStatus": "PRESENT", "datasetKey": dataset_key,
                            "year": year, "month": month,
                            "limit": PAGE_SIZE, "offset": offset})
                        response = fetch_json(f"{GBIF_API}/occurrence/search?{query}")
                        queries += 1
                        for hit in response["results"]:
                            writer.writerow({c: hit.get(c, "") for c in COLUMNS})
                            rows += 1
                        if response.get("endOfRecords") or not response["results"]:
                            break
                        offset += PAGE_SIZE
                        if offset >= 100000:   # harte Grenze der Search-API
                            print(f"  WARNUNG: {name} {year}-{month:02d} ueberschreitet 100'000 "
                                  "Treffer, der Rest fehlt.")
                            break
                    print(f"\r  {name} {year}-{month:02d}: {rows} Zeilen", end="", flush=True)
    print()
    partial.replace(target)
    return {"url": f"{GBIF_API}/occurrence/search", "rows": rows, "queries": queries,
            "path": str(target), "bytes": target.stat().st_size,
            "note": "Search-API statt Download; Backbone-Taxonomie, nicht byteidentisch"}


# ---------------- Quelle 2: Referenz der Vogelwarte ----------------
def reference(data_dir: Path, force: bool):
    folder = data_dir / "dwca-soi_aves-v1"
    if (folder / "occurrence.txt").exists() and not force:
        return {"status": "present", "doi": REFERENCE_DOI, "path": str(folder)}

    endpoints = fetch_json(f"{GBIF_API}/dataset/{REFERENCE_DATASET}/endpoint")
    archives = [e["url"] for e in endpoints if e.get("type") == "DWC_ARCHIVE"]
    if not archives:
        raise SystemExit("Kein DWC_ARCHIVE-Endpunkt im Datensatz der Vogelwarte gefunden.")
    entry = {"source": "Swiss National Breeding Bird Databank", "doi": REFERENCE_DOI,
             "dataset_key": REFERENCE_DATASET, "url": archives[0]}
    print(f"Darwin-Core-Archiv der Vogelwarte: {archives[0]}")
    zip_path = data_dir / "dwca-soi_aves-v1.zip"
    entry.update(download_file(archives[0], zip_path))
    entry["extracted"] = extract(zip_path, folder)
    entry["path"] = str(folder)
    return entry


# ---------------- Quelle 3: Arealstatistik ----------------
def landuse(data_dir: Path, force: bool):
    folder = data_dir / "ag-b-00"
    if any(folder.glob("*.csv")) and not force:
        return {"status": "present", "asset": BFS_ASSET_ID, "path": str(folder)}

    entry = {"source": "Arealstatistik BFS, Aktueller Stand", "url": BFS_ASSET_URL,
             "landing_page": BFS_LANDING, "asset": BFS_ASSET_ID}
    print(f"Arealstatistik des BFS: {BFS_ASSET_URL}")
    zip_path = data_dir / "ag-b-00.zip"
    entry.update(download_file(BFS_ASSET_URL, zip_path))
    entry["extracted"] = extract(zip_path, folder)
    entry["path"] = str(folder)
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default="data", help="Zielordner, Standard data/")
    parser.add_argument("--only", choices=["platforms", "reference", "landuse"],
                        help="nur eine Quelle laden")
    parser.add_argument("--force", action="store_true", help="vorhandene Dateien ueberschreiben")
    parser.add_argument("--fallback", action="store_true",
                        help="Plattformdaten ueber die Search-API statt ueber den Download laden")
    parser.add_argument("--log-dir", default="ingest_out",
                        help="Ordner fuer das Protokoll, Standard ingest_out/ (wird versioniert)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "download_log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {"runs": []}

    run = {"started": now(), "python": sys.version.split()[0], "sources": {}}
    tasks = {"platforms": lambda: platforms(data_dir, args.force, args.fallback),
             "reference": lambda: reference(data_dir, args.force),
             "landuse": lambda: landuse(data_dir, args.force)}
    for name, task in tasks.items():
        if args.only and args.only != name:
            continue
        print(f"\n=== {name}")
        try:
            run["sources"][name] = task()
        except Exception as error:                  # Lauf protokollieren, auch wenn er scheitert
            run["sources"][name] = {"status": "failed", "error": repr(error)}
            print(f"  FEHLER: {error}")
    run["finished"] = now()

    log["runs"].append(run)
    log_path.write_text(json.dumps(log, indent=1, ensure_ascii=False, default=str))
    print(f"\nProtokoll: {log_path} ({len(log['runs'])} Laeufe)")
    for name, entry in run["sources"].items():
        print(f"  {name:11} {entry.get('status', entry.get('origin', 'geladen')):12} "
              f"{entry.get('doi') or entry.get('asset') or ''}")


if __name__ == "__main__":
    main()
