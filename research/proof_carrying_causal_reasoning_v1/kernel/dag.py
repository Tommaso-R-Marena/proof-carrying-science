"""Finite directed acyclic causal graphs."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import FrozenSet, Iterable, Mapping


class GraphError(ValueError):
    """Malformed or unsupported graph construction."""


@dataclass(frozen=True, slots=True)
class CausalDAG:
    """Finite DAG. Edge X→Y means Y's mechanism may depend on X."""

    nodes: FrozenSet[str]
    edges: FrozenSet[tuple[str, str]]

    def __post_init__(self) -> None:
        for u, v in self.edges:
            if u not in self.nodes or v not in self.nodes:
                raise GraphError(f"edge ({u!r}, {v!r}) references unknown node")
            if u == v:
                raise GraphError(f"self-loop forbidden: {u!r}")
        if self._has_cycle():
            raise GraphError("graph contains a directed cycle; DAG required")

    @classmethod
    def from_edges(
        cls,
        nodes: Iterable[str],
        edges: Iterable[tuple[str, str]],
    ) -> "CausalDAG":
        node_list = list(nodes)
        if len(node_list) != len(set(node_list)):
            raise GraphError("duplicate node identifier")
        return cls(
            nodes=frozenset(str(n) for n in node_list),
            edges=frozenset((str(u), str(v)) for u, v in edges),
        )

    @classmethod
    def from_parents(cls, parents: Mapping[str, Iterable[str]]) -> "CausalDAG":
        nodes = frozenset(parents)
        edges: set[tuple[str, str]] = set()
        for child, pars in parents.items():
            for p in pars:
                if p not in nodes:
                    raise GraphError(f"parent {p!r} of {child!r} not in nodes")
                edges.add((p, child))
        return cls(nodes=nodes, edges=frozenset(edges))

    def parents(self, node: str) -> FrozenSet[str]:
        self._require(node)
        return frozenset(u for u, v in self.edges if v == node)

    def children(self, node: str) -> FrozenSet[str]:
        self._require(node)
        return frozenset(v for u, v in self.edges if u == node)

    def ancestors(self, node: str) -> FrozenSet[str]:
        self._require(node)
        seen: set[str] = set()
        q = deque(self.parents(node))
        while q:
            n = q.popleft()
            if n in seen:
                continue
            seen.add(n)
            q.extend(self.parents(n))
        return frozenset(seen)

    def descendants(self, node: str) -> FrozenSet[str]:
        self._require(node)
        seen: set[str] = set()
        q = deque(self.children(node))
        while q:
            n = q.popleft()
            if n in seen:
                continue
            seen.add(n)
            q.extend(self.children(n))
        return frozenset(seen)

    def topological_order(self) -> tuple[str, ...]:
        indeg = {n: 0 for n in self.nodes}
        for _, v in self.edges:
            indeg[v] += 1
        q = deque(sorted(n for n, d in indeg.items() if d == 0))
        order: list[str] = []
        while q:
            n = q.popleft()
            order.append(n)
            for c in sorted(self.children(n)):
                indeg[c] -= 1
                if indeg[c] == 0:
                    q.append(c)
        if len(order) != len(self.nodes):
            raise GraphError("topological sort failed")
        return tuple(order)

    def mutilate(self, interventions: Iterable[str]) -> "CausalDAG":
        """Remove incoming edges to intervened nodes (do-operator graph)."""
        cut = frozenset(interventions)
        for n in cut:
            self._require(n)
        return CausalDAG(
            nodes=self.nodes,
            edges=frozenset((u, v) for u, v in self.edges if v not in cut),
        )

    def to_dict(self) -> dict:
        return {
            "nodes": sorted(self.nodes),
            "edges": sorted([list(e) for e in self.edges]),
        }

    def _require(self, node: str) -> None:
        if node not in self.nodes:
            raise GraphError(f"unknown node: {node!r}")

    def _has_cycle(self) -> bool:
        indeg = {n: 0 for n in self.nodes}
        for _, v in self.edges:
            indeg[v] += 1
        q = deque(n for n, d in indeg.items() if d == 0)
        seen = 0
        while q:
            n = q.popleft()
            seen += 1
            for c in self.children(n):
                indeg[c] -= 1
                if indeg[c] == 0:
                    q.append(c)
        return seen != len(self.nodes)
