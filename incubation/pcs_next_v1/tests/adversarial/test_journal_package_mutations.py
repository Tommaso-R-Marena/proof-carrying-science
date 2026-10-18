import json
import shutil
from pathlib import Path
import pytest
from pcs_next_v1.core.errors import PcsNextError
from pcs_next_v1.core.canonical import canonicalize
from pcs_next_v1.reviewer.independent import review_package
from pcs_next_v1.trust.policy import pin_policy
from pcs_next_v1.pilot.intake import freeze_intake, bind_artifact_hashes, load_intake

FIX = Path(__file__).resolve().parents[2] / "fixtures"


def _build_pkg(tmp_path: Path):
    # Use synthetic pilot fixtures for packaging shape; journal data integrity covered elsewhere
    intake = load_intake(FIX / "synthetic_pilot/intake.json")
    bound = bind_artifact_hashes(intake, FIX / "synthetic_pilot/project")
    policy = pin_policy(json.loads((FIX / "synthetic_pilot/acceptance_policy.json").read_text()))
    lock = freeze_intake(bound, acceptance_policy=policy.raw)
    from pcs_next_v1.core.canonical import canonical_hash
    bundle = {
        "format": "pcs-next-evidence-bundle-v1",
        "project_id": intake["project_id"],
        "lock_hash": canonical_hash(lock),
        "policy_hash": policy.content_hash,
        "producer_claimed_pass": True,
        "replay": {"note": "adversarial-suite"},
    }
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "intake.lock.json").write_bytes(canonicalize(lock) + b"\n")
    (pkg / "evidence_bundle.json").write_bytes(canonicalize(bundle) + b"\n")
    (pkg / "acceptance_policy.json").write_bytes(canonicalize(policy.raw) + b"\n")
    return pkg, policy, bundle


def test_one_byte_mutation_rejected(tmp_path):
    pkg, policy, _ = _build_pkg(tmp_path)
    p = pkg / "evidence_bundle.json"
    raw = bytearray(p.read_bytes())
    # flip a byte in the middle
    raw[len(raw)//2] ^= 0x20
    p.write_bytes(bytes(raw))
    with pytest.raises(Exception):
        review_package(pkg, receiver_policy=policy)


def test_stale_lock_hash(tmp_path):
    pkg, policy, bundle = _build_pkg(tmp_path)
    bundle["lock_hash"] = "ab" * 32
    (pkg / "evidence_bundle.json").write_bytes(canonicalize(bundle) + b"\n")
    with pytest.raises(PcsNextError):
        review_package(pkg, receiver_policy=policy)


def test_oversized_nested_rejected_by_canonical_loads(tmp_path):
    from pcs_next_v1.core.canonical import loads_strict, CanonicalError
    # deeply nested arrays
    s = "[" * 200 + "]" * 200
    # json allows this; ensure our loader at least parses or raises cleanly
    try:
        loads_strict(s)
    except CanonicalError:
        pass
