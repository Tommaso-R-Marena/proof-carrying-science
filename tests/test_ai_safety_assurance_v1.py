from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from pcs import action_shield_v1 as shield
from pcs import ai_safety_assurance_v1 as assurance
from pcs.canonical_json import canonicalize_jcs_bytes as encode
from pcs.signing import generate_keypair

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    model = encode({"format": shield.MODEL_FORMAT, "states": [0, 1, 2], "actions": [0, 1, 2],
        "initial": [0], "safe": [0, 1], "forbidden": [2],
        "transitions": [{"source": 0, "action": 0, "target": 1}, {"source": 0, "action": 1, "target": 2},
                        {"source": 1, "action": 0, "target": 0}],
        "assumptions": [{"id": x, "statement": "Explicit deployment correspondence premise.", "status": "OPEN"}
                        for x in ("model_completeness", "shield_enforcement", "state_observation")]})
    cert = encode(shield.propose(model))
    return model, cert, encode(assurance.guard_task(model, cert))


def test_guard_substitution_checks_complete_boolean_and_model_domains():
    model, cert, guard = inputs()
    result = assurance.replay(model, cert, guard)
    assert result["model"]["outcome"] == result["guard"]["outcome"] == "PASS"
    assert result["guard"]["complete_state_action_domain_checked"] == 9
    bad = json.loads(guard)
    bad["candidate"] = {"op": "true"}
    result = assurance.replay(model, cert, encode(bad))
    assert result["guard"]["outcome"] == "FAIL" and [0, 1] in result["guard"]["mismatches"]


def test_nonvacuous_reference_and_empty_premises_are_binding():
    model, cert, guard = inputs()
    for update in ({"source": {"op": "true"}}, {"assumptions": [{"op": "false"}]}):
        bad = json.loads(guard)
        bad.update(update)
        with pytest.raises(assurance.ShieldAssuranceError, match="reference or context"):
            assurance.replay(model, cert, encode(bad))


def test_actual_guarded_proposals_reject_unlisted_and_unsafe_actions():
    model, cert, guard = inputs()
    assert assurance.admit_guarded_action(model, cert, guard, 0, 0) is True
    assert assurance.admit_guarded_action(model, cert, guard, 1, 0) is True
    assert assurance.admit_guarded_action(model, cert, guard, 0, 1) is False
    assert assurance.admit_guarded_action(model, cert, guard, 99, 0) is False
    assert assurance.admit_guarded_action(model, cert, guard, 0, 99) is False
    bad = json.loads(guard)
    bad["candidate"] = {"op": "true"}
    assert assurance.admit_guarded_action(model, cert, encode(bad), 0, 0) is False
    with pytest.raises(assurance.ShieldAssuranceError, match="exact integer"):
        assurance.admit_guarded_action(model, cert, guard, True, 0)


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    path = tmp_path_factory.mktemp("shield-package")
    for name, raw in zip(("model", "shield", "guard"), inputs()):
        (path / (name + ".json")).write_bytes(raw)
    private, public = path / "secret.pem", path / "public.pem"
    fingerprint = generate_keypair(private, public)["fingerprint"]
    result = assurance.build_bundle(path / "model.json", path / "shield.json", path / "guard.json",
        path / "work", path / "positive.zip", private, public, expected_fingerprint=fingerprint)
    assert result["bounded_assurance_satisfied"], result
    return {"path": path, "private": private, "public": public, "fingerprint": fingerprint}


def test_exact_model_kernel_support_is_separate_from_base_open_and_deployment(package):
    r = assurance.verify_bundle(package["path"] / "positive.zip", package["public"], expected_fingerprint=package["fingerprint"])
    assert r["bounded_assurance_satisfied"] and r["kernel_replay"]["kernel_checked"]
    assert {x["decision"] for x in r["pcs_verification"]["claims"]} == {"OPEN"}
    assert r["deployment_safety"] == r["liveness"] == "OPEN" and not r["scientific_acceptance"]
    assert not r["producer_proof_trusted"] and not r["independent_human_review"]
    assert next(x for x in r["obligations"]["nodes"] if x["id"] == "model_invariant")["status"] == "FORMALLY_SUPPORTED"


@pytest.mark.parametrize("mutation", ["false-report", "proof-injection", "missing-source", "changed-premise", "weakened-claim"])
def test_authentically_resigned_false_or_misbinding_packages_reject(package, mutation):
    from pcs.attest_v06 import build_attestation_directory_v06
    from pcs.bundle_v06 import create_verified_bundle_v06
    path = package["path"]
    stage = path / mutation
    shutil.copytree(path / "work/project", stage)
    manifest_file = stage / "manifest.confirmed.json"
    manifest = json.loads(manifest_file.read_bytes())
    if mutation == "false-report":
        report_file = stage / assurance.FILES["replay"]
        report = json.loads(report_file.read_bytes())
        report["guard"]["complete_state_action_domain_checked"] = 0
        report_file.write_bytes(encode(report))
    elif mutation == "proof-injection":
        (stage / assurance.PREFIX / "proof.lean.txt").write_text("axiom forged : False\n")
    elif mutation == "missing-source":
        manifest["artifacts"] = [x for x in manifest["artifacts"] if x["path"] != "guard.json"]
    elif mutation == "changed-premise":
        manifest["assumptions"][0]["statement"] = "An unmodeled tool outcome exists."
    else:
        manifest["claims"][0]["predicate"]["proposition"] = "True"
    for item in manifest["artifacts"]:
        raw = (stage / item["path"]).read_bytes()
        item["metadata"]["pcs_discovery_sha256"] = hashlib.sha256(raw).hexdigest()
        item["metadata"]["pcs_discovery_size"] = len(raw)
    manifest_file.write_bytes(encode(manifest))
    artifact = path / (mutation + ".zip")
    build_attestation_directory_v06(manifest_file, path / (mutation + "-package"), package["private"], package["public"],
        expected_fingerprint=package["fingerprint"], generated_at="2026-10-14T00:00:00+00:00")
    create_verified_bundle_v06(path / (mutation + "-package"), artifact, package["public"], expected_fingerprint=package["fingerprint"])
    r = assurance.verify_bundle(artifact, package["public"], expected_fingerprint=package["fingerprint"])
    assert r["pcs_package_valid"] and not r["independent_replay_consistent"] and not r["formal_model_supported"]


def test_missing_or_failed_kernel_cannot_be_replaced_by_a_signed_proof(package, monkeypatch):
    monkeypatch.setattr(shield, "kernel_replay", lambda *args: {"kernel_checked": False, "status": "UNAVAILABLE_OR_EXHAUSTED"})
    r = assurance.verify_bundle(package["path"] / "positive.zip", package["public"], expected_fingerprint=package["fingerprint"])
    assert r["pcs_package_valid"] and r["independent_replay_consistent"] and not r["bounded_assurance_satisfied"]


def test_separate_receiving_process_and_immutable_output(package):
    output = package["path"] / "separate-receiver.json"
    cmd = [sys.executable, "-m", "pcs.ai_safety_assurance_v1", str(package["path"] / "positive.zip"),
           "--public-key", str(package["public"]), "--fingerprint", package["fingerprint"], "--output", str(output)]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode()
    assert json.loads(output.read_bytes())["formal_model_supported"]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=120)
    assert p.returncode != 0 and b"output must be new" in p.stderr
