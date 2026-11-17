#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/.local/lean-4.28.0/bin:${PATH}"
export PYTHONPATH="${ROOT}/python:${ROOT}/independent_checker:${PYTHONPATH:-}"

echo "== Lean =="
(cd "${ROOT}/lean" && lake build)

echo "== pytest =="
python3 -m pytest -q "${ROOT}/tests" "${ROOT}/adversarial"

echo "== case studies =="
python3 "${ROOT}/case_studies/pkpd_synthetic.py"
python3 "${ROOT}/case_studies/causal_identification.py"

echo "== benchmarks =="
python3 "${ROOT}/benchmarks/reproduce.py"

echo "== isolation =="
python3 "${ROOT}/scripts/check_isolation.py"

echo "== axiom audit (no sorryAx in CheckCertificate) =="
grep -R "sorryAx" "${ROOT}/results/lean_build_phase2.log" && exit 1 || echo "no sorryAx in phase2 build log"

echo "ALL_OK"
