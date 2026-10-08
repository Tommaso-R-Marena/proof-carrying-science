#!/usr/bin/env bash
# Cloudflare core gate: no deploy, fail on any Lean/runtime/fixture/adversarial failure.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m pip install --disable-pip-version-check -e '.[dev]'
python3 scripts/check_repository_integrity.py
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
export PATH="$HOME/.elan/bin:$PATH"
bash scripts/verify_lean.sh
cd "$ROOT/formal"
bash tools/run_fixture_tests.sh
lake env lean --run tools/CheckGoldenFileLiterals.lean
lake env lean PCS/V2/FailClosedAudit.lean
cd "$ROOT"
python3 -m pytest -q
python3 scripts/adversarial_campaign.py
python3 scripts/adversarial_v06_hardening.py
echo 'PCS_CORE_CI_FULL_GATE_PASS'
