from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.attest_v06 import attest_v06
from pcs.check_registry_v06 import (
    CERTIFIED_BUILTIN_CHECK_TYPES_V06,
    formal_target_for_check_v06,
)
from pcs.discover_v06 import confirm_manifest_draft_v06, discover_project_v06
from pcs.proof_translation_v06 import (
    PROOF_PROPOSALS_FORMAT_V06,
    PROOF_TRANSLATION_FORMAT_V06,
    V06ProofTranslationError,
    translate_project_v06,
    write_proof_translation_outputs_v06,
)
from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]


def _write_csv_pair(root: Path) -> None:
    (root / "cohort_a.csv").write_text(
        "id,value\nA,1\nB,2\n",
        encoding="utf-8",
    )
    (root / "cohort_b.csv").write_text(
        "id,value\nC,3\nD,4\n",
        encoding="utf-8",
    )


def _inventory_ids(discovery: dict) -> dict[str, str]:
    return {item["path"]: item["artifact_id"] for item in discovery["inventory"]}


def _model_proposal_file(
    root: Path,
    *,
    discovery: dict,
    confidence: float = 0.995,
    key: str = "id",
    predicate: dict | None = None,
    format_value: str = PROOF_PROPOSALS_FORMAT_V06,
    commitment: str | None = None,
) -> Path:
    ids = _inventory_ids(discovery)
    left = ids["cohort_a.csv"]
    right = ids["cohort_b.csv"]
    claim = {
        "id": "C_MODEL_DISJOINT",
        "statement": "The two discovered cohorts are disjoint on their id column.",
        "kind": "computational",
    }
    if predicate is not None:
        claim["predicate"] = predicate
    value = {
        "format": format_value,
        "inventory_commitment_sha256": (
            discovery["inventory_commitment_sha256"]
            if commitment is None
            else commitment
        ),
        "proposer": {
            "kind": "external_model",
            "name": "test-scientific-proposer",
            "version": "1",
            "model_family": "fixture",
        },
        "proposals": [
            {
                "id": "MODEL_DISJOINT",
                "confidence": confidence,
                "finding": "The two cohort tables appear intended as non-overlapping populations.",
                "artifact_ids": [left, right],
                "claim": claim,
                "check": {
                    "id": "E_MODEL_DISJOINT",
                    "type": "csv_disjoint",
                    "claim_ids": ["C_MODEL_DISJOINT"],
                    "left_artifact": left,
                    "right_artifact": right,
                    "key": key,
                },
            }
        ],
    }
    path = root / "model-proposals.json"
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _keypair(root: Path) -> tuple[Path, Path]:
    private = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public = private.public_key()
    private_path = root / "private.pem"
    public_path = root / "public.pem"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path


def test_shared_registry_names_exact_certified_frontier():
    assert CERTIFIED_BUILTIN_CHECK_TYPES_V06 == {
        "reaction_balance",
        "unit_compatible",
        "csv_disjoint",
        "pkpd_contract",
        "pkpd_reference_match",
    }
    target = formal_target_for_check_v06("pkpd_reference_match")
    assert target["soundness_theorem"] == "PCS.V2.PKPDCheck.pkpdMatchRun_sound"
    assert target["real_bridge_theorem"] == "PCSReal.PKPD.pcs_pkpd_reference_match_real"


