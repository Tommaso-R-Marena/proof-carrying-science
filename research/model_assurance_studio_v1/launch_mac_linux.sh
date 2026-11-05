#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -f .venv/bin/python ]; then python3 -m venv .venv; fi
if [ ! -f .venv/pcs_dependencies_installed.txt ]; then
  .venv/bin/python -m pip install -r requirements.txt
  printf 'Installed\n' > .venv/pcs_dependencies_installed.txt
fi
.venv/bin/python launch.py
