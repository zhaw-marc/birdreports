#!/usr/bin/env bash
# Orchestrierung der Pipeline: fuehrt alle Schritte in der festen Reihenfolge aus und bricht
# beim ersten Fehler ab (auch wenn eine Datenpruefung in src/check_outputs.py fehlschlaegt).
#
# Aufruf aus dem Repository-Wurzelverzeichnis, mit aktivierter .venv:
#   ./run_all.sh                  alles: Download, Profiling, Bereinigung, Pruefungen, Tests,
#                                 Sensitivitaetslaeufe
#   ./run_all.sh --analysis-only  nur Pruefungen und Hypothesentests auf den vorhandenen
#                                 Tabellen (braucht keine Rohdaten)
#   ./run_all.sh --storage        zusaetzlich die Storage-Evaluation (schreibt rund 320 MB
#                                 Testdateien nach storage_test_out/)
#
# Vorhandene Rohdaten in data/ werden nicht neu geladen (siehe src/download_data.py --force).
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python}"
LANDUSE="data/ag-b-00/ag-b-00.03-37-area-current-csv.csv"
PLATFORM="data/0024005-260928105237408.csv"
REFERENCE="data/dwca-soi_aves-v1/occurrence.txt"
MAPPING="mappings/taxon_mapping.csv"

ANALYSIS_ONLY=0
STORAGE=0
for arg in "$@"; do
  case "$arg" in
    --analysis-only) ANALYSIS_ONLY=1 ;;
    --storage) STORAGE=1 ;;
    *) echo "Unbekannte Option: $arg" >&2; exit 2 ;;
  esac
done

step() { printf '\n==== %s\n' "$*"; }

# Laeufe: Ausgabeordner der Tabellen, Ausgabeordner der Tests, Parameter der Bereinigung
RUNS=(
  "build_out analysis_out"
  "build_out_sens_all_years analysis_out_sens_all_years --min-breeding-year 0"
  "build_out_sens_5000m analysis_out_sens_5000m --max-uncertainty 5000"
)

if [[ $ANALYSIS_ONLY -eq 0 ]]; then
  step "Ingestion: Rohdaten beziehen (vorhandene Dateien bleiben)"
  "$PYTHON" src/download_data.py

  step "Transformation Teil 1: initiale Analyse der Datengrundlage"
  "$PYTHON" src/profile_data.py "$LANDUSE" "$PLATFORM" "$REFERENCE" "$MAPPING"

  if [[ $STORAGE -eq 1 ]]; then
    step "Storage: Evaluation DuckDB gegen SQLite"
    "$PYTHON" src/storage_test.py "$LANDUSE" "$PLATFORM"
  fi
fi

for run in "${RUNS[@]}"; do
  # shellcheck disable=SC2086
  set -- $run
  build_dir="$1"; analysis_dir="$2"; shift 2
  if [[ $ANALYSIS_ONLY -eq 1 && ! -f "$build_dir/analysis_cells.parquet" ]]; then
    # Die Tabellen der Sensitivitaetslaeufe sind nicht versioniert (siehe .gitignore).
    step "Uebersprungen: $build_dir fehlt (zuerst ohne --analysis-only laufen lassen)"
    continue
  fi
  if [[ $ANALYSIS_ONLY -eq 0 ]]; then
    step "Bereinigung und Analysetabelle -> $build_dir $*"
    "$PYTHON" src/build_analysis_table.py "$LANDUSE" "$PLATFORM" "$REFERENCE" "$MAPPING" \
      "$build_dir" "$@"
  fi
  step "Datenpruefungen -> $build_dir"
  "$PYTHON" src/check_outputs.py "$build_dir"
  step "Hypothesentests -> $analysis_dir"
  "$PYTHON" src/hypothesis_tests.py "$build_dir/analysis_cells.parquet" "$analysis_dir"
done

step "Fertig. Notebook: marimo run notebooks/birdreports.py"
