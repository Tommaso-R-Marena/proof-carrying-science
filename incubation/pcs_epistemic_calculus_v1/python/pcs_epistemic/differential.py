"""Lean↔Python differential vectors for Controls fixtures.

These encode the exact finite controls proved in `PcsEpistemic/Controls.lean`.
Python must agree; disagreement is a hard failure. This is empirical
correspondence evidence, not a refinement theorem about the Python runtime.
"""

from __future__ import annotations

from typing import Any

from .assures import assure
from .dialectic import agreement_core, distinguishing, dispute_frontier, model_supports
from .invalidate import compute_impact, nonimpact
from .lattice import EvidenceClass, le


FORMAL_CLAIM = {"id": 1, "required_class": "formal", "required_evidence": [10]}
COMP_CLAIM = {"id": 2, "required_class": "computational", "required_evidence": [11]}

SAMPLE_GRAPH = {
    "workflow": [
        {"id": 100, "inputs": [0], "outputs": [1]},
        {"id": 101, "inputs": [1], "outputs": [2]},
    ],
    "evidence": [{"id": 10, "artifact_ids": [2], "claim_ids": [1]}],
    "claims": [{"id": 1, "required_evidence": [10]}],
}

MODEL_A = {
    "model_id": 1,
    "claims": [FORMAL_CLAIM, COMP_CLAIM],
    "evidence": [
        {"id": 10, "class": "formal", "accepted": True},
        {"id": 11, "class": "computational", "accepted": True},
    ],
}
MODEL_B = {
    "model_id": 2,
    "claims": [FORMAL_CLAIM, COMP_CLAIM],
    "evidence": [
        {"id": 10, "class": "formal", "accepted": True},
        {"id": 11, "class": "computational", "accepted": False},
    ],
}


def lean_control_vectors() -> list[dict[str, Any]]:
    """Expected outcomes of Lean Controls theorems, as executable predicates."""
    impact = compute_impact(SAMPLE_GRAPH, [0])
    models = [MODEL_A, MODEL_B]
    candidates = [FORMAL_CLAIM, COMP_CLAIM]
    return [
        {
            "id": "control_no_computational_to_formal",
            "expected": False,
            "actual": le(EvidenceClass.COMPUTATIONAL, EvidenceClass.FORMAL),
        },
        {
            "id": "control_formal_evidence_accepts",
            "expected": True,
            "actual": assure(
                FORMAL_CLAIM,
                [{"id": 10, "class": "formal", "accepted": True}],
                level="formal",
            ),
        },
        {
            "id": "control_computational_rejects_formal",
            "expected": False,
            "actual": assure(
                FORMAL_CLAIM,
                [{"id": 10, "class": "computational", "accepted": True}],
                level="formal",
            ),
        },
        {
            "id": "control_missing_evidence",
            "expected": False,
            "actual": assure(COMP_CLAIM, [], level="computational"),
        },
        {
            "id": "control_rejected_blocks_formal",
            "expected": False,
            "actual": assure(
                FORMAL_CLAIM,
                [{"id": 10, "class": "formal", "accepted": False}],
                level="formal",
            ),
        },
        {
            "id": "control_formal_covers_computational_claim",
            "expected": True,
            "actual": assure(
                COMP_CLAIM,
                [{"id": 11, "class": "formal", "accepted": True}],
                level="computational",
            ),
        },
        {
            "id": "control_empirical_rejects_formal",
            "expected": False,
            "actual": assure(
                FORMAL_CLAIM,
                [{"id": 10, "class": "empirical", "accepted": True}],
                level="formal",
            ),
        },
        {
            "id": "control_impact_reaches_claim",
            "expected": True,
            "actual": 1 in impact["affected_claims"],
        },
        {
            "id": "control_changed_artifact_in_impact",
            "expected": True,
            "actual": 0 in impact["affected_artifacts"],
        },
        {
            "id": "control_seed_reaches_processed",
            "expected": True,
            "actual": 1 in impact["affected_artifacts"],
        },
        {
            "id": "control_unrelated_declared_nonimpact",
            "expected": True,
            "actual": nonimpact(SAMPLE_GRAPH, [0], 99, dependency_complete=False)[
                "declared_nonimpact"
            ],
        },
        {
            "id": "control_incomplete_never_endorses",
            "expected": False,
            "actual": nonimpact(SAMPLE_GRAPH, [0], 99, dependency_complete=False)[
                "world_nonimpact_endorsed"
            ],
        },
        {
            "id": "control_agreement_contains_formal",
            "expected": True,
            "actual": FORMAL_CLAIM in agreement_core(models, candidates),
        },
        {
            "id": "control_dispute_contains_computational",
            "expected": True,
            "actual": COMP_CLAIM in dispute_frontier(models, candidates),
        },
        {
            "id": "control_distinguishing_computational",
            "expected": True,
            "actual": distinguishing(models, COMP_CLAIM),
        },
        {
            "id": "control_agreement_dispute_disjoint",
            "expected": True,
            "actual": FORMAL_CLAIM not in dispute_frontier(models, candidates)
            and model_supports(MODEL_A, FORMAL_CLAIM)
            and model_supports(MODEL_B, FORMAL_CLAIM),
        },
        {
            "id": "control_le_trans_formal_comp_prov",
            "expected": True,
            "actual": le(EvidenceClass.FORMAL, EvidenceClass.PROVENANCE),
        },
    ]


def run_differential() -> dict[str, Any]:
    vectors = lean_control_vectors()
    failures = [v for v in vectors if bool(v["actual"]) != bool(v["expected"])]
    return {
        "format": "pcs-epistemic-differential-v1",
        "total": len(vectors),
        "passed": len(vectors) - len(failures),
        "failed": len(failures),
        "failures": [{"id": f["id"], "expected": f["expected"], "actual": f["actual"]} for f in failures],
        "refinement_theorem": False,
        "production_authority": False,
    }
