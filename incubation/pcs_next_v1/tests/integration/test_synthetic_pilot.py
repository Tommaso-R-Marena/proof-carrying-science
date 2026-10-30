import json
from pathlib import Path
from pcs_next_v1.pilot.runner import PilotRunner
from pcs_next_v1.trust.policy import pin_policy
from pcs_next_v1.reviewer.independent import review_package
from pcs_next_v1.core.canonical import canonicalize

FIX = Path(__file__).resolve().parents[2] / "fixtures/synthetic_pilot"
REPO = Path(__file__).resolve().parents[4]

def test_end_to_end(tmp_path):
    intake = json.loads((FIX/"intake.json").read_text())
    policy = pin_policy(json.loads((FIX/"acceptance_policy.json").read_text()))
    runner = PilotRunner(tmp_path, policy=policy, repo_root=REPO)
    report = runner.run_synthetic(FIX/"project", intake)
    assert report["external_lab_validation"]["status"] == "OPEN"
    assert report["statuses"]["independent"]["status"] == "INDEPENDENTLY_REPRODUCED"
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg/"intake.lock.json").write_bytes((tmp_path/"intake.lock.json").read_bytes())
    (pkg/"evidence_bundle.json").write_bytes((tmp_path/"evidence_bundle.json").read_bytes())
    (pkg/"acceptance_policy.json").write_bytes(canonicalize(policy.raw)+b"\n")
    receipt = review_package(pkg, receiver_policy=policy)
    assert receipt["status"] == "INDEPENDENTLY_REPRODUCED"
