#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m pytest -q
"$PYTHON" experiments/compose_campaign/run_campaign.py
"$PYTHON" -m heck.cli attacks --output results/attacks.json
"$PYTHON" -m heck.cli compose \
  --atoms fixtures/formal_leaf/atoms.json \
  --claim fixtures/formal_leaf/claim.json \
  --output results/formal_leaf.json
"$PYTHON" -m heck.cli compose \
  --atoms fixtures/empirical_leaf/atoms.json \
  --claim fixtures/empirical_leaf/claim.json \
  --output results/empirical_leaf.json
set +e
"$PYTHON" -m heck.cli compose \
  --atoms fixtures/attacks/promote_to_formal/atoms.json \
  --claim fixtures/attacks/promote_to_formal/claim.json \
  --output results/promote_to_formal.json
status=$?
set -e
test "$status" -ne 0
bash scripts/noninterference_check.sh
echo "validate_all ok"
