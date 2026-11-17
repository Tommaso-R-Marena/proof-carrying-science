#!/usr/bin/env bash
# Replayable local qualification for Proof-Carrying Causal Reasoning v1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
export PYTHONDONTWRITEBYTECODE=1

echo "== unit tests =="
python3 -m unittest discover -s research/proof_carrying_causal_reasoning_v1/tests -v

echo "== controls + oracle =="
OUT="research/proof_carrying_causal_reasoning_v1/results/check-all-$$"
python3 -m research.proof_carrying_causal_reasoning_v1 all --out "$OUT"

echo "== lean =="
if command -v lake >/dev/null 2>&1; then
  (cd research/proof_carrying_causal_reasoning_v1/lean && lake build)
else
  echo "lake not on PATH; skipping Lean build (activate scripts/activate_lean_428.sh)"
fi

echo "OK: $OUT"
