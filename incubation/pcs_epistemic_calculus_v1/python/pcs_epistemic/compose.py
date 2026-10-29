"""Certificate composition along pipelines."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .assures import assure, find_evidence, supports_claim
from .lattice import EvidenceClass


def compose_assures(
    claim_upstream: Mapping[str, Any],
    evidence_upstream: Sequence[Mapping[str, Any]],
    claim_downstream: Mapping[str, Any],
    evidence_downstream: Sequence[Mapping[str, Any]],
    *,
    level_upstream: EvidenceClass | str,
    level_downstream: EvidenceClass | str,
) -> dict[str, Any]:
    """Compose two graded assurances when evidence ids do not collide on the right."""
    ok_up = assure(claim_upstream, evidence_upstream, level=level_upstream)
    ok_down = assure(claim_downstream, evidence_downstream, level=level_downstream)
    required = claim_downstream.get("required_evidence", [])
    disjoint = all(find_evidence(evidence_upstream, eid) is None for eid in required)
    combined = list(evidence_upstream) + list(evidence_downstream)
    supported = ok_up and ok_down and disjoint and supports_claim(claim_downstream, combined)
    return {
        "format": "pcs-epistemic-composition-v1",
        "upstream_assured": ok_up,
        "downstream_assured": ok_down,
        "evidence_disjoint": disjoint,
        "composed_assured": supported,
        "combined_evidence_ids": [e["id"] for e in combined],
    }
