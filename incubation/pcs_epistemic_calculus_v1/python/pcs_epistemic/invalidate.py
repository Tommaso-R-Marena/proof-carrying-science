"""Declared-graph invalidation with explicit completeness gate."""

from __future__ import annotations

from collections import deque
from typing import Any, Mapping, Sequence


def _workflow_nodes(graph: Mapping[str, Any]) -> list:
    """Accept either a bare node list or commons `{nodes: [...]}` shape."""
    workflow = graph.get("workflow", [])
    if isinstance(workflow, dict):
        nodes = workflow.get("nodes", [])
        return nodes if isinstance(nodes, list) else []
    return workflow if isinstance(workflow, list) else []


def _reach_artifacts(graph: Mapping[str, Any], changed: Sequence[str | int]) -> list:
    consumers: dict[Any, list] = {}
    for node in _workflow_nodes(graph):
        for aid in node.get("inputs", []):
            consumers.setdefault(aid, []).append(node)
    affected = set(changed)
    q = deque(changed)
    while q:
        aid = q.popleft()
        for node in consumers.get(aid, []):
            for out in node.get("outputs", []):
                if out not in affected:
                    affected.add(out)
                    q.append(out)
    return sorted(affected, key=lambda x: (str(type(x)), str(x)))


def compute_impact(graph: Mapping[str, Any], changed: Sequence[str | int]) -> dict[str, list]:
    arts = _reach_artifacts(graph, changed)
    art_set = set(arts)
    affected_evidence = []
    for ev in graph.get("evidence", []):
        if art_set.intersection(ev.get("artifact_ids", [])):
            affected_evidence.append(ev["id"])
    ev_set = set(affected_evidence)
    affected_claims = []
    for claim in graph.get("claims", []):
        if ev_set.intersection(claim.get("required_evidence", [])):
            affected_claims.append(claim["id"])
        else:
            # Also reopen claims cited by affected evidence.
            for ev in graph.get("evidence", []):
                if ev["id"] in ev_set and claim["id"] in ev.get("claim_ids", []):
                    affected_claims.append(claim["id"])
                    break
    # Stable unique
    def uniq(xs):
        out = []
        for x in xs:
            if x not in out:
                out.append(x)
        return out

    return {
        "changed_artifacts": list(changed),
        "affected_artifacts": arts,
        "affected_evidence": uniq(affected_evidence),
        "affected_claims": uniq(affected_claims),
    }


def nonimpact(
    graph: Mapping[str, Any],
    changed: Sequence[str | int],
    claim_id: str | int,
    *,
    dependency_complete: bool,
) -> dict[str, Any]:
    report = compute_impact(graph, changed)
    declared = claim_id not in report["affected_claims"]
    return {
        "format": "pcs-epistemic-nonimpact-v1",
        "claim_id": claim_id,
        "declared_nonimpact": declared,
        "dependency_complete": bool(dependency_complete),
        "world_nonimpact_endorsed": bool(dependency_complete) and declared,
        "impact": report,
    }
