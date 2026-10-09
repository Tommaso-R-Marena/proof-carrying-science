#!/usr/bin/env bash
# Build and audit the Mathlib-based real-analysis bridge (`formal/real/PCSReal`).
# The bridge is proof-only: it is not linked into `pcs-lean-authority`.  It is built from
# the repository root, whose lakefile requires Mathlib and the PCS kernel (`formal/`).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
lake build PCSReal
python "$ROOT/scripts/audit_lean_source.py" formal/real
echo "Real-analysis bridge build and audits passed."
