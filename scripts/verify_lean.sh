#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v lean >/dev/null || { echo "lean not found" >&2; exit 2; }
command -v lake >/dev/null || { echo "lake not found" >&2; exit 2; }
cd "$ROOT/formal"

echo "Lean toolchain:"
lean --version

lake build

if grep -R --line-number -E '\\b(sorry|admit)\\b' PCS.lean PCS; then
  echo "ERROR: proof placeholder found in formal PCS source" >&2
  exit 3
fi

if grep -R --line-number -E '^[[:space:]]*(axiom|unsafe)[[:space:]]' PCS.lean PCS; then
  echo "ERROR: project axiom/unsafe declaration found in formal PCS source" >&2
  exit 4
fi

echo "Lean kernel build, placeholder audit, and project-axiom audit passed."
