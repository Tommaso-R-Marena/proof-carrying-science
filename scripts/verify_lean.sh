#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v lean >/dev/null || { echo "lean not found" >&2; exit 2; }
command -v lake >/dev/null || { echo "lake not found" >&2; exit 2; }
cd "$ROOT/formal"

echo "Lean toolchain:"
lean --version

lake build
# Keep expensive controls apart from the authority build to bound peak memory.
lake build PCSControls

# Avoid ambiguous escaped word-boundary regexes. Match identifiers as tokens.
python "$ROOT/scripts/audit_lean_source.py" PCS.lean PCS PCSAuthority.lean PCSSemanticCheck.lean PCSCountermodel.lean PCSCountermodel PCSCountermodelReplay.lean
python "$ROOT/scripts/verify_countermodel_formal.py"
python "$ROOT/scripts/verify_omega_dd_formal.py"

echo "Lean kernel build, placeholder audit, and forbidden-declaration audit passed."
