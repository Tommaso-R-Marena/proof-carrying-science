from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

from research.integration_v1.demo import run_demo
from research.integration_v1.protocols import inspect_artifact
from research.integration_v1.scoped_evidence import (
    ROOT, ComponentUnavailable, component, falsify_dependency, replay_conservation,
    replay_interval, replay_nonidentifiability)
from research.integration_v1.source_gate import check_profile


def run(arguments, *, cwd=ROOT, timeout=180):
    result = subprocess.run(arguments, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@pytest.fixture(scope="module")
def pilot(tmp_path_factory):
    from pcs.independent_pilot_v1 import run_independent_pilot_v1
    authority = Path(os.environ.get("PCS_LEAN_AUTHORITY_BIN", str(ROOT / "formal/.lake/build/bin/pcs-lean-authority")))
    assert authority.is_file() and os.access(authority, os.X_OK), "mandatory real authority unavailable"
    out = tmp_path_factory.mktemp("cross-pr") / "pilot"
    evidence = run_independent_pilot_v1(out, lean_authority_path=authority,
                                       apply_closeout=True, deterministic_fixture=True)
    return out, authority, evidence


def test_01_production_v06_real_receiving_with_research_present(pilot):
    from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06
    out, authority, evidence = pilot
    result = verify_package_zip_end_to_end_v06(
        evidence["paths"]["bundle"], out / "reviewer/trusted-public.pem",
        expected_fingerprint=evidence["signer_fingerprint"], lean_authority_path=authority,
        require_canonical_archive=True, require_intake_lock=True,
        expected_intake_semantic_hash=evidence["intake_semantic_hash"])
    assert result["valid"] is True and result["authoritative"] is True
    assert result["bundle_sha256"] == evidence["bundle_sha256"]
    wrong = verify_package_zip_end_to_end_v06(
        evidence["paths"]["bundle"], out / "reviewer/trusted-public.pem",
        lean_authority_path=authority, expected_intake_semantic_hash="0" * 64)
    assert wrong["valid"] is False


def test_02_four_explicit_protocols_reject_cross_interpretation():
    fixtures = ROOT / "formal/fixtures/proof_gated"
    examples = {
        "PGSI1": b"PGSI1|R|1|1",
        "PGSI2-WIDE": b"PGSI2-WIDE|0|1|1|1",
        "PGSC6": (fixtures / "v6_certs/step1.pgsc6").read_bytes(),
        "PGSC7": (fixtures / "v7/certs/step1.pgsc7").read_bytes(),
    }
    for profile, raw in examples.items():
        assert inspect_artifact(profile, raw)["authorization"] == "NOT_RUN"
        for other in examples:
            if other != profile:
                with pytest.raises(ValueError):
                    inspect_artifact(other, raw)
        with pytest.raises(ValueError):
            inspect_artifact(profile, raw + b"\n")


def test_03_v7_exact_audited_module_identity():
    result = check_profile()
    assert result["passed"], result
    assert result["V7_modules"] == 38


def test_04_pointwise_preserves_valid_and_refutes_finite_gate_counterexample():
    frozen = ROOT / "research/isolated/pgsi1/research/proof-gated-self-improvement-v1"
    # Original producer and actual receiver-owned Lean checker, separate interpreter.
    script = '''
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path("pointwise").resolve()))
from dominance import certificate
from receive import Kernel,expression
from universal_relu import Net,Term
target=Net((Term(1,2,1),)); zero=Net(())
old=Net((Term(1,3,-3),)); new=Net((Term(1,3,-1),))
with tempfile.TemporaryDirectory() as tmp:
    k=Kernel(Path(tmp)/"proofs")
    good=certificate(zero,target,target);bad=certificate(old,new,target)
    assert good["result"]["passes"] and not bad["result"]["passes"]
    k.replay([expression(good,(zero,target,target))],"Good")
    k.replay([expression(bad,(old,new,target))],"Refuted")
print("actual pointwise Lean replay completed")
'''
    assert "Lean replay completed" in run([sys.executable, "-c", script], cwd=frozen)


def test_05_actual_pinned_policy_promotion_rollback_and_journal_recovery():
    cwd = ROOT / "research/proof-gated-self-improvement-v1"
    for script in ("pgsc6_pinned_store_live.py", "pgsc6_external_anchor_live.py",
                   "pgsc6_journaled_recovery_live.py"):
        result = json.loads(run([sys.executable, script], cwd=cwd))
        assert result["result"] == "PASS"
        assert result.get("machine_checked_host_refinement", False) is False


def test_06_computational_scope_cannot_upgrade_to_formal_or_empirical():
    result = run_demo()
    observation = replay_interval(result["numerical_certificate"])
    assert observation.supports(category="computationally_reproduced", scope=observation.scope)
    for category in ("formal", "kernel_checked", "empirically_validated", "causal_effect"):
        assert not observation.supports(category=category, scope=observation.scope)
    assert not observation.supports(category="computationally_reproduced", scope="unrestricted")
    with pytest.raises(ValueError):
        replay_interval({"format": "certnum-cert-v1", "kind": "expression_equivalence", "accepted": True})


def test_07_sticky_falsification_reopens_distinct_engine_dependencies():
    result = falsify_dependency()
    assert result["falsifier_status"] == "falsified"
    assert result["reopened"] == ["certnum:dependent", "pcca:assumption"]
    assert all(n["status"] == "OPEN" for n in result["graph"]["nodes"].values())
    assert result["mathematical_theorems_invalidated"] is False


def test_08_conservation_and_numerical_enclosure_keep_distinct_scopes():
    result = run_demo()
    scopes = [o["scope"] for o in result["scoped_observations"]]
    assert any(s.startswith("pcca.trajectory_conservation:") for s in scopes)
    assert any(s.startswith("certnum.interval_enclosure:") for s in scopes)
    assert result["conservation"]["trajectory_pools"] == {"C": "6", "H": "12", "O": "6"}
    assert result["numeric_binding"]["state_count"] == 13
    bridge = result["two_species_bridge_fixture"]
    assert bridge["trajectory_certificate"]["claim"]["states"][-1] == ["2/3", "1/3"]
    assert bridge["lean_execution"] == "NOT_RUN"
    assert bridge["python_lean_general_refinement"] == "OPEN"
    assert result["empirical_validity"] == "OPEN"
    contract = result["contract"]
    contract["reactions"][0]["reactants"][0]["coefficient"] = 1.5
    with pytest.raises(ValueError, match="exact"):
        replay_conservation(contract)


def test_09_nonidentifiability_is_a_negative_not_a_causal_effect():
    result = replay_nonidentifiability()
    assert result["result"]["status"] == "NOT_IDENTIFIABLE"
    assert result["result"]["observational_total_variation"] == [0, 1]
    assert result["result"]["interventional_outcome_total_variation"] == [1, 2]
    assert result["causal_effect_supported"] is False


def test_10_real_pilot_exports_reviewer_report_and_non_authoritative_card(pilot, tmp_path):
    from independent_eval.reviewer_adoption.workbench.generate_report import generate_report
    from independent_eval.reviewer_adoption.workbench.export_assurance_card import run_assurance_card_export
    out, _, evidence = pilot
    checked = tmp_path / "received"
    checked.mkdir()
    import zipfile
    # This exact locally generated canonical archive was received by the real authority above.
    with zipfile.ZipFile(evidence["paths"]["bundle"]) as archive:
        for name in archive.namelist():
            path = checked / name
            assert path.resolve().is_relative_to(checked.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))
    shutil.copy2(out / "reviewer/verification-receipt.json", checked / "verification-receipt.json")
    reports = generate_report(checked, tmp_path / "workbench", fmt="both")
    inspection = json.loads(reports["json"].read_text())
    assert inspection["workbench_issues_accept"] is False
    exported = run_assurance_card_export(evidence=checked, out=tmp_path / "card", skip_verify=True)
    assert exported["export_status"] == "EXPORTED"
    card = json.loads((tmp_path / "card.json").read_text())
    assert card["card_issues_accept"] is False and card["inspection_is_not_authority"] is True
    assert card["authority"]["skipped"] is True
    assert card["lane_consistency"]["overall"] == "inconclusive"


