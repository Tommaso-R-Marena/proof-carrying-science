import json
from pathlib import Path
import pytest
from pcs_next_v1.core.canonical import canonicalize
from pcs_next_v1.core.errors import PcsNextError
from pcs_next_v1.pilot.intake import freeze_intake, load_intake, bind_artifact_hashes
from pcs_next_v1.reviewer.independent import review_package
from pcs_next_v1.trust.policy import pin_policy

FIX = Path(__file__).resolve().parents[2] / "fixtures/synthetic_pilot"

def _pkg(tmp_path, mutate_bundle=None, mutate_policy=None):
    intake = load_intake(FIX/"intake.json")
    bound = bind_artifact_hashes(intake, FIX/"project")
    policy = pin_policy(json.loads((FIX/"acceptance_policy.json").read_text()))
    lock = freeze_intake(bound, acceptance_policy=policy.raw)
    bundle = {
        "format": "pcs-next-evidence-bundle-v1",
        "project_id": intake["project_id"],
        "lock_hash": __import__("pcs_next_v1.core.canonical", fromlist=["canonical_hash"]).canonical_hash(lock),
        "policy_hash": policy.content_hash,
        "producer_claimed_pass": True,
        "replay": {},
    }
    if mutate_bundle:
        mutate_bundle(bundle)
    pol = dict(policy.raw)
    if mutate_policy:
        mutate_policy(pol)
        # keep hash wrong intentionally sometimes
    pkg = tmp_path / "p"
    pkg.mkdir()
    (pkg/"intake.lock.json").write_bytes(canonicalize(lock)+b"\n")
    (pkg/"evidence_bundle.json").write_bytes(canonicalize(bundle)+b"\n")
    (pkg/"acceptance_policy.json").write_bytes(canonicalize(pol)+b"\n")
    return pkg, policy

def test_policy_swap(tmp_path):
    pkg, policy = _pkg(tmp_path, mutate_policy=lambda p: p.__setitem__("policy_version", "0.0.1"))
    with pytest.raises(PcsNextError):
        review_package(pkg, receiver_policy=policy)

def test_hash_mismatch(tmp_path):
    pkg, policy = _pkg(tmp_path, mutate_bundle=lambda b: b.__setitem__("lock_hash", "0"*64))
    with pytest.raises(PcsNextError):
        review_package(pkg, receiver_policy=policy)

def test_truncated(tmp_path):
    pkg, policy = _pkg(tmp_path)
    p = pkg/"evidence_bundle.json"
    p.write_bytes(p.read_bytes()[:20])
    with pytest.raises(Exception):
        review_package(pkg, receiver_policy=policy)

def test_duplicate_keys(tmp_path):
    from pcs_next_v1.core.canonical import loads_strict, CanonicalError
    with pytest.raises(CanonicalError):
        loads_strict(b'{"a":1,"a":2}')

def test_missing_member(tmp_path):
    pkg, policy = _pkg(tmp_path)
    (pkg/"evidence_bundle.json").unlink()
    with pytest.raises(PcsNextError):
        review_package(pkg, receiver_policy=policy)

def test_producer_pass_ignored_but_ok(tmp_path):
    pkg, policy = _pkg(tmp_path)
    receipt = review_package(pkg, receiver_policy=policy)
    assert receipt["producer_verdict_handling"]["receiver_action"] == "IGNORED"
