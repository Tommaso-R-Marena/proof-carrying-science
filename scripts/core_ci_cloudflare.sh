#!/usr/bin/env bash
# Cloudflare core gate: no deploy, fail on any Lean/runtime/fixture/adversarial failure.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# Emit immutable source identity so a CI log can be tied back to the exact Git commit.
HEAD_SHA="$(git rev-parse HEAD)"
case "$HEAD_SHA" in
  (*[!0-9a-f]*|'') echo "invalid Git HEAD SHA" >&2; exit 8;;
esac
echo "PCS_CORE_HEAD_SHA=$HEAD_SHA"
python3 -m pip install --disable-pip-version-check --require-hashes -r requirements-build.lock -r requirements-dev.lock
python3 -m pip install --disable-pip-version-check --no-deps --no-build-isolation -e .
python3 scripts/check_repository_integrity.py
source scripts/activate_lean_428.sh
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
