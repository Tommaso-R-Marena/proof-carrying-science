#!/usr/bin/env bash
# Build HECK Lean and reject sorry/admit in owned sources.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FORMAL="$(cd "$SCRIPT_DIR/../formal" && pwd)"
cd "$FORMAL"
if ! command -v lake >/dev/null 2>&1; then
  echo "lake not on PATH; source PCS scripts/activate_lean_428.sh first" >&2
  exit 2
fi
lake build
if grep -R --include='*.lean' -nE '\bsorry\b|\badmit\b' PCSCompose PCSCompose.lean; then
  echo "sorry/admit found in HECK Lean sources" >&2
  exit 1
fi
echo "axiom audit ok: lake build clean; no sorry/admit"
