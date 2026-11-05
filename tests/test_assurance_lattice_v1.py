from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcs.assurance_lattice_v1 import (
    FORMAT,
    AssuranceLatticeError,
    adversarial_campaign,
    evaluate,
    kernel_replay,
    load_package,
    proof_source,
)
from pcs.canonical_json import canonicalize_jcs_bytes

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "assurance_lattice_v1"


def _raw(name: str) -> bytes:
    return canonicalize_jcs_bytes(json.loads((EXAMPLES / name).read_text()))


def test_composed_scientific_chain_passes_python_replay():
    report = evaluate(_raw("composed_scientific_chain.json"))
    assert report["outcome"] == "PASS"
    assert report["certified_claim_ids"] == [0, 1, 2]
    assert report["checks"]["no_silent_promotion"] is True
    assert report["checks"]["composition_closed"] is True
    assert report["scientific_acceptance"] is False
    assert report["formal_model_support"] == "REQUIRES_FRESH_KERNEL_REPLAY"


def test_silent_computational_to_formal_is_rejected():
    report = evaluate(_raw("silent_formal_forgery.json"))
    assert report["outcome"] == "FAIL"
    assert report["violations"] == [{
        "kind": "silent_promotion_or_unsupported",
        "claim_id": 0,
        "required": "formal",
    }]


def test_bridged_upgrade_is_accepted_by_python_gate():
    report = evaluate(_raw("bridged_upgrade.json"))
    assert report["outcome"] == "PASS"
    assert report["certified_claim_ids"] == [0]


def test_changed_artifact_invalidates_supported_claim():
    package = load_package(_raw("composed_scientific_chain.json"))
    package["changed_artifacts"] = [102]
    report = evaluate(canonicalize_jcs_bytes(package))
    assert report["outcome"] == "FAIL"
    assert {"kind": "invalidated_by_change", "claim_id": 2} in report["violations"]


def test_missing_premise_blocks_composition():
    package = load_package(_raw("composed_scientific_chain.json"))
    package["evidence"] = [e for e in package["evidence"] if e["claim_id"] != 0]
    report = evaluate(canonicalize_jcs_bytes(package))
    assert report["outcome"] == "FAIL"
    assert {"kind": "missing_premise", "claim_id": 1} in report["violations"]


def test_empirical_cannot_forge_formal():
    package = {
        "format": FORMAT,
        "claims": [{"id": 0, "required": "formal", "artifact_deps": [1], "premise_claims": []}],
        "evidence": [{"claim_id": 0, "stratum": "empirical", "accepted": True}],
        "bridges": [],
        "changed_artifacts": [],
        "assumptions": [
            {"id": "bridge_soundness", "statement": "none", "status": "OPEN"},
            {"id": "dependency_completeness", "statement": "complete", "status": "OPEN"},
            {"id": "empirical_correspondence", "statement": "open", "status": "OPEN"},
        ],
    }
    report = evaluate(canonicalize_jcs_bytes(package))
    assert report["outcome"] == "FAIL"
    assert report["violations"][0]["kind"] == "silent_promotion_or_unsupported"


def test_adversarial_campaign_has_zero_false_formal_accepts():
    campaign = adversarial_campaign(_raw("composed_scientific_chain.json"))
    assert campaign["campaign_pass"] is True
    assert campaign["false_formal_accepts"] == 0
    assert {m["mutation"] for m in campaign["mutations"]} >= {
        "computational_as_formal",
        "empirical_as_formal",
        "drop_premise_evidence",
        "mark_artifact_changed",
    }
    assert all(m["outcome"] == "FAIL" for m in campaign["mutations"]
               if m["mutation"] in {
                   "computational_as_formal",
                   "empirical_as_formal",
                   "mark_artifact_changed",
               })


def test_proof_source_is_literal_only():
    text = proof_source(_raw("bridged_upgrade.json")).decode("utf-8")
    assert "import PCSAssuranceLattice" in text
    assert "theorem certificate_checked" in text
    assert "theorem certificate_certified" in text
    assert "sorry" not in text and "admit" not in text


def test_reject_unknown_stratum_and_unordered_assumptions():
    package = load_package(_raw("composed_scientific_chain.json"))
    package["claims"][0]["required"] = "quantum"
    with pytest.raises(AssuranceLatticeError):
        evaluate(canonicalize_jcs_bytes(package))
    package = load_package(_raw("composed_scientific_chain.json"))
    package["assumptions"] = list(reversed(package["assumptions"]))
    with pytest.raises(AssuranceLatticeError):
        load_package(canonicalize_jcs_bytes(package))


def test_kernel_replay_composed_chain():
    result = kernel_replay(_raw("composed_scientific_chain.json"), timeout=90)
    assert result["status"] == "KERNEL_CHECKED", result
    assert result["kernel_checked"] is True
    assert set(result["kernel_axioms"]).issubset({"propext", "Classical.choice", "Quot.sound"})
    assert result["scientific_acceptance"] is False


def test_kernel_replay_rejects_silent_forgery_before_lean():
    result = kernel_replay(_raw("silent_formal_forgery.json"), timeout=90)
    assert result["status"] == "PYTHON_REJECTED"
    assert result["kernel_checked"] is False


def test_kernel_exhaustion_does_not_grant_support(monkeypatch):
    import subprocess
    import pcs.assurance_lattice_v1 as module
    raw = _raw("composed_scientific_chain.json")

    def exhausted(*args, **kwargs):
        raise subprocess.TimeoutExpired("lean", 1)

    monkeypatch.setattr(module.subprocess, "run", exhausted)
    result = kernel_replay(raw)
    assert result["kernel_checked"] is False
    assert result["status"] == "UNAVAILABLE_OR_EXHAUSTED"
