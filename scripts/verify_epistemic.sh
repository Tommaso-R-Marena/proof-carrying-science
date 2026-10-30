#!/usr/bin/env bash
# Isolated build + axiom audit for the research epistemic stratification library.
# Does not touch production PCS Lean authority.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/activate_lean_428.sh"
python3 - <<'PY'
from pcs.epistemic_kernel_v1 import kernel_audit, run_campaign, lattice_self_check
import json
lattice = lattice_self_check()
assert lattice["passed"], lattice
campaign = run_campaign()
assert campaign["passed"], {k: v for k, v in campaign["cases"].items() if not v}
audit = kernel_audit(timeout=120)
assert audit.get("accepted"), audit
print(json.dumps({
    "lattice_cases": lattice["case_count"],
    "campaign_passed": campaign["passed"],
    "lean_accepted": audit["accepted"],
    "theorem_count": len(audit.get("inventory", {})),
    "scientific_acceptance": False,
}, indent=2))
PY
