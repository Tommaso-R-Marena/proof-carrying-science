from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization

from pcs.attest_v06 import build_attestation_directory_v06
from pcs.bundle_v06 import create_verified_bundle_v06
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.canonical_zip_v06 import canonical_zip_bytes_v06
from pcs.external_validator_v06 import build_external_validator_receipt_payload_v06, sign_external_validator_receipt_v06
from pcs.jsonio import strict_json_load
from pcs.scientific_assurance_v1 import (build_scientific_bundle, prepare_scientific_project,
    verify_scientific_bundle, render_scientific_receipt_html, ScientificAssuranceError)
from pcs.scientific_contracts_v1 import evaluate
from pcs.scientific_research_v1 import investigate_scientific_contract
from pcs.signing import generate_keypair
from pcs.verifier_zip_v06 import load_package_zip_v06, verify_package_zip_end_to_end_v06

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prepared_case(tmp_path_factory):
    directory = tmp_path_factory.mktemp("science-signed")
    project = directory / "external-workflow"
    shutil.copytree(ROOT / "examples/scientific_mass_action", project)
    # Only this explicitly authored standard-library source is executed, by the
    # fixture owner. Neither discovery nor assurance executes arbitrary source.
    subprocess.run([sys.executable, "run_workflow.py"], cwd=project, check=True)
    private = directory / "producer-private.pem"
    public = directory / "producer-public.pem"
    fingerprint = generate_keypair(private, public)["fingerprint"]
    bundle = directory / "positive.pcs.zip"
    result = build_scientific_bundle(project, directory / "positive-work", bundle, private, public,
        expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
    return {"directory": directory, "project": project, "private": private, "public": public,
        "fingerprint": fingerprint, "bundle": bundle, "result": result}


def test_real_signed_scientific_package_passes_compiled_authority_and_fresh_domain_replay(prepared_case):
    case = prepared_case
    result = case["result"]
    assert result["pcs_package_valid"] and result["independent_replay_consistent"]
    assert result["bounded_contract_satisfied"] is True
    assert result["pcs_numerical_claim"] == "OPEN"
    assert result["scientific_acceptance"] is False
    receipt = verify_scientific_bundle(case["bundle"], case["public"], expected_fingerprint=case["fingerprint"])
    assert receipt["pcs_verification"]["lean_authority"]["accepted"] is True
    assert receipt["domain_replay"]["outcome"] == "PASS"
    assert receipt["external_numerical_signature"]["semantic_authority"] == "EXTERNAL_VALIDATOR_TRUST_REQUIRED"
    statuses = {x["claim_id"]: x["decision"] for x in receipt["pcs_verification"]["claims"]}
    assert statuses["C_NUMERICAL"] == "OPEN"
    assert all(status == "COMPUTATIONALLY_SUPPORTED" for ident, status in statuses.items() if ident != "C_NUMERICAL")


def test_archive_is_deterministic_for_exact_inputs_key_and_declared_timestamp(prepared_case):
    case = prepared_case
    other = case["directory"] / "positive-again.pcs.zip"
    result = build_scientific_bundle(case["project"], case["directory"] / "positive-again-work",
        other, case["private"], case["public"], expected_fingerprint=case["fingerprint"], confirm_reviewed_draft=True)
    assert result["bundle_sha256"] == case["result"]["bundle_sha256"]
    assert other.read_bytes() == case["bundle"].read_bytes()


def test_discovery_never_executes_dangerous_source_and_original_tree_remains_intact(prepared_case):
    case = prepared_case
    project = case["directory"] / "no-execute"
    shutil.copytree(case["project"], project)
    (project / "danger.py").write_text("from pathlib import Path\nPath('MUST_NOT_EXIST').write_text('executed')\nraise RuntimeError('no')\n")
    before = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in project.rglob("*") if p.is_file()}
    result = prepare_scientific_project(project, case["directory"] / "no-execute-work",
        case["private"], case["public"], expected_fingerprint=case["fingerprint"])
    after = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in project.rglob("*") if p.is_file()}
    assert before == after
    assert not (project / "MUST_NOT_EXIST").exists()
    assert not (Path(result["project"]) / "MUST_NOT_EXIST").exists()
    assert result["user_code_executed"] is False
    assert result["status"] == "DRAFT"


def test_compiled_valid_producer_signed_false_report_is_rejected_by_receiving_adapter(prepared_case):
    case = prepared_case
    project = case["directory"] / "false-report-project"
    shutil.copytree(case["directory"] / "positive-work/project", project)
    report_path = project / "pcs-scientific/domain-replay.json"
    forged = strict_json_load(report_path)
    forged["resources"]["reaction_step_evaluations"] = 0
    report_path.write_bytes(canonicalize_jcs_bytes(forged))
    manifest_path = project / "manifest.confirmed.json"
    manifest = strict_json_load(manifest_path)
    spec = strict_json_load(project / "pcs-scientific/numerical-spec.json")
    artifacts = {x["id"]: x for x in manifest["artifacts"]}
    bound = {ident: (project / artifacts[ident]["path"]).read_bytes() for ident in spec["bound_artifact_ids"]}
    payload = build_external_validator_receipt_payload_v06(check_type=spec["type"], validator=spec["validator"],
        predicate=spec["predicate"], bound_artifact_ids=spec["bound_artifact_ids"], artifact_bytes=bound, outcome="PASS")
    key = serialization.load_pem_private_key(case["private"].read_bytes(), password=None)
    receipt_path = project / artifacts[spec["receipt_artifact"]]["path"]
    receipt_path.write_bytes(canonicalize_jcs_bytes(sign_external_validator_receipt_v06(payload, key)))
    for artifact in manifest["artifacts"]:
        raw = (project / artifact["path"]).read_bytes()
        artifact["metadata"]["pcs_discovery_sha256"] = hashlib.sha256(raw).hexdigest()
        artifact["metadata"]["pcs_discovery_size"] = len(raw)
    manifest_path.write_bytes(canonicalize_jcs_bytes(manifest))
    package = case["directory"] / "false-report-package"
    build_attestation_directory_v06(manifest_path, package, case["private"], case["public"],
        expected_fingerprint=case["fingerprint"], generated_at="2026-10-12T00:00:00+00:00")
    bundle = case["directory"] / "false-report.pcs.zip"
    create_verified_bundle_v06(package, bundle, case["public"], expected_fingerprint=case["fingerprint"])
    # Package integrity and builtin semantics remain valid. The receiver rejects
    # the false numerical assertion without pretending the kernel had proved it.
    ordinary = verify_package_zip_end_to_end_v06(bundle, case["public"], expected_fingerprint=case["fingerprint"])
    assert ordinary["valid"] is True
    independent = verify_scientific_bundle(bundle, case["public"], expected_fingerprint=case["fingerprint"])
    assert independent["pcs_package_valid"] is True
    assert independent["independent_replay_consistent"] is False
    assert independent["bounded_contract_satisfied"] is False
    assert "differs from fresh independent replay" in independent["errors"][0]


