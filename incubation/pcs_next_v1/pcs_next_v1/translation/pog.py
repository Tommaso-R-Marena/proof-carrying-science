"""Proof Obligation Graph with cycle detection and invalidation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.canonical import canonical_hash
from ..core.errors import ErrorCode, PcsNextError
from ..core.schemas import POG_FORMAT
from ..core.statuses import AssuranceStatus, classify_status


@dataclass
class ObligationNode:
    id: str
    claim: str
    assumptions: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)
    lemmas: list[str] = field(default_factory=list)
    method: str = "unspecified"
    status: AssuranceStatus = AssuranceStatus.OPEN
    counterexamples: list[str] = field(default_factory=list)
    external_deps: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claim": self.claim,
            "assumptions": self.assumptions,
            "evidence_requirements": self.evidence_requirements,
            "lemmas": self.lemmas,
            "method": self.method,
            "status": self.status.value,
            "counterexamples": self.counterexamples,
            "external_deps": self.external_deps,
            "artifact_ids": self.artifact_ids,
            "depends_on": self.depends_on,
        }


class ProofObligationGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, ObligationNode] = {}

    def add(self, node: ObligationNode) -> None:
        if node.id in self.nodes:
            raise PcsNextError(ErrorCode.SCHEMA_INVALID, f"duplicate obligation id {node.id}")
        self.nodes[node.id] = node

    def edges(self) -> list[tuple[str, str]]:
        out = []
        for n in self.nodes.values():
            for d in n.depends_on:
                out.append((n.id, d))
        return out

    def detect_cycles(self) -> list[list[str]]:
        cycles: list[list[str]] = []
        visiting: set[str] = set()
        visited: set[str] = set()
        stack: list[str] = []

        def dfs(u: str) -> None:
            visiting.add(u)
            stack.append(u)
            for _, v in ((a, b) for a, b in self.edges() if a == u):
                if v not in self.nodes:
                    continue
                if v in visiting:
                    i = stack.index(v)
                    cycles.append(stack[i:] + [v])
                elif v not in visited:
                    dfs(v)
            stack.pop()
            visiting.remove(u)
            visited.add(u)

        for nid in list(self.nodes):
            if nid not in visited:
                dfs(nid)
        return cycles

    def invalidate_from(self, artifact_id: str) -> list[str]:
        touched = [n.id for n in self.nodes.values() if artifact_id in n.artifact_ids]
        changed = set(touched)
        # upstream dependents
        reverse: dict[str, list[str]] = {k: [] for k in self.nodes}
        for a, b in self.edges():
            reverse.setdefault(b, []).append(a)
        queue = list(touched)
        while queue:
            u = queue.pop()
            for dep in reverse.get(u, []):
                if dep not in changed:
                    changed.add(dep)
                    queue.append(dep)
        for nid in changed:
            self.nodes[nid].status = AssuranceStatus.OPEN
        return sorted(changed)

    def minimal_failed(self) -> list[str]:
        failed = [n.id for n in self.nodes.values() if n.status == AssuranceStatus.REFUTED]
        # keep nodes whose deps are not also failed
        failed_set = set(failed)
        minimal = []
        for nid in failed:
            deps = set(self.nodes[nid].depends_on)
            if not (deps & failed_set):
                minimal.append(nid)
        return minimal

    def to_dict(self) -> dict[str, Any]:
        cycles = self.detect_cycles()
        if cycles:
            raise PcsNextError(ErrorCode.STATE_ILLEGAL, "POG contains cycles", details={"cycles": cycles})
        body = {
            "format": POG_FORMAT,
            "nodes": {k: v.to_dict() for k, v in sorted(self.nodes.items())},
            "edges": [{"from": a, "to": b} for a, b in self.edges()],
        }
        body["content_hash"] = canonical_hash({k: v for k, v in body.items() if k != "content_hash"})
        return body

    def reviewer_view(self) -> str:
        lines = ["# Proof Obligation Graph", ""]
        for n in sorted(self.nodes.values(), key=lambda x: x.id):
            lines.append(f"## {n.id} [{n.status.value}]")
            lines.append(f"- Claim: {n.claim}")
            lines.append(f"- Method: {n.method}")
            if n.depends_on:
                lines.append(f"- Depends on: {', '.join(n.depends_on)}")
            if n.counterexamples:
                lines.append(f"- Counterexamples: {', '.join(n.counterexamples)}")
            lines.append("")
        return "\n".join(lines)


def set_status(graph: ProofObligationGraph, node_id: str, status: str) -> None:
    graph.nodes[node_id].status = classify_status(status)
