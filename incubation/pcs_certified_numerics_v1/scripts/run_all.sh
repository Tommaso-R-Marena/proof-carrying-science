#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/.elan/bin:$PATH"
export LAKE_CACHE_DIR="${LAKE_CACHE_DIR:-$HOME/.cache/certnum-lake}"
VENV="${CERTNUM_VENV:-$HOME/.venvs/pcs-certified-numerics}"

echo "== CertNum run_all =="
cd "$ROOT"

if [[ -x "$VENV/bin/python" ]]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
fi

python -m pip install -e ".[dev]" -q
python -m pytest -q
echo "Python tests OK"

lake build
echo "Lean build OK"

python scripts/gen_theorem_inventory.py || true
python scripts/run_benchmarks.py || true
bash scripts/noninterference_check.sh

echo "ALL GREEN"