def test_deterministic_discovery_compiles_to_explicit_formal_target(tmp_path: Path):
    (tmp_path / "reaction.json").write_text(
        json.dumps(
            {
                "reactants": [
                    {"formula": "H2", "coefficient": 2},
                    {"formula": "O2", "coefficient": 1},
                ],
                "products": [
                    {"formula": "H2O", "coefficient": 2},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = translate_project_v06(tmp_path)

    assert result["format"] == PROOF_TRANSLATION_FORMAT_V06
    assert result["summary"]["compiled_selected"] == 1
    candidate = next(c for c in result["candidates"] if c["selected"])
    assert candidate["status"] == "COMPILED_LEAN_BUILTIN"
    assert candidate["check"]["type"] == "reaction_balance"
    assert candidate["grounding"]["status"] == "GROUNDED"
    assert candidate["formal_target"]["soundness_theorem"] == "PCS.V2.Checkers.chem_sound"
    assert candidate["formal_target"]["decision_theorem"] == "PCS.V2.Chemistry.balancedB_iff"
    assert len(candidate["translation_sha256"]) == 64
    assert result["manifest_draft"]["pcs_intake"]["status"] == "draft"
    assert result["manifest_draft"]["pcs_intake"]["requires_confirmation"] is True


def test_external_model_can_expand_beyond_heuristics_but_compiler_derives_predicate(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    assert discovery["recommendations"] == []

    proposal = _model_proposal_file(tmp_path, discovery=discovery)
    result = translate_project_v06(tmp_path, proposal_files=[proposal])

    model = next(
        candidate
        for candidate in result["candidates"]
        if candidate["source"]["kind"] == "external_model"
    )
    assert model["selected"] is True
    assert model["status"] == "COMPILED_LEAN_BUILTIN"
    assert model["grounding"]["status"] == "GROUNDED"
    assert "CSV key 'id'" in model["grounding"]["facts"][0]
    assert model["typed_claim"]["predicate"] == {
        "type": "csv_disjoint",
        "left_artifact": model["check"]["left_artifact"],
        "right_artifact": model["check"]["right_artifact"],
        "key": "id",
    }
    assert model["formal_target"]["soundness_theorem"] == "PCS.V2.Csv.csvRun_sound"
    assert result["summary"]["external_model_selected"] == 1
    assert "C_MODEL_DISJOINT" in {
        claim["id"] for claim in result["manifest_draft"]["claims"]
    }
    assert any(
        obligation["kind"] == "MODEL_PROPOSAL_UNTRUSTED"
        for obligation in model["obligations"]
    )


def test_external_model_hallucinated_grounding_is_fail_closed(tmp_path: Path):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    proposal = _model_proposal_file(
        tmp_path,
        discovery=discovery,
        key="patient_id",
    )

    result = translate_project_v06(tmp_path, proposal_files=[proposal])
    model = next(
        candidate
        for candidate in result["candidates"]
        if candidate["source"]["kind"] == "external_model"
    )

    assert model["selected"] is False
    assert model["status"] == "REJECTED_UNGROUNDED"
    assert model["grounding"]["status"] == "FAILED"
    assert any(
        obligation["kind"] == "GROUND_PREDICATE_IN_PROJECT_BYTES"
        and obligation["blocking"] is True
        for obligation in model["obligations"]
    )
    assert "C_MODEL_DISJOINT" not in {
        claim["id"] for claim in result["manifest_draft"]["claims"]
    }


def test_model_cannot_substitute_predicate_that_differs_from_compiled_check(tmp_path: Path):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    proposal = _model_proposal_file(
        tmp_path,
        discovery=discovery,
        predicate={
            "type": "csv_disjoint",
            "left_artifact": ids["cohort_a.csv"],
            "right_artifact": ids["cohort_b.csv"],
            "key": "different_key",
        },
    )

    result = translate_project_v06(tmp_path, proposal_files=[proposal])
    model = next(
        candidate
        for candidate in result["candidates"]
        if candidate["source"]["kind"] == "external_model"
    )
    assert model["selected"] is False
    assert model["status"] == "REJECTED_PREDICATE_MISMATCH"
    assert any(
        obligation["kind"] == "PREDICATE_CHECK_MISMATCH"
        for obligation in model["obligations"]
    )


def test_low_confidence_model_proposal_compiles_but_stays_review_only(tmp_path: Path):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    proposal = _model_proposal_file(
        tmp_path,
        discovery=discovery,
        confidence=0.97,
    )

    result = translate_project_v06(
        tmp_path,
        proposal_files=[proposal],
        minimum_model_confidence=0.98,
    )
    model = next(
        candidate
        for candidate in result["candidates"]
        if candidate["source"]["kind"] == "external_model"
    )
    assert model["formalizable"] is True
    assert model["selected"] is False
    assert model["status"] == "REVIEW_ONLY_LOW_CONFIDENCE"
    assert "C_MODEL_DISJOINT" not in {
        claim["id"] for claim in result["manifest_draft"]["claims"]
    }


def test_external_proposals_are_bound_to_exact_discovery_inventory(tmp_path: Path):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    proposal = _model_proposal_file(
        tmp_path,
        discovery=discovery,
        commitment="0" * 64,
    )

    with pytest.raises(V06ProofTranslationError, match="inventory commitment"):
        translate_project_v06(tmp_path, proposal_files=[proposal])


def test_translation_outputs_are_deterministic_and_cli_visible(tmp_path: Path):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    proposal = _model_proposal_file(tmp_path, discovery=discovery)
    result = translate_project_v06(tmp_path, proposal_files=[proposal])

    plan = tmp_path / "translation.json"
    manifest = tmp_path / "translated-manifest.json"
    written = write_proof_translation_outputs_v06(
        result,
        plan_output=plan,
        manifest_output=manifest,
    )
    assert written["proof_translation_plan"] == str(plan.resolve())
    assert written["manifest_draft"] == str(manifest.resolve())
    loaded_plan = json.loads(plan.read_text(encoding="utf-8"))
    assert loaded_plan["plan_sha256"] == result["plan_sha256"]

    cli_plan = tmp_path / "cli-translation.json"
    cli_manifest = tmp_path / "cli-manifest.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pcs.cli",
            "translate-project-v06",
            str(tmp_path),
            "--proposals",
            str(proposal),
            "-o",
            str(cli_plan),
            "--manifest-draft",
            str(cli_manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    output = json.loads(proc.stdout)
    assert output["format"] == PROOF_TRANSLATION_FORMAT_V06
    assert output["summary"]["external_model_selected"] == 1
    assert cli_plan.is_file() and cli_manifest.is_file()


@pytest.mark.skipif(shutil.which("lake") is None, reason="Lean/Lake unavailable")
def test_model_proposal_can_reach_confirmed_attestation_and_authoritative_verification(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    proposal = _model_proposal_file(tmp_path, discovery=discovery)
    translation = translate_project_v06(tmp_path, proposal_files=[proposal])

    plan_path = tmp_path / "pcs-proof-translation.json"
    draft_path = tmp_path / "pcs-manifest.draft.json"
    write_proof_translation_outputs_v06(
        translation,
        plan_output=plan_path,
        manifest_output=draft_path,
    )
    confirmed_path = tmp_path / "manifest.json"
    confirmed = confirm_manifest_draft_v06(
        draft_path,
        confirmed_path,
        project_root=tmp_path,
    )
    assert confirmed["valid"] is True

    private_key, public_key = _keypair(tmp_path)
    bundle = tmp_path / "translated.pcs.zip"
    attested = attest_v06(
        confirmed_path,
        bundle,
        private_key,
        public_key,
    )
    assert bundle.is_file()
    assert attested["valid"] is True

    verified = verify_package_zip_end_to_end_v06(
        bundle,
        public_key,
        require_canonical_archive=True,
    )
    assert verified["valid"] is True
    assert verified["authoritative"] is True
    assert verified["archive_assurance"] == "lean-decoded-canonical-zip"
    claim = next(c for c in verified["claims"] if c["claim_id"] == "C_MODEL_DISJOINT")
    assert claim["decision"] == "COMPUTATIONALLY_SUPPORTED"
