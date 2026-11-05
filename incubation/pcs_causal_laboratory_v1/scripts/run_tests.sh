#!/usr/bin/env bash
set -euo pipefail
LAB="$(cd "$(dirname "$0")/.." && pwd)"
cd "$LAB"
export PATH="$HOME/.local/bin:$PATH"
if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python -m pip install -e ".[dev]" -q 2>/dev/null || uv pip install -e ".[dev]"
python -m pytest -q
