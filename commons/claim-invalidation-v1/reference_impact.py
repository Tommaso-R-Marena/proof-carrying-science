from __future__ import annotations
from collections import defaultdict, deque
from typing import Any


def impact_from_artifacts(cert: dict[str, Any], changed_artifacts: set[str]) -> dict[str, list[str]]:
    """Public snapshot of PCS conservative declared-graph invalidation semantics."""
    nodes = cert.get("workflow", {}).get("nodes", [])
    consumers: dict[str, list[dict]] = defaultdict(list)
    for node in nodes:
        for aid in node.get("inputs", []):
            consumers[aid].append(node)

    affected_artifacts = set(changed_artifacts)
    affected_nodes: set[str] = set()
    q = deque(changed_artifacts)
    while q:
        aid = q.popleft()
        for node in consumers.get(aid, []):
            nid = node.get("id")
            if nid:
                affected_nodes.add(nid)
            for out in node.get("outputs", []):
                if out not in affected_artifacts:
                    affected_artifacts.add(out)
                    q.append(out)

    affected_evidence: set[str] = set()
    affected_claims: set[str] = set()
    for evidence in cert.get("evidence", []):
        if affected_artifacts.intersection(evidence.get("artifact_ids", [])):
            if evidence.get("id"):
                affected_evidence.add(evidence["id"])
            affected_claims.update(evidence.get("claim_ids", []))

    for claim in cert.get("claims", []):
        if affected_evidence.intersection(claim.get("required_evidence", [])):
            affected_claims.add(claim.get("id"))

    return {
        "changed_artifacts": sorted(changed_artifacts),
        "affected_artifacts": sorted(affected_artifacts),
        "affected_workflow_nodes": sorted(affected_nodes),
        "affected_evidence": sorted(affected_evidence),
        "affected_claims": sorted(x for x in affected_claims if x),
    }