def test_11_absent_optional_component_leaves_ordinary_cli_usable(tmp_path):
    with pytest.raises(ComponentUnavailable, match="ABSENT"):
        component("pcca", root=tmp_path)
    assert "usage:" in run([sys.executable, "-m", "pcs.cli", "--help"])


def test_12_research_artifacts_cannot_be_used_as_production_deliveries(pilot):
    from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06, V06BundleVerificationError
    out, authority, _ = pilot
    before = hashlib.sha256(authority.read_bytes()).hexdigest()
    with pytest.raises(V06BundleVerificationError):
        verify_package_zip_end_to_end_v06(
            ROOT / "formal/fixtures/proof_gated/v7/certs/step1.pgsc7",
            out / "reviewer/trusted-public.pem", lean_authority_path=authority)
    assert hashlib.sha256(authority.read_bytes()).hexdigest() == before
    assert run_demo()["deployment_performed"] is False


def test_13_source_integrity_and_module_discovery():
    run([sys.executable, "scripts/check_repository_integrity.py"])
    assert check_profile()["passed"]


def test_14_committed_clean_checkout_reproduces_demo(tmp_path):
    archive = subprocess.check_output(["git", "archive", "HEAD"], cwd=ROOT)
    import io, tarfile
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
        contents.extractall(checkout, filter="data")
    result = json.loads(run([sys.executable, "-m", "research.integration_v1.demo",
                             "--out", str(tmp_path / "replay")], cwd=checkout))
    from research.integration_v1.scoped_evidence import digest
    assert result["report_sha256"] == digest(run_demo())


def test_15_all_original_prs_have_source_test_and_disposition():
    coverage = json.loads((ROOT / "docs/integration/2026-10-18/PR_CAPABILITY_COVERAGE.json").read_text())
    assert len(coverage["pull_requests"]) == 32
    for pr in coverage["pull_requests"]:
        assert pr["source_commit"] and pr["capabilities"]
        assert pr["disposition"] in {"INTEGRATED_EXACT", "INTEGRATED_ADAPTED", "RETAINED_ISOLATED",
                                      "SEMANTICALLY_SUBSUMED_PROVEN", "BLOCKED_EXTERNAL_INPUT"}
        assert pr["tests"] or pr["blockers"]
