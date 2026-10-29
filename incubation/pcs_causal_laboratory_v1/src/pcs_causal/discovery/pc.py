"""PC-style constraint-based discovery with explicit uncertainty about orientation.

Observationally inferred graphs are candidate / Markov-equivalence information,
not established causal truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.hypothesis.states import ScientificStatus


CIOracle = Callable[[str, str, Tuple[str, ...]], bool]


@dataclass
class PCResult:
    nodes: Tuple[str, ...]
    skeleton_edges: Set[frozenset]
    oriented_edges: Set[Tuple[str, str]]
    ambiguous_edges: Set[frozenset]
    separation_sets: Dict[frozenset, Tuple[str, ...]]
    status: ScientificStatus
    notes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "nodes": list(self.nodes),
            "skeleton_edges": [sorted(e) for e in sorted(self.skeleton_edges, key=lambda x: sorted(x))],
            "oriented_edges": sorted([list(e) for e in self.oriented_edges]),
            "ambiguous_edges": [sorted(e) for e in sorted(self.ambiguous_edges, key=lambda x: sorted(x))],
            "status": self.status.value,
            "notes": list(self.notes),
            "interpretation": (
                "Result is a candidate CPDAG/MEC sketch under CI oracle + faithfulness. "
                "Not established causal truth."
            ),
        }


def pc_oracle(
    nodes: Sequence[str],
    independent: CIOracle,
    max_cond_size: Optional[int] = None,
) -> PCResult:
    """PC skeleton + collider orientation using an exact CI oracle."""
    nodes = tuple(nodes)
    adj: Dict[str, Set[str]] = {n: set(nodes) - {n} for n in nodes}
    sep: Dict[frozenset, Tuple[str, ...]] = {}
    l = 0
    max_l = len(nodes) - 2 if max_cond_size is None else max_cond_size
    while l <= max_l:
        removed = []
        for x in nodes:
            for y in list(adj[x]):
                if y <= x:
                    continue
                candidates = sorted(adj[x] - {y})
                if len(candidates) < l:
                    continue
                for z in combinations(candidates, l):
                    if independent(x, y, z):
                        removed.append((x, y, z))
                        break
        for x, y, z in removed:
            adj[x].discard(y)
            adj[y].discard(x)
            sep[frozenset((x, y))] = z
        l += 1
        # stop if no adjacency large enough
        if all(len(adj[n]) <= l for n in nodes):
            # continue until l exceeds
            pass

    skeleton = {frozenset((x, y)) for x in nodes for y in adj[x] if x < y}

    # Orient v-structures: x - z - y with x not adj y, z not in sepset(x,y)
    oriented: Set[Tuple[str, str]] = set()
    for z in nodes:
        neigh = sorted(adj[z])
        for x, y in combinations(neigh, 2):
            if frozenset((x, y)) in skeleton:
                continue
            s = sep.get(frozenset((x, y)), ())
            if z not in s:
                oriented.add((x, z))
                oriented.add((y, z))

    # Remaining undirected skeleton edges
    oriented_undirected = {frozenset(e) for e in oriented}
    ambiguous = set()
    for e in skeleton:
        a, b = tuple(e)
        if (a, b) in oriented or (b, a) in oriented:
            continue
        ambiguous.add(e)

    return PCResult(
        nodes=nodes,
        skeleton_edges=skeleton,
        oriented_edges=oriented,
        ambiguous_edges=ambiguous,
        separation_sets=sep,
        status=ScientificStatus.OPEN,
        notes=(
            "Markov equivalence / orientation ambiguity preserved in ambiguous_edges.",
            "Faithfulness assumed for oracle recovery of skeleton; not empirically guaranteed.",
            "Candidate graph ≠ causal truth.",
        ),
    )


def pc_from_dag_oracle(true_dag: CausalDAG) -> PCResult:
    """Oracle PC using d-separation on a known DAG (tests algorithm, not nature)."""
    from pcs_causal.graphs.d_separation import d_separated

    nodes = tuple(sorted(true_dag.nodes))

    def indep(x, y, z):
        return d_separated(true_dag, [x], [y], list(z))

    return pc_oracle(nodes, indep)


def pc_statistical(
    data: np.ndarray,
    var_names: Sequence[str],
    alpha: float = 0.05,
    kind: str = "gaussian",
) -> PCResult:
    from pcs_causal.discovery.ci_tests import (
        discrete_g_test,
        gaussian_partial_correlation_test,
    )

    names = tuple(var_names)
    idx = {n: i for i, n in enumerate(names)}

    def indep(x, y, z):
        cond = tuple(idx[v] for v in z)
        if kind == "gaussian":
            r = gaussian_partial_correlation_test(data, idx[x], idx[y], cond, alpha)
        elif kind == "discrete":
            r = discrete_g_test(data, idx[x], idx[y], cond, alpha)
        else:
            raise ValueError(kind)
        return r.independent

    res = pc_oracle(names, indep)
    res.notes = res.notes + (
        f"Statistical CI tests ({kind}) with alpha={alpha}; finite-sample errors possible.",
        "Do not treat output as established causal mechanism.",
    )
    return res
