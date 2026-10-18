"""Executable tests for the epistemic stratification kernel."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs import epistemic_kernel_v1 as ek


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
        lean_audit = False
        timeout = 60.0
        output = str(out)

    assert ek.command(Args()) == 0
    payload = json.loads((out / "RESULT.json").read_text(encoding="utf-8"))
    assert payload["passed"] is True
