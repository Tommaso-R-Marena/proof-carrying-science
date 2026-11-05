#!/usr/bin/env python3
"""Run the frozen, credential-free synthetic scientific-assurance experiment.

Only the explicitly authored example script is executed. No untrusted project
code, remote resource, production secret, paid service or personal data is used.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives import serialization
from pcs.attest_v06 import build_attestation_directory_v06
from pcs.bundle_v06 import create_verified_bundle_v06
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.external_validator_v06 import build_external_validator_receipt_payload_v06, sign_external_validator_receipt_v06
from pcs.jsonio import strict_json_load
from pcs.scientific_assurance_v1 import build_scientific_bundle, render_scientific_receipt_html
from pcs.scientific_contracts_v1 import evaluate
from pcs.scientific_obligations_v1 import make_plan, resolve_plan, new_review_revision, unsupported_claim_diagnostics
from pcs.scientific_research_v1 import investigate_scientific_contract
from pcs.signing import generate_keypair


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write(path: Path, value) -> None:
    if path.exists():
        raise RuntimeError("refusing to overwrite frozen experiment evidence")
    path.write_bytes(canonicalize_jcs_bytes(value))


def independently_replay(bundle: Path, public: Path, fingerprint: str, output: Path) -> dict:
    completed = subprocess.run([sys.executable, str(ROOT / "scripts/replay_scientific_bundle_v1.py"),
        str(bundle), str(public), "--expected-fingerprint", fingerprint, "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=120)
    if completed.returncode != 0:
        raise RuntimeError("fresh-process scientific replay rejected: " + completed.stderr[-2000:])
    return strict_json_load(output)


def run(output: Path) -> dict:
    if output.exists():
        raise RuntimeError("output directory must be new; historical evidence is immutable")
    output.mkdir(parents=True)
    started = time.perf_counter()
    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    source_paths = ["pcs/scientific_assurance_v1.py", "pcs/scientific_contracts_v1.py",
        "pcs/scientific_obligations_v1.py", "pcs/scientific_research_v1.py",
        "scripts/run_scientific_assurance_v1.py", "scripts/replay_scientific_bundle_v1.py",
        "examples/scientific_mass_action/model.json", "examples/scientific_mass_action/run_workflow.py"]
    protocol = {"format": "pcs-scientific-experiment-protocol-v1", "frozen_before_execution": True,
        "source_sha256": {name: sha((ROOT / name).read_bytes()) for name in source_paths},
        "domain": "authored CC0 synthetic three-species two-reaction mass-action model",
        "question_grounding": "free text retained; typed contract alone determines the checked obligations",
        "comparison": "deterministic dependency planner baseline; no learned-policy or scientific-discovery advantage claimed",
        "expected_positive": "all eight finite predicates pass; compiled builtin certificate accepted; numerical PCS claim OPEN",
        "expected_negative": ["mass leak fails conservation/reference", "producer-signed false replay report rejected by receiver",
            "premise change invalidates transitive dependent results", "clinical English remains OPEN"],
        "limits": {"steps": 128, "species": 16, "reactions": 32, "fraction_bits": 4096, "replay_process_seconds": 120},
        "license": "CC0-1.0", "human_participants": 0, "private_data": False, "financial_spend": 0,
        "private_keys_exported": False, "kernel_refinement_of_numerical_adapter": False,
        "deterministic_archive_parameter": "2026-10-12T00:00:00+00:00 (declared parameter, not actual execution time)",
        "archive_reproduction": "same key/inputs/timestamp yield identical ZIPs; a new random key changes signed bytes"}
    write(output / "PROTOCOL.json", protocol)
    invocations = []
    def audit(event, args):
        if event == "subprocess.Popen":
            executable, command = args[0], args[1]
            invocations.append({"executable": Path(executable).name,
                "kind": "lean_authority" if Path(executable).name == "pcs-lean-authority" else "explicit_authored_workflow_or_independent_replay"})
    sys.addaudithook(audit)
    with tempfile.TemporaryDirectory(prefix="pcs-scientific-experiment-") as temporary:
        temp = Path(temporary)
        project = temp / "authored-workflow"
        shutil.copytree(ROOT / "examples/scientific_mass_action", project)
        # Approved authored source, independent of the PCS implementation.
        subprocess.run([sys.executable, "run_workflow.py"], cwd=project, check=True, timeout=10)
        model_raw = (project / "model.json").read_bytes()
        observations = (project / "observations.csv").read_bytes()
        (output / "observations.csv").write_bytes(observations)
        (output / "model.json").write_bytes(model_raw)
        private, public = temp / "ephemeral-private.pem", output / "producer-public.pem"
        fingerprint = generate_keypair(private, public)["fingerprint"]
        positive = output / "positive.pcs.zip"
        built = build_scientific_bundle(project, temp / "positive-work", positive, private, public,
            expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
        repeated = temp / "positive-repeated.pcs.zip"
        repeated_result = build_scientific_bundle(project, temp / "positive-repeated-work", repeated, private, public,
            expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
        assert positive.read_bytes() == repeated.read_bytes()
        positive_receipt = independently_replay(positive, public, fingerprint, output / "positive-independent-replay.json")
        assert positive_receipt["bounded_contract_satisfied"] is True
        statuses = {x["claim_id"]: x["decision"] for x in positive_receipt["pcs_verification"]["claims"]}
        assert statuses["C_NUMERICAL"] == "OPEN"
        (output / "REPORT.html").write_text(render_scientific_receipt_html(positive_receipt), encoding="utf-8")
        failed = temp / "failed-workflow"
        shutil.copytree(project, failed)
        rows = observations.decode().splitlines()
        cells = rows[-1].split(",")
        cells[1] = "100"
        rows[-1] = ",".join(cells)
        failed_observations = ("\n".join(rows) + "\n").encode()
        (failed / "observations.csv").write_bytes(failed_observations)
        negative = output / "mass-leak.pcs.zip"
        negative_result = build_scientific_bundle(failed, temp / "failed-work", negative, private, public,
            expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
        failed_receipt = independently_replay(negative, public, fingerprint, output / "mass-leak-independent-replay.json")
        assert failed_receipt["domain_replay"]["outcome"] == "FAIL" and not failed_receipt["bounded_contract_satisfied"]
        investigator = investigate_scientific_contract(model_raw, failed_observations, allow_reference_proposal=True)
        assert investigator["original_outcome"] == "FAIL" and investigator["proposals"][0]["outcome"] == "PASS"
        write(output / "bounded-investigation.json", investigator)
        original_plan = make_plan(strict_json_load(project / "model.json"), contract_artifact_sha256=sha(model_raw))
        original_results = resolve_plan(original_plan, positive_receipt["domain_replay"])
        changed_plan = deepcopy(original_plan)
        changed_plan["nodes"][0]["statement"] = "The compartment now exchanges mass with an unmodeled environment."
        changed = resolve_plan(changed_plan, positive_receipt["domain_replay"], previous=original_results)
        assert next(x for x in changed["nodes"] if x["id"] == "workflow")["status"] == "INVALIDATED"
        write(output / "premise-invalidation.json", {"original": original_results, "revised": changed})
        review1 = new_review_revision(previous=None, evidence_sha256=sha(positive.read_bytes()),
            reviewer_id="authored-synthetic-fixture", decisions=[{"obligation_id": "workflow", "type": "assumptions",
                "message": "Closed volume is an explicit premise, not an observed fact."}])
        review2 = new_review_revision(previous=review1, evidence_sha256=sha(positive.read_bytes()),
            reviewer_id="authored-synthetic-fixture", decisions=[{"obligation_id": "biological_adequacy", "type": "reject",
                "message": "No independent domain validation is present."}])
        write(output / "review-fixture-revisions.json", [review1, review2])
        write(output / "unsupported-clinical-claim.json", unsupported_claim_diagnostics("This model is always safe for every possible patient."))
        # Deliberately sign a false report with the legitimate ephemeral producer
        # key, showing why a valid signature cannot replace numerical replay.
        forged_project = temp / "producer-false-report"
        shutil.copytree(temp / "positive-work/project", forged_project)
        report_path = forged_project / "pcs-scientific/domain-replay.json"
        false_report = strict_json_load(report_path)
        false_report["resources"]["reaction_step_evaluations"] = 0
        report_path.write_bytes(canonicalize_jcs_bytes(false_report))
        manifest_path = forged_project / "manifest.confirmed.json"
        manifest = strict_json_load(manifest_path)
        spec = strict_json_load(forged_project / "pcs-scientific/numerical-spec.json")
        artifact_map = {x["id"]: x for x in manifest["artifacts"]}
        bound = {ident: (forged_project / artifact_map[ident]["path"]).read_bytes() for ident in spec["bound_artifact_ids"]}
        payload = build_external_validator_receipt_payload_v06(check_type=spec["type"], validator=spec["validator"],
            predicate=spec["predicate"], bound_artifact_ids=spec["bound_artifact_ids"], artifact_bytes=bound, outcome="PASS")
        key = serialization.load_pem_private_key(private.read_bytes(), password=None)
        (forged_project / artifact_map[spec["receipt_artifact"]]["path"]).write_bytes(canonicalize_jcs_bytes(sign_external_validator_receipt_v06(payload, key)))
        for artifact in manifest["artifacts"]:
            raw = (forged_project / artifact["path"]).read_bytes()
            artifact["metadata"].update(pcs_discovery_sha256=sha(raw), pcs_discovery_size=len(raw))
        manifest_path.write_bytes(canonicalize_jcs_bytes(manifest))
        false_package = temp / "false-package"
        build_attestation_directory_v06(manifest_path, false_package, private, public, expected_fingerprint=fingerprint,
            generated_at="2026-10-12T00:00:00+00:00")
        false_bundle = output / "producer-signed-false-report.pcs.zip"
        create_verified_bundle_v06(false_package, false_bundle, public, expected_fingerprint=fingerprint)
        rejected = subprocess.run([sys.executable, str(ROOT / "scripts/replay_scientific_bundle_v1.py"), str(false_bundle),
            str(public), "--expected-fingerprint", fingerprint, "--output", str(output / "false-report-rejection.json")],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
        assert rejected.returncode == 1
        false_receipt = strict_json_load(output / "false-report-rejection.json")
        assert false_receipt["pcs_package_valid"] and not false_receipt["independent_replay_consistent"]
        built["bundle"] = positive.name
        negative_result["bundle"] = negative.name
        summary = {"format": "pcs-scientific-assurance-experiment-v1", "protocol_sha256": sha((output / "PROTOCOL.json").read_bytes()),
            "producer_public_key_fingerprint": fingerprint, "positive": built, "honest_failure": negative_result,
            "deterministic_archive_equal": repeated_result["bundle_sha256"] == built["bundle_sha256"],
            "producer_signed_false_report": {"pcs_package_valid": True, "independent_receiver_rejected": True},
            "primitive_claims_computationally_supported": 4, "numerical_claim_status_in_pcs": "OPEN",
            "independently_replayed_domain_predicates": 8, "hypothesis_or_premise_revision_propagated": True,
            "bounded_investigation": {"initial_failure_preserved": True, "separate_checked_proposal_passed": True,
                "model_or_rl_used": False, "autonomous_scientific_discovery": False},
            "independent_replay_processes": 3, "human_participants": 0, "independent_human_reviews": 0,
            "financial_spend": 0, "known_limitations": protocol["question_grounding"]}
    elapsed = time.perf_counter() - started
    usage_after = resource.getrusage(resource.RUSAGE_SELF)
    child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    summary["resources"] = {"wall_seconds": format(elapsed, ".6f"),
        "self_cpu_seconds": format(usage_after.ru_utime + usage_after.ru_stime - usage_before.ru_utime - usage_before.ru_stime, ".6f"),
        "child_cpu_seconds": format(child_after.ru_utime + child_after.ru_stime - child_before.ru_utime - child_before.ru_stime, ".6f"),
        "self_peak_rss": usage_after.ru_maxrss, "child_peak_rss": child_after.ru_maxrss,
        "peak_rss_unit": "KiB" if platform.system() == "Linux" else "platform-dependent",
        "parent_observed_subprocess_starts": invocations,
        "accounting_limit": "Parent subprocess observations exclude nested Lean invocations inside the three independent Python replay processes; CPU includes waited children."}
    summary["environment"] = {"python": platform.python_version(), "system": platform.system(), "machine": platform.machine(),
        "lean_toolchain": (ROOT / "formal/lean-toolchain").read_text().strip(),
        "compiled_authority_sha256": sha((ROOT / "formal/.lake/build/bin/pcs-lean-authority").read_bytes())}
    write(output / "SUMMARY.json", summary)
    write(output / "ARTIFACT_SHA256.json", {"format": "pcs-experiment-artifact-seal-v1",
        "files": {path.name: sha(path.read_bytes()) for path in sorted(output.iterdir()) if path.is_file()}})
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = run(args.output.resolve())
    print(json.dumps({"output": str(args.output), "positive": summary["positive"]["bounded_contract_satisfied"],
        "negative_rejected": summary["producer_signed_false_report"]["independent_receiver_rejected"],
        "wall_seconds": summary["resources"]["wall_seconds"], "financial_spend": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