def test_honest_failed_numerical_case_is_integrity_valid_but_not_satisfied(prepared_case):
    case = prepared_case
    project = case["directory"] / "bad-data"
    shutil.copytree(case["project"], project)
    observations = project / "observations.csv"
    rows = observations.read_text().splitlines()
    cells = rows[-1].split(",")
    cells[1] = "100"
    rows[-1] = ",".join(cells)
    observations.write_text("\n".join(rows) + "\n")
    result = build_scientific_bundle(project, case["directory"] / "bad-data-work",
        case["directory"] / "bad-data.pcs.zip", case["private"], case["public"],
        expected_fingerprint=case["fingerprint"], confirm_reviewed_draft=True)
    assert result["pcs_package_valid"] is True
    assert result["independent_replay_consistent"] is True
    assert result["bounded_contract_satisfied"] is False
    assert result["pcs_numerical_claim"] == "OPEN"


def test_wrong_caller_pinned_identity_cannot_acquire_scientific_authority(prepared_case):
    case = prepared_case
    result = verify_scientific_bundle(case["bundle"], case["public"], expected_fingerprint="0" * 64)
    assert result["pcs_package_valid"] is False
    assert result["bounded_contract_satisfied"] is False
    assert result["scientific_acceptance"] is False


def test_source_tampering_fails_existing_authority_before_scientific_replay(prepared_case):
    case = prepared_case
    loaded = load_package_zip_v06(case["bundle"])
    files = dict(loaded["package_files"])
    certificate = json.loads(loaded["certificate_bytes"])
    model = next(x for x in certificate["artifacts"] if x["source_path"] == "model.json")
    files[model["path"]] += b" "
    files.update({"certificate_signature.json": loaded["certificate_signature_bytes"],
        "package_manifest.json": loaded["package_manifest_bytes"], "package_signature.json": loaded["package_signature_bytes"]})
    tampered = case["directory"] / "tampered.pcs.zip"
    tampered.write_bytes(canonical_zip_bytes_v06(files))
    result = verify_scientific_bundle(tampered, case["public"], expected_fingerprint=case["fingerprint"])
    assert result["pcs_package_valid"] is False
    assert result["independent_replay_consistent"] is False


def test_packaging_requires_explicit_confirmation_and_does_not_touch_destination(prepared_case):
    case = prepared_case
    work = case["directory"] / "unconfirmed"
    bundle = case["directory"] / "unconfirmed.pcs.zip"
    with pytest.raises(ScientificAssuranceError, match="explicitly confirm"):
        build_scientific_bundle(case["project"], work, bundle, case["private"], case["public"], expected_fingerprint=case["fingerprint"])
    assert not work.exists() and not bundle.exists()


def test_path_escape_and_symlink_are_rejected_before_staging(prepared_case):
    case = prepared_case
    with pytest.raises(ScientificAssuranceError, match="canonical"):
        prepare_scientific_project(case["project"], case["directory"] / "escaped", case["private"], case["public"],
            expected_fingerprint=case["fingerprint"], contract_path="../model.json")


def test_html_report_escapes_untrusted_claim_text():
    rendered = render_scientific_receipt_html({"claim": "<script>alert(1)</script>"})
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_bounded_investigator_preserves_failed_original_and_separate_verified_proposal(prepared_case):
    case = prepared_case
    contract = (case["project"] / "model.json").read_bytes()
    observations = (case["project"] / "observations.csv").read_bytes()
    wrong = observations.replace(b"0,1,0,0", b"0,2,0,0", 1)
    result = investigate_scientific_contract(contract, wrong, allow_reference_proposal=True)
    assert result["original_outcome"] == "FAIL"
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["replay"]["outcome"] == "FAIL"
    assert result["proposals"][0]["outcome"] == "PASS"
    assert result["proposals"][0]["requires_human_selection_and_new_signed_package"] is True
    assert result["scientific_acceptance"] is False
    assert result["release_authorization"] is False
    assert result["original_contract_sha256"] == hashlib.sha256(contract).hexdigest()


def test_empty_evidence_is_not_repaired_into_success(prepared_case):
    case = prepared_case
    result = investigate_scientific_contract((case["project"] / "model.json").read_bytes(), b"", allow_reference_proposal=True)
    assert result["original_outcome"] == "OPEN"
    assert result["proposals"] == []
    assert result["release_authorization"] is False
