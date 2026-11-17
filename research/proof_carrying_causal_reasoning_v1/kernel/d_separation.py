"""Exact d-separation (Bayes-ball) and backdoor path enumeration."""

from __future__ import annotations

from collections import deque
from typing import Iterable, Set

from .dag import CausalDAG, GraphError


def d_separated(
    graph: CausalDAG,
    x: Iterable[str],
    y: Iterable[str],
    z: Iterable[str] = (),
) -> bool:
    """True iff X ⊥ Y | Z graphically in the DAG (Markov interpretation)."""
    X = _as_set(x, graph)
    Y = _as_set(y, graph)
    Z = _as_set(z, graph)
    if X & Y:
        raise GraphError("d-separation requires disjoint X and Y")
    if (X | Y) & Z:
        raise GraphError("conditioning set must be disjoint from X and Y")
    if not X or not Y:
        return True

    parents = {n: graph.parents(n) for n in graph.nodes}
    children = {n: graph.children(n) for n in graph.nodes}
    scheduled: set[tuple[str, int]] = set()
    visited: set[tuple[str, int]] = set()
    q: deque[tuple[str, int]] = deque()

    for s in X:
        q.append((s, 0))
        q.append((s, 1))
        scheduled.add((s, 0))
        scheduled.add((s, 1))

    while q:
        node, direction = q.popleft()
        if (node, direction) in visited:
            continue
        visited.add((node, direction))
        if node in Y:
            return False

        if direction == 0:  # going up
            if node not in Z:
                for p in parents[node]:
                    item = (p, 0)
                    if item not in scheduled:
                        scheduled.add(item)
                        q.append(item)
                for c in children[node]:
                    item = (c, 1)
                    if item not in scheduled:
                        scheduled.add(item)
                        q.append(item)
        else:  # going down
            if node not in Z:
                for c in children[node]:
                    item = (c, 1)
                    if item not in scheduled:
                        scheduled.add(item)
                        q.append(item)
            if node in Z or _has_descendant_in(graph, node, Z):
                for p in parents[node]:
                    item = (p, 0)
                    if item not in scheduled:
                        scheduled.add(item)
                        q.append(item)
    return True


def path_blocked(graph: CausalDAG, path: list[str], z: Iterable[str]) -> bool:
    """Whether an undirected path is blocked by Z under standard d-separation."""
    Z = set(z)
    if len(path) < 2:
        return True
    for i in range(1, len(path) - 1):
        prev, mid, nxt = path[i - 1], path[i], path[i + 1]
        is_collider = (mid in graph.children(prev)) and (mid in graph.children(nxt))
        if is_collider:
            if mid not in Z and not (graph.descendants(mid) & Z):
                return True
        else:
            if mid in Z:
                return True
    return False


def find_backdoor_paths(graph: CausalDAG, treatment: str, outcome: str) -> list[list[str]]:
    """Undirected paths from treatment to outcome that begin with an arrow into treatment."""
    if treatment not in graph.nodes or outcome not in graph.nodes:
        raise GraphError("unknown treatment or outcome")
    adj: dict[str, list[tuple[str, str]]] = {n: [] for n in graph.nodes}
    for u, v in graph.edges:
        adj[u].append((v, "→"))
        adj[v].append((u, "←"))

    paths: list[list[str]] = []

    def dfs(cur: str, path: list[str], first_orient: str | None) -> None:
        if cur == outcome and len(path) > 1:
            if first_orient == "←":
                paths.append(list(path))
            return
        for nxt, orient in adj[cur]:
            if nxt in path:
                continue
            fo = first_orient if first_orient is not None else orient
            path.append(nxt)
            dfs(nxt, path, fo)
            path.pop()

    dfs(treatment, [treatment], None)
    return paths


def _has_descendant_in(graph: CausalDAG, node: str, z: Set[str]) -> bool:
    if node in z:
        return True
    return bool(graph.descendants(node) & z)


def _as_set(xs: Iterable[str], graph: CausalDAG) -> set[str]:
    out = set()
    for x in xs:
        if x not in graph.nodes:
            raise GraphError(f"unknown node: {x!r}")
        out.add(x)
    return out
