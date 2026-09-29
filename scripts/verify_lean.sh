#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v lean >/dev/null || { echo "lean not found" >&2; exit 2; }
command -v lake >/dev/null || { echo "lake not found" >&2; exit 2; }
cd "$ROOT/formal"

echo "Lean toolchain:"
lean --version

lake build

# Avoid ambiguous escaped word-boundary regexes. Match identifiers as tokens.
if grep -R --line-number -E '(^|[^[:alnum:]_])(sorry|admit)([^[:alnum:]_]|$)' PCS.lean PCS; then
  echo "ERROR: proof placeholder found in formal PCS source" >&2
  exit 3
fi

# Reject project-level escape hatches or foreign/native declaration shortcuts.
if grep -R --line-number -E '^[[:space:]]*(axiom|unsafe|implemented_by|extern|native_decide)([[:space:]]|$)' PCS.lean PCS; then
  echo "ERROR: forbidden project declaration found in formal PCS source" >&2
  exit 4
fi

echo "Lean kernel build, placeholder audit, and forbidden-declaration audit passed."
