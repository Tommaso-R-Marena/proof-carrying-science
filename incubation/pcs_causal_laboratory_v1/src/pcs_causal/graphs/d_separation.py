"""Exact d-separation on finite DAGs (Bayes-ball / moralized ancestral graph)."""

from __future__ import annotations

from typing import FrozenSet, Iterable, Set

from pcs_causal.graphs.dag import CausalDAG, GraphError


def d_separated(
    graph: CausalDAG,
    x: Iterable[str],
    y: Iterable[str],
    z: Iterable[str] = (),
) -> bool:
    """Return True iff X ⊥ Y | Z in the DAG under the usual Markov interpretation.

    This is a graphical criterion. It equals conditional independence in every
    distribution that is Markov relative to the DAG; faithfulness is not assumed.
    """
    X = _as_set(x, graph)
    Y = _as_set(y, graph)
    Z = _as_set(z, graph)
    if X & Y:
        raise GraphError("d-separation requires disjoint X and Y")
    if (X | Y) & Z:
        # conditioning on the queried sets is ill-posed for independence queries
        raise GraphError("conditioning set must be disjoint from X and Y")
    if not X or not Y:
        return True

    # Bayes-ball algorithm (Shachter 1998 / Pearl)
    # Direction: 0 = up (toward parents), 1 = down (toward children)
    from collections import deque

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

    reachable: set[str] = set()

    while q:
        node, direction = q.popleft()
        if (node, direction) in visited:
            continue
        visited.add((node, direction))
        if node in Y:
            return False
        reachable.add(node)

        if direction == 0:  # arriving from child (going up)
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
        else:  # arriving from parent (going down)
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


def _has_descendant_in(graph: CausalDAG, node: str, z: Set[str]) -> bool:
    if node in z:
        return True
    return bool(graph.descendants(node) & z)


def find_backdoor_paths(graph: CausalDAG, treatment: str, outcome: str) -> list[list[str]]:
    """Enumerate undirected paths from treatment to outcome that start with an arrow into treatment.

    Path representation: list of nodes. A backdoor path is a path from X to Y with
    an arrow into X (Pearl).
    """
    if treatment not in graph.nodes or outcome not in graph.nodes:
        raise GraphError("unknown treatment or outcome")
    # Build undirected adjacency with orientation labels
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


def path_blocked(graph: CausalDAG, path: Sequence[str], z: Iterable[str]) -> bool:
    """Whether an undirected path is blocked by Z (d-separation path criterion)."""
    Z = set(z)
    if len(path) < 2:
        return True
    for i in range(1, len(path) - 1):
        a, mid, b = path[i - 1], path[i], path[i + 1]
        is_coll = graph.is_collider(a, mid, b)
        if is_coll:
            # collider (and descendants) unblock when conditioned
            if mid not in Z and not (graph.descendants(mid) & Z):
                return True  # blocked by unconditioned collider
        else:
            # chain or fork blocked by conditioning on mid
            if mid in Z:
                return True
    # endpoints: if no non-collider/collider rule blocked, open unless empty interior handled
    # Check colliders that might leave path open
    for i in range(1, len(path) - 1):
        a, mid, b = path[i - 1], path[i], path[i + 1]
        if graph.is_collider(a, mid, b):
            if mid in Z or (graph.descendants(mid) & Z):
                continue
            return True
        if mid in Z:
            return True
    return False


from typing import Sequence  # noqa: E402  — kept local clarity


def _as_set(xs: Iterable[str], graph: CausalDAG) -> Set[str]:
    s = set(xs)
    if not s <= graph.nodes:
        raise GraphError(f"unknown nodes in query: {sorted(s - graph.nodes)}")
    return s
