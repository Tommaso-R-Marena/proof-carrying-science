#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v lean >/dev/null || { echo "lean not found" >&2; exit 2; }
command -v lake >/dev/null || { echo "lake not found" >&2; exit 2; }
cd "$ROOT/formal"
lake build
if grep -R --line-number --fixed-strings 'sorry' PCS.lean PCS; then
  echo "ERROR: sorry found in formal source" >&2
  exit 3
fi
echo "Lean kernel build and no-sorry audit passed."
