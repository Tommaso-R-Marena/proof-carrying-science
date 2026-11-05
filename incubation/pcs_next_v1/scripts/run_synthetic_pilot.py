#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))

from pcs_next_v1.core.canonical import canonicalize
from pcs_next_v1.pilot.runner import PilotRunner
from pcs_next_v1.reviewer.assurance_card import export_card
from pcs_next_v1.reviewer.independent import review_package
from pcs_next_v1.trust.policy import pin_policy


def main() -> int:
    fixtures = ROOT / "fixtures" / "synthetic_pilot"
    work = ROOT / "results" / "synthetic_pilot_run"
    work.mkdir(parents=True, exist_ok=True)
    intake = json.loads((fixtures / "intake.json").read_text())
    policy = pin_policy(json.loads((fixtures / "acceptance_policy.json").read_text()))
    runner = PilotRunner(work, policy=policy, repo_root=REPO)
    report = runner.run_synthetic(fixtures / "project", intake)
    # package for reviewer
    pkg = work / "package"
    pkg.mkdir(exist_ok=True)
    for name in ("intake.lock.json", "evidence_bundle.json"):
        (pkg / name).write_bytes((work / name).read_bytes())
    (pkg / "acceptance_policy.json").write_bytes(canonicalize(policy.raw) + b"\n")
    receipt = review_package(pkg, receiver_policy=policy)
    card = export_card(report, work / "card")
    summary = {
        "report_status_independent": report["statuses"]["independent"]["status"],
        "receipt_status": receipt["status"],
        "external_lab": report["external_lab_validation"]["status"],
        "card": str(work / "card" / "assurance_card.html"),
    }
    (work / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
