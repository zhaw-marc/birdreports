"""DataOps: Pruefungen der bereinigten Tabellen und der Analysetabelle.

Das Skript prueft die Ausgaben von src/build_analysis_table.py, bevor die Hypothesentests
darauf laufen. Jede Pruefung steht fuer eine Regel, deren Verletzung eine falsche, aber
plausibel aussehende Zahl ergeben wuerde (zum Beispiel doppelt gezaehlte Art/Quadrat-Paare
oder Anteile, die sich nicht auf 1 summieren). Die Art der Pruefungen (unique, not_null,
accepted_values, relationships) folgt den Datentests von dbt, wie sie in der Kleinklasse
(Session 1) verwendet wurden.

Bei einer verletzten Regel endet das Skript mit Exit-Code 1, sodass run_all.sh abbricht.
Die Ergebnisse stehen zusaetzlich in OUT_DIR/checks.json.

Bezeichner sind englisch, Kommentare und Konsolenausgaben deutsch.

Aufruf:
  python src/check_outputs.py [build_out]

Quellen:
  dbt Labs. Data tests. https://docs.getdbt.com/docs/build/data-tests (Vorbild fuer die
    vier Pruefungsarten; es wird kein dbt verwendet).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

GRID_SIZE = 5000
HECTARES_PER_CELL = GRID_SIZE * GRID_SIZE // 10_000        # 2'500 ha pro 5-km-Quadrat
PLATFORMS = ["ebird", "inaturalist", "observation_org"]
LAND_CLASSES = ["settlement", "agriculture", "wooded", "unproductive"]
TOLERANCE = 1e-9

results = []


def check(name, passed, detail=""):
    """Eine Pruefung festhalten und ausgeben."""
    results.append({"check": name, "passed": bool(passed), "detail": str(detail)})
    print(f"{'OK    ' if passed else 'FEHLER'} {name}" + (f"  ({detail})" if detail else ""))


def check_platform(platform, parameters):
    years = parameters.get("years", [2020, 2024])
    months = parameters.get("breeding_months", [4, 7])
    max_uncertainty = parameters.get("max_uncertainty_inaturalist_m", 2500)
    check("platform: accepted_values platform", platform.platform.isin(PLATFORMS).all(),
          sorted(platform.platform.unique()))
    check("platform: not_null species, cell_id",
          platform.species.notna().all() and platform.cell_id.notna().all())
    check(f"platform: Jahr {years[0]}-{years[1]}", platform.year.between(*years).all())
    check(f"platform: Monat {months[0]}-{months[1]} (Brutzeit)",
          platform.month.between(*months).all())
    inat = platform[platform.platform == "inaturalist"]
    check(f"platform: iNaturalist hoechstens {max_uncertainty:g} m Ungenauigkeit",
          not (inat.uncertainty_m > max_uncertainty).any())
    check("platform: keine Klarnamen (recordedBy entfernt)", "recordedBy" not in platform.columns)
    hashes = platform.observer_hash.dropna()
    check("platform: Beobachter-Hash hat 16 Hex-Zeichen",
          hashes.str.fullmatch(r"[0-9a-f]{16}").all(), f"{len(hashes):,} Hashes")
    cells = np.floor(platform.east / GRID_SIZE) * 1000 + np.floor(platform.north / GRID_SIZE)
    check("platform: cell_id passt zu den LV95-Koordinaten", (cells == platform.cell_id).all())


def check_reference(reference):
    check("reference: unique (species, cell_id)",
          not reference.duplicated(["species", "cell_id"]).any(), f"{len(reference):,} Paare")
    check("reference: not_null species, cell_id, last_breeding_year",
          reference[["species", "cell_id", "last_breeding_year"]].notna().all().all())
    check("reference: letztes Brutjahr plausibel (1900 bis 2026)",
          reference.last_breeding_year.between(1900, 2026).all(),
          f"{int(reference.last_breeding_year.min())}-{int(reference.last_breeding_year.max())}")


def check_landuse(landuse):
    check("landuse: unique cell_id", landuse.cell_id.is_unique, f"{len(landuse):,} Quadrate")
    check(f"landuse: 1 bis {HECTARES_PER_CELL} Hektaren je Quadrat",
          landuse.hectares.between(1, HECTARES_PER_CELL).all(),
          f"max {int(landuse.hectares.max())}")
    shares = landuse[[f"share_{c}" for c in LAND_CLASSES]].sum(axis=1)
    check("landuse: Anteile summieren sich auf 1", np.allclose(shares, 1, atol=TOLERANCE))
    hectares = landuse[[f"ha_{c}" for c in LAND_CLASSES]].sum(axis=1)
    check("landuse: Hektaren der Klassen ergeben die Gesamtflaeche",
          (hectares == landuse.hectares).all())


def check_analysis(cells, parameters, log):
    check("analysis: unique cell_id", cells.cell_id.is_unique, f"{len(cells):,} Quadrate")
    rebuilt = (cells.e_min // GRID_SIZE) * 1000 + cells.n_min // GRID_SIZE
    check("analysis: cell_id aus e_min/n_min rekonstruierbar", (rebuilt == cells.cell_id).all())
    for name in PLATFORMS + ["any"]:
        hits_ok = (cells[f"hits_{name}"] <= cells.reference_species).all()
        check(f"analysis: hits_{name} <= reference_species", hits_ok)
        coverage = cells[f"coverage_{name}"]
        has_reference = cells.reference_species > 0
        in_range = coverage[has_reference].between(0, 1).all()
        empty_ok = coverage[~has_reference].isna().all()
        check(f"analysis: coverage_{name} in [0, 1], leer ohne Referenzart", in_range and empty_ok)
    most = cells[[f"hits_{p}" for p in PLATFORMS]].max(axis=1)
    total = cells[[f"hits_{p}" for p in PLATFORMS]].sum(axis=1)
    check("analysis: max(hits je Plattform) <= hits_any <= Summe",
          ((most <= cells.hits_any) & (cells.hits_any <= total)).all())
    check("analysis: records_<plattform> summieren sich zu records",
          (cells[[f"records_{p}" for p in PLATFORMS]].sum(axis=1) == cells.records).all())
    expected_main = (cells.hectares >= parameters.get("min_hectares", 1000)) & (cells.reference_species > 0)
    check("analysis: in_main_analysis = kein Randquadrat und mindestens eine Referenzart",
          (expected_main == cells.in_main_analysis).all())
    main = cells[cells.in_main_analysis]
    if "analysis_cells_main" in log:
        check("analysis: Zahl der Quadrate wie im build_log",
              len(main) == log["analysis_cells_main"], f"{len(main):,}")
    if "analysis_reference_pairs_main" in log:
        check("analysis: Referenzpaare wie im build_log",
              int(main.reference_species.sum()) == log["analysis_reference_pairs_main"],
              f"{int(main.reference_species.sum()):,}")


def check_relationships(cells, reference, landuse, platform, parameters):
    """Querbezuege: Die Analysetabelle muss sich aus den bereinigten Tabellen ergeben."""
    check("relationships: Quadrate der Analysetabelle = Quadrate der Landnutzung",
          set(cells.cell_id) == set(landuse.cell_id))
    min_year = parameters.get("min_breeding_year", 2020)
    main_reference = reference[(~reference.ten_km) & (reference.last_breeding_year >= min_year)]
    counted = main_reference.groupby("cell_id").size()
    expected = cells.set_index("cell_id").reference_species
    recount = counted.reindex(expected.index, fill_value=0)
    check("relationships: reference_species aus reference_clean nachgezaehlt",
          (recount == expected).all())
    records = platform[["species", "cell_id", "platform"]].drop_duplicates()
    pairs = main_reference[["species", "cell_id"]]
    for name in PLATFORMS:
        hits = (pairs.merge(records[records.platform == name], on=["species", "cell_id"])
                .groupby("cell_id").size().reindex(expected.index, fill_value=0))
        check(f"relationships: hits_{name} aus platform_clean nachgezaehlt",
              (hits == cells.set_index("cell_id")[f"hits_{name}"]).all())


def main(build_dir):
    log_path = build_dir / "build_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    parameters = log.get("parameters", {})
    platform = pd.read_parquet(build_dir / "platform_clean.parquet")
    reference = pd.read_parquet(build_dir / "reference_clean.parquet")
    landuse = pd.read_parquet(build_dir / "landuse_cells.parquet")
    cells = pd.read_parquet(build_dir / "analysis_cells.parquet")

    print(f"Pruefe {build_dir}/ (Parameter: {parameters})\n")
    check_platform(platform, parameters)
    check_reference(reference)
    check_landuse(landuse)
    check_analysis(cells, parameters, log)
    check_relationships(cells, reference, landuse, platform, parameters)

    failed = [r for r in results if not r["passed"]]
    (build_dir / "checks.json").write_text(json.dumps(
        {"build_dir": str(build_dir), "parameters": parameters, "checks": results,
         "passed": len(results) - len(failed), "failed": len(failed)},
        indent=1, ensure_ascii=False))
    print(f"\n{len(results) - len(failed)} von {len(results)} Pruefungen bestanden.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "build_out")))
