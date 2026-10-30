"""Executable tests for the epistemic stratification kernel."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs import epistemic_kernel_v1 as ek

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "epistemic_stratification_v1"


def test_forbidden_promotion_computational_to_empirical():
    cert = ek._fixture_cert(
        stratum="empirical",
        evidence_stratum="computational",
        claim_id="C_world",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    result = ek.assess(cert)
    assert result["accepted"] is False
    assert result["forbidden_promotions"]
    assert result["scientific_acceptance"] is False


def test_formal_support_keeps_continuum_residual():
    cert = ek._fixture_cert(
        stratum="formal",
        evidence_stratum="formal",
        claim_id="C_discrete",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    result = ek.assess(cert)
    assert result["accepted"] is True
    assert any(r["stratum"] == "continuum" and r["status"] == "OPEN" for r in result["residuals"])
    assert any(r["stratum"] == "empirical" and r["status"] == "OPEN" for r in result["residuals"])
    assert any(r["stratum"] == "causal" and r["status"] == "OPEN" for r in result["residuals"])


def test_compose_meet_and_residual_union():
    left = ek._fixture_cert(
        stratum="formal",
        evidence_stratum="formal",
        claim_id="C_discrete",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    right = ek._fixture_cert(
        stratum="computational",
        evidence_stratum="computational",
        claim_id="C_pipeline",
        predicate="pipeline-ok",
        evidence_id="E_pipe",
        artifacts=["pipe.json"],
        cite="C_discrete",
    )
    composed = ek.compose(canonicalize_jcs_bytes(left), canonicalize_jcs_bytes(right))
    assert composed["accepted"] is True
    assert composed["result_stratum"] == "computational"
    assert "continuum" in {r["stratum"] for r in composed["composed"]["residuals"]}


def test_invalidation_reopens_dependent_claim():
    cert = ek._fixture_cert(
        stratum="formal",
        evidence_stratum="formal",
        claim_id="C_discrete",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    result = ek.invalidate(canonicalize_jcs_bytes(cert), ["matrix.json"])
    assert result["affected_claims"] == ["C_discrete"]
    assert result["affected_evidence"] == ["E_matrix"]
    assert result["accepted"] is False


def test_campaign_passes(tmp_path: Path):
    result = ek.run_campaign()
    assert result["passed"] is True
    assert result["scientific_acceptance"] is False
    assert result["cases"]["lattice_self_check"] is True
    assert result["cases"]["reject_computational_continuum_bridge"] is True
    assert result["cases"]["transport_lift_keeps_continuum_open"] is True
    out = tmp_path / "campaign"
    ek.export_evidence(out, result)
    assert (out / "RESULT.json").is_file()
    assert (out / "SHA256.json").is_file()


def test_compose_requires_upstream_citation():
    left = ek._fixture_cert(
        stratum="formal",
        evidence_stratum="formal",
        claim_id="C_discrete",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    right = ek._fixture_cert(
        stratum="computational",
        evidence_stratum="computational",
        claim_id="C_pipeline",
        predicate="pipeline-ok",
        evidence_id="E_pipe",
        artifacts=["pipe.json"],
    )
    with pytest.raises(ek.EpistemicKernelError, match="cite upstream"):
        ek.compose(canonicalize_jcs_bytes(left), canonicalize_jcs_bytes(right))


def test_direct_command_campaign(tmp_path: Path):
    out = tmp_path / "cli-campaign"

    class Args:
        mode = "campaign"
        certificate = None
        left = None
        right = None
        changed = None
        bridge = None
        schema = False
        lean_audit = False
        timeout = 60.0
        output = str(out)

    assert ek.command(Args()) == 0
    payload = json.loads((out / "RESULT.json").read_text(encoding="utf-8"))
    assert payload["passed"] is True


def test_lattice_self_check_exhaustive():
    result = ek.lattice_self_check()
    assert result["passed"] is True
    assert result["stratum_count"] == 6
    assert result["case_count"] > 200


def test_bridge_rejects_computational_continuum():
    payload = json.loads((EXAMPLES / "bad_bridge.json").read_text(encoding="utf-8"))
    result = ek.apply_bridge(
        payload["bridge"], payload["residual"], payload["evidence"], payload["claim"]
    )
    assert result["accepted"] is False
    assert result["scientific_acceptance"] is False


def test_transport_lift_keeps_opens():
    result = ek.lift_transport_opens()
    assert result["continuum_residual_open"] is True
    assert result["empirical_residual_open"] is True
    assert result["scientific_acceptance"] is False
    assert result["assessment"]["accepted"] is True


def test_schema_accepts_example_formal():
    cert = json.loads((EXAMPLES / "formal.json").read_text(encoding="utf-8"))
    # Loader normalizes residuals with status OPEN before schema checks in CLI assess.
    loaded = ek.load_certificate(canonicalize_jcs_bytes(cert))
    ek.validate_schema(loaded)


def test_schema_rejects_scientific_acceptance_true():
    cert = ek._fixture_cert(
        stratum="formal",
        evidence_stratum="formal",
        claim_id="C_discrete",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    cert["scientific_acceptance"] = True
    with pytest.raises(ek.EpistemicKernelError, match="schema validation failed"):
        ek.validate_schema(cert)


def test_reject_extra_fields():
    raw = canonicalize_jcs_bytes(
        {
            **ek._fixture_cert(
                stratum="formal",
                evidence_stratum="formal",
                claim_id="C_discrete",
                predicate="amount-conserved",
                evidence_id="E_matrix",
                artifacts=["matrix.json"],
            ),
            "extra": True,
        }
    )
    with pytest.raises(ek.EpistemicKernelError):
        ek.load_certificate(raw)


def test_reject_claim_stratum_mismatch():
    cert = ek._fixture_cert(
        stratum="formal",
        evidence_stratum="formal",
        claim_id="C_discrete",
        predicate="amount-conserved",
        evidence_id="E_matrix",
        artifacts=["matrix.json"],
    )
    cert["claim"]["stratum"] = "empirical"
    with pytest.raises(ek.EpistemicKernelError, match="certificate stratum"):
        ek.load_certificate(canonicalize_jcs_bytes(cert))


def test_conflicting_evidence_on_compose():
    left = ek._fixture_cert(
        stratum="formal",
        evidence_stratum="formal",
        claim_id="C_discrete",
        predicate="amount-conserved",
        evidence_id="E_shared",
        artifacts=["matrix.json"],
    )
    right = ek._fixture_cert(
        stratum="computational",
        evidence_stratum="computational",
        claim_id="C_pipeline",
        predicate="pipeline-ok",
        evidence_id="E_shared",
        artifacts=["pipe.json"],
        cite="C_discrete",
    )
    with pytest.raises(ek.EpistemicKernelError, match="conflicting evidence"):
        ek.compose(canonicalize_jcs_bytes(left), canonicalize_jcs_bytes(right))


@pytest.mark.parametrize(
    ("evidence", "claim"),
    [
        ("integrity", "computational"),
        ("computational", "formal"),
        ("formal", "continuum"),
        ("continuum", "empirical"),
        ("empirical", "causal"),
    ],
)
def test_forbidden_promotion_matrix(evidence: str, claim: str):
    assert ek.forbidden_promotion(evidence, claim) is True
    assert ek.can_discharge(evidence, claim) is False


@pytest.mark.parametrize("stratum", list(ek.STRATA))
def test_same_stratum_can_discharge(stratum: str):
    assert ek.can_discharge(stratum, stratum) is True
    assert ek.forbidden_promotion(stratum, stratum) is False
