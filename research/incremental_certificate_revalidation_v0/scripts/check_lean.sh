#!/usr/bin/env bash
# Rebuild the PCSIncremental Lean library (must stay green).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORMAL="$ROOT/formal"
LOG="$ROOT/results/lean_build.log"

export PATH="${HOME}/.local/lean-4.28.0/bin:${PATH}"

mkdir -p "$ROOT/results"
cd "$FORMAL"

{
  echo "lean=$(lean --version 2>&1 | head -1)"
  echo "lake=$(lake --version 2>&1 | head -1)"
  echo "cwd=$(pwd)"
  lake build
} 2>&1 | tee "$LOG"

# Forbid actual sorry/admit *commands*, not documentation mentions.
# Match only as a statement token (start of content after optional whitespace).
if command -v rg >/dev/null; then
  if rg -n --glob '*.lean' -e '^[[:space:]]*sorry\b' -e '^[[:space:]]*admit\b' \
      PCSIncremental PCSIncremental.lean; then
    echo "forbidden sorry/admit found" >&2
    exit 1
  fi
fi

echo "Lean build OK — log at $LOG"
