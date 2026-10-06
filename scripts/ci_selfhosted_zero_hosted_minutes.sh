#!/usr/bin/env bash
# Optional zero-GitHub-hosted-minute PCS CI for an owner-controlled Linux runner.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null || { echo "Python 3 required" >&2; exit 2; }
command -v lean >/dev/null || { echo "Lean + elan required (see lean-toolchain)" >&2; exit 2; }
command -v lake >/dev/null || { echo "Lake required" >&2; exit 2; }
python3 scripts/check_repository_integrity.py
python3 -m venv .pcs-ci-venv
source .pcs-ci-venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/adversarial_campaign.py
python scripts/adversarial_v06_hardening.py
bash scripts/verify_lean.sh
printf '%s\n' "PCS integrity + Python + adversarial + Lean gate passed on an owner-controlled machine."
