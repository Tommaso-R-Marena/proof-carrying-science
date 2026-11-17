#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/.local/lean-4.28.0/bin:${PATH}"
export PYTHONPATH="${ROOT}/python:${ROOT}/independent_checker:${PYTHONPATH:-}"

echo "== Lean =="
(cd "${ROOT}/lean" && lake build)

echo "== pytest =="
python3 -m pytest -q "${ROOT}/tests" "${ROOT}/adversarial"

echo "== case study =="
python3 "${ROOT}/case_studies/pkpd_synthetic.py"

echo "== isolation =="
python3 "${ROOT}/scripts/check_isolation.py"

echo "ALL_OK"
