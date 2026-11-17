"""Benchmark suite for incremental vs fresh verification."""
from __future__ import annotations

import random
import time
import tracemalloc
from dataclasses import dataclass
from typing import List, Sequence

from model.graph import Graph, Node
from model.ops import OP_INT_ADD, OP_INT_CONST, OP_INT_MUL, DEFAULT_POLICY, default_registry
from reference.fresh import fresh_verify
from verifier.incremental import IncrementalVerifier


@dataclass
class BenchRow:
    name: str
    nodes: int
    changes: int
    fresh_ms: float
    incr_ms: float
    reused: int
    rechecked: int
    agree: bool
    peak_kib: float

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "nodes": self.nodes,
            "changes": self.changes,
            "fresh_ms": self.fresh_ms,
            "incr_ms": self.incr_ms,
            "reused": self.reused,
            "rechecked": self.rechecked,
            "agree": self.agree,
            "peak_kib": self.peak_kib,
            "speedup": (self.fresh_ms / self.incr_ms) if self.incr_ms > 0 else None,
        }


def chain_graph(n: int) -> Graph:
    nodes = [Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 1)]
    for i in range(1, n):
        nodes.append(Node(i, OP_INT_ADD, (i - 1, 0), DEFAULT_POLICY, 1, 0))
    return Graph(nodes=nodes)


def wide_graph(width: int) -> Graph:
    nodes = [Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 1)]
    for i in range(1, width + 1):
        nodes.append(Node(i, OP_INT_CONST, (), DEFAULT_POLICY, 1, i))
    # binary reduction tree of adds
    cur = list(range(1, width + 1))
    nid = width + 1
    while len(cur) > 1:
        nxt = []
        for j in range(0, len(cur), 2):
            if j + 1 < len(cur):
                nodes.append(Node(nid, OP_INT_ADD, (cur[j], cur[j + 1]), DEFAULT_POLICY, 1, 0))
                nxt.append(nid)
                nid += 1
            else:
                nxt.append(cur[j])
        cur = nxt
    return Graph(nodes=nodes)


def branching_graph(depth: int) -> Graph:
    nodes: List[Node] = []
    n_leaves = 2 ** (depth - 1)
    for i in range(n_leaves):
        nodes.append(Node(i, OP_INT_CONST, (), DEFAULT_POLICY, 1, 1))
    next_id = n_leaves
    level = list(range(n_leaves))
    while len(level) > 1:
        nxt = []
        for j in range(0, len(level), 2):
            if j + 1 < len(level):
                nodes.append(Node(next_id, OP_INT_ADD, (level[j], level[j + 1]), DEFAULT_POLICY, 1, 0))
                nxt.append(next_id)
                next_id += 1
            else:
                nxt.append(level[j])
        level = nxt
    return Graph(nodes=nodes)


def shared_subexpr_graph(k: int) -> Graph:
    nodes = [
        Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 2),
        Node(1, OP_INT_CONST, (), DEFAULT_POLICY, 1, 3),
        Node(2, OP_INT_MUL, (0, 1), DEFAULT_POLICY, 1, 0),
    ]
    for i in range(k):
        nodes.append(Node(3 + i, OP_INT_ADD, (2, 0), DEFAULT_POLICY, 1, 0))
    return Graph(nodes=nodes)


def scientific_synthetic(n_meas: int) -> Graph:
    nodes: List[Node] = []
    for i in range(n_meas):
        nodes.append(Node(i, OP_INT_CONST, (), DEFAULT_POLICY, 1, (i % 97) + 1))
    t0 = n_meas
    transform_ids = []
    for i in range(0, n_meas - 1, 2):
        nid = t0 + len(transform_ids)
        nodes.append(Node(nid, OP_INT_ADD, (i, i + 1), DEFAULT_POLICY, 1, 0))
        transform_ids.append(nid)
    # reduce transforms
    cur = transform_ids
    nid = t0 + len(transform_ids)
    while len(cur) > 1:
        nxt = []
        for j in range(0, len(cur), 2):
            if j + 1 < len(cur):
                nodes.append(Node(nid, OP_INT_ADD, (cur[j], cur[j + 1]), DEFAULT_POLICY, 1, 0))
                nxt.append(nid)
                nid += 1
            else:
                nxt.append(cur[j])
        cur = nxt
    return Graph(nodes=nodes)


def _run_case(name: str, g: Graph, change_ids: Sequence[int]) -> BenchRow:
    reg = default_registry()
    v = IncrementalVerifier(reg)
    assert v.initial_verify(g).accepted
    replacements = []
    for cid in change_ids:
        node = g.by_id()[cid]
        if node.op == OP_INT_CONST:
            replacements.append(
                Node(node.id, node.op, node.deps, node.policy, node.version, node.evidence + 1)
            )
        else:
            replacements.append(
                Node(node.id, node.op, node.deps, node.policy, node.version, node.evidence + 1)
            )
    new_g = g.replace_nodes(replacements)

    tracemalloc.start()
    t0 = time.perf_counter()
    fresh = fresh_verify(new_g, reg)
    t1 = time.perf_counter()
    # Time incremental without nested fresh comparison (fair wall-clock).
    incr = v.revalidate(new_g, list(change_ids), compare_fresh=False)
    t2 = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    agree = incr.accepted == fresh.accepted and (
        not incr.accepted or incr.outputs == fresh.outputs
    )
    return BenchRow(
        name=name,
        nodes=len(g.nodes),
        changes=len(change_ids),
        fresh_ms=(t1 - t0) * 1000,
        incr_ms=(t2 - t1) * 1000,
        reused=len(incr.reused),
        rechecked=len(incr.rechecked),
        agree=agree,
        peak_kib=peak / 1024,
    )


def run_benchmarks(seed: int = 0) -> List[BenchRow]:
    rng = random.Random(seed)
    rows: List[BenchRow] = []
    rows.append(_run_case("chain_200_leaf", chain_graph(200), [199]))
    rows.append(_run_case("chain_200_root", chain_graph(200), [0]))
    rows.append(_run_case("wide_300_one_input", wide_graph(300), [1]))
    rows.append(_run_case("branch_depth7_leaf", branching_graph(7), [0]))
    rows.append(_run_case("shared_50_shared_mid", shared_subexpr_graph(50), [2]))
    rows.append(_run_case("shared_50_input", shared_subexpr_graph(50), [0]))
    sci = scientific_synthetic(2000)
    leaf = rng.sample([n.id for n in sci.nodes if n.op == OP_INT_CONST], 3)
    rows.append(_run_case("sci_2000_sparse3", sci, leaf))
    many = rng.sample([n.id for n in sci.nodes if n.op == OP_INT_CONST], 100)
    rows.append(_run_case("sci_2000_dense100", sci, many))
    sci10k = scientific_synthetic(10000)
    rows.append(
        _run_case(
            "sci_10000_sparse5",
            sci10k,
            rng.sample([n.id for n in sci10k.nodes if n.op == OP_INT_CONST], 5),
        )
    )
    return rows
