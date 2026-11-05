"""Directed acyclic causal graphs with explicit edge semantics.

A directed edge X → Y means: in the structural model class associated with
the graph, Y's structural mechanism may depend on X. Absence of an edge does
not by itself imply causal independence unless the Markov/graphical
assumptions of the model class are stated separately.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import FrozenSet, Iterable, Iterator, Mapping, Sequence, Set


class GraphError(ValueError):
    """Malformed or unsupported graph construction."""


@dataclass(frozen=True, slots=True)
class CausalDAG:
    """Finite DAG over named variables.

    Attributes
    ----------
    nodes:
        Finite set of variable names.
    edges:
        Directed edges (parent, child). Acyclicity is enforced at construction.
    """

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
        node_set = frozenset(nodes)
        if len(list(nodes) if not isinstance(nodes, (set, frozenset)) else nodes) != len(
            node_set
        ) and isinstance(nodes, list):
            # detect duplicates in list construction path
            seen: set[str] = set()
            for n in nodes:
                if n in seen:
                    raise GraphError(f"duplicate node identifier: {n!r}")
                seen.add(n)
        edge_set = frozenset((str(u), str(v)) for u, v in edges)
        return cls(nodes=frozenset(str(n) for n in node_set), edges=edge_set)

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
        stack = list(self.parents(node))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self.parents(cur))
        return frozenset(seen)

    def descendants(self, node: str) -> FrozenSet[str]:
        self._require(node)
        seen: set[str] = set()
        stack = list(self.children(node))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self.children(cur))
        return frozenset(seen)

    def topological_order(self) -> list[str]:
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
            raise GraphError("topological sort failed (cycle)")
        return order

    def directed_paths(self, source: str, target: str) -> list[list[str]]:
        """Enumerate all directed paths from source to target."""
        self._require(source)
        self._require(target)
        paths: list[list[str]] = []

        def dfs(cur: str, path: list[str]) -> None:
            if cur == target and len(path) > 1:
                paths.append(list(path))
                return
            for c in sorted(self.children(cur)):
                if c in path:
                    continue
                path.append(c)
                dfs(c, path)
                path.pop()

        dfs(source, [source])
        return paths

    def induce(self, nodes: Iterable[str]) -> "CausalDAG":
        keep = frozenset(nodes)
        if not keep <= self.nodes:
            raise GraphError("induce on non-subset of nodes")
        edges = frozenset((u, v) for u, v in self.edges if u in keep and v in keep)
        return CausalDAG(nodes=keep, edges=edges)

    def ancestral_subgraph(self, nodes: Iterable[str]) -> "CausalDAG":
        seed = set(nodes)
        if not seed <= self.nodes:
            raise GraphError("ancestral subgraph on unknown nodes")
        closure = set(seed)
        for n in list(seed):
            closure |= set(self.ancestors(n))
        return self.induce(closure)

    def mutilate(self, intervene: Iterable[str]) -> "CausalDAG":
        """Graph mutilation for hard interventions: remove incoming edges to intervened nodes."""
        intervened = frozenset(intervene)
        if not intervened <= self.nodes:
            raise GraphError("intervention on unknown node")
        edges = frozenset((u, v) for u, v in self.edges if v not in intervened)
        return CausalDAG(nodes=self.nodes, edges=edges)

    def is_collider(self, a: str, mid: str, b: str) -> bool:
        """True iff a → mid ← b (unordered endpoints)."""
        return (a, mid) in self.edges and (b, mid) in self.edges and a != b

    def is_fork(self, a: str, mid: str, b: str) -> bool:
        return (mid, a) in self.edges and (mid, b) in self.edges and a != b

    def is_chain(self, a: str, mid: str, b: str) -> bool:
        return ((a, mid) in self.edges and (mid, b) in self.edges) or (
            (b, mid) in self.edges and (mid, a) in self.edges
        )

    def neighbors(self, node: str) -> FrozenSet[str]:
        return self.parents(node) | self.children(node)

    def undirected_edges(self) -> FrozenSet[frozenset[str]]:
        return frozenset(frozenset((u, v)) for u, v in self.edges)

    def to_dict(self) -> dict:
        return {
            "nodes": sorted(self.nodes),
            "edges": sorted([list(e) for e in self.edges]),
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "CausalDAG":
        nodes = data["nodes"]
        edges = [tuple(e) for e in data["edges"]]
        return cls.from_edges(nodes, edges)

    def _require(self, node: str) -> None:
        if node not in self.nodes:
            raise GraphError(f"unknown node: {node!r}")

    def _has_cycle(self) -> bool:
        white, gray, black = 0, 1, 2
        color = {n: white for n in self.nodes}
        adj = {n: list(self.children(n)) for n in self.nodes}

        def visit(n: str) -> bool:
            color[n] = gray
            for c in adj[n]:
                if color[c] == gray:
                    return True
                if color[c] == white and visit(c):
                    return True
            color[n] = black
            return False

        return any(color[n] == white and visit(n) for n in self.nodes)

    def __iter__(self) -> Iterator[str]:
        return iter(self.topological_order())
