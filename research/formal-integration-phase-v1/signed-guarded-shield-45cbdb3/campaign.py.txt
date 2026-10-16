"""Build and independently receive a signed finite-model safety case.

Uses a temporary experimental signing key; only its public key is retained.
All receiver runs use a new process and regenerate their own kernel proof.
This is a first-party synthetic tool-use case, with deployment premises OPEN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pcs import ai_safety_assurance_v1 as assurance
from pcs.attest_v06 import build_attestation_directory_v06
from pcs.bundle_v06 import create_verified_bundle_v06
from pcs.canonical_json import canonicalize_jcs_bytes as encode
from pcs.signing import generate_keypair


def run(output: Path):
    output = output.resolve()
    if output.exists():
        raise ValueError("new evidence directory required")
    output.mkdir(parents=True)
    started = time.monotonic()
    example = ROOT / "examples/action_shield_v1"
    model_path, shield_path, guard_path = (output / x for x in ("model.json", "shield.json", "guard.json"))
    model_path.write_bytes((example / "model.json").read_bytes())
    shield_path.write_bytes((example / "shield.json").read_bytes())
    guard_path.write_bytes(encode(assurance.guard_task(model_path.read_bytes(), shield_path.read_bytes())))
    public = output / "producer-public.pem"
    receivers = []
    with tempfile.TemporaryDirectory(prefix="pcs-shield-experimental-key-") as key_directory, tempfile.TemporaryDirectory(prefix="pcs-shield-package-work-") as work_directory:
        private = Path(key_directory) / "secret.pem"
        fingerprint = generate_keypair(private, public)["fingerprint"]
        work = Path(work_directory) / "positive-work"
        positive = output / "positive.pcs.zip"
        producer = assurance.build_bundle(model_path, shield_path, guard_path, work, positive, private, public, expected_fingerprint=fingerprint)
        if not producer["bounded_assurance_satisfied"]:
            raise RuntimeError(producer["errors"])

        def receive(label, bundle, expected):
            target = output / (label + "-receiver.json")
            command = [sys.executable, "-m", "pcs.ai_safety_assurance_v1", str(bundle), "--public-key", str(public),
                       "--fingerprint", fingerprint, "--output", str(target)]
            p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
            (output / (label + "-receiver.log")).write_text(p.stdout + p.stderr)
            if not target.exists():
                raise RuntimeError("receiver did not publish a result: " + label)
            result = json.loads(target.read_bytes())
            if result["bounded_assurance_satisfied"] != expected or (p.returncode == 0) != expected:
                raise RuntimeError("unexpected receiver outcome: " + label)
            if not result["pcs_package_valid"]:
                raise RuntimeError("signed attack did not pass package integrity: " + label)
            receivers.append({"id": label, "returncode": p.returncode, "bundle_sha256": assurance.sha(bundle.read_bytes()),
                "pcs_package_valid": result["pcs_package_valid"], "formal_model_supported": result["formal_model_supported"],
                "bounded_assurance_satisfied": result["bounded_assurance_satisfied"], "expected": expected,
                "deployment_safety": result["deployment_safety"], "scientific_acceptance": result["scientific_acceptance"]})

        receive("positive", positive, True)
        for mutation in ("false-report", "bool-number-report", "source-substitution", "proof-injection", "missing-artifact", "changed-premise", "weakened-claim"):
            stage = Path(work_directory) / mutation
            shutil.copytree(work / "project", stage)
            manifest_path = stage / "manifest.confirmed.json"
            manifest = json.loads(manifest_path.read_bytes())
            if mutation in {"false-report", "bool-number-report"}:
                path = stage / assurance.FILES["replay"]
                report = json.loads(path.read_bytes())
                if mutation == "false-report":
                    report["guard"]["complete_state_action_domain_checked"] = 0
                else:
                    report["scientific_acceptance"] = 0
                path.write_bytes(encode(report))
            elif mutation == "source-substitution":
                (stage / assurance.PREFIX / "sources/pcs/experimental/conditional.py.txt").write_text("raise RuntimeError('producer source must never execute')\n")
            elif mutation == "proof-injection":
                (stage / assurance.PREFIX / "proof.lean.txt").write_text("axiom forged : False\n")
            elif mutation == "missing-artifact":
                manifest["artifacts"] = [x for x in manifest["artifacts"] if x["path"] != "guard.json"]
            elif mutation == "changed-premise":
                manifest["assumptions"][0]["statement"] = "Some actual tool outcomes are missing."
            else:
                manifest["claims"][0]["predicate"]["proposition"] = "True"
            for item in manifest["artifacts"]:
                raw = (stage / item["path"]).read_bytes()
                item["metadata"]["pcs_discovery_sha256"] = assurance.sha(raw)
                item["metadata"]["pcs_discovery_size"] = len(raw)
            manifest_path.write_bytes(encode(manifest))
            package, bundle = Path(work_directory) / (mutation + "-package"), output / (mutation + ".pcs.zip")
            build_attestation_directory_v06(manifest_path, package, private, public, expected_fingerprint=fingerprint,
                generated_at="2026-10-14T00:00:00+00:00")
            create_verified_bundle_v06(package, bundle, public, expected_fingerprint=fingerprint)
            receive(mutation, bundle, False)
    summary = {"format": "pcs-action-shield-assurance-campaign-v1", "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "producer_public_fingerprint": fingerprint, "case_origin": "first-party synthetic tool-use model; not deployed observations",
        "receivers": receivers, "wall_seconds": round(time.monotonic() - started, 6),
        "separate_receiving_processes": len(receivers), "private_key_retained": False, "scientific_acceptance": False,
        "deployment_safety": "OPEN", "independent_external_review": False, "training_authorization": False}
    (output / "SUMMARY.json").write_bytes(encode(summary) + b"\n")
    (output / "receiver.py.txt").write_bytes((ROOT / "pcs/ai_safety_assurance_v1.py").read_bytes())
    (output / "campaign.py.txt").write_bytes(Path(__file__).read_bytes())
    seal = {str(p.relative_to(output)): assurance.sha(p.read_bytes()) for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "ARTIFACT_SHA256.json").write_bytes(encode({"format": "pcs-unsigned-byte-inventory-v1", "files": seal}) + b"\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    result = run(parser.parse_args().output)
    print(encode({"cases": len(result["receivers"]), "all_expected": True, "scientific_acceptance": False}).decode())
