#!/usr/bin/env bash
# Build and audit the Mathlib-based real-analysis bridge (`formal/real/PCSReal`).
# The bridge is proof-only: it is not linked into `pcs-lean-authority`.  It is built from
# the repository root, whose lakefile requires Mathlib and the PCS kernel (`formal/`).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
lake build PCSReal
if grep -R --line-number -E '(^|[^[:alnum:]_])(sorry|admit)([^[:alnum:]_]|$)' formal/real; then
  echo "ERROR: proof placeholder found in formal/real" >&2
  exit 3
fi
if grep -R --line-number -E '^[[:space:]]*(axiom|unsafe|implemented_by|extern|native_decide)([[:space:]]|$)' formal/real; then
  echo "ERROR: forbidden declaration found in formal/real" >&2
  exit 4
fi
echo "Real-analysis bridge build and audits passed."
