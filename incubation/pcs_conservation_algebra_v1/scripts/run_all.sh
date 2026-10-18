#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== pytest =="
python3 -m pip install -e ".[dev]" -q
python3 -m pytest -q

echo "== receive demos =="
OUT="$ROOT/research/demo-receipts"
rm -rf "$OUT"
mkdir -p "$OUT"
python3 -m pcca.cli.main receive examples/mass_action/glucose_cleavage.json -o "$OUT/glucose"
python3 -m pcca.cli.main receive examples/transport_reduction/two_cell_exchange.json -o "$OUT/exchange"
set +e
python3 -m pcca.cli.main receive examples/adversarial/mass_leak.json -o "$OUT/leak"
leak_status=$?
set -e
test "$leak_status" -ne 0

echo "== noninterference =="
bash scripts/noninterference_check.sh

echo "== optional Lean build =="
if command -v lake >/dev/null 2>&1; then
  export LAKE_CACHE_DIR="${LAKE_CACHE_DIR:-$HOME/.cache/pcca-lake}"
  lake exe cache get || true
  lake build
else
  echo "lake not on PATH; skipping Lean build"
fi

echo "ALL GREEN"
