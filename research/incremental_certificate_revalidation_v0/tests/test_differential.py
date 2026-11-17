from __future__ import annotations

import random

from model.graph import Graph, Node
from model.ops import OP_INT_ADD, OP_INT_CONST, OP_INT_MUL, DEFAULT_POLICY, default_registry
from reference.fresh import fresh_verify
from verifier.incremental import IncrementalVerifier


def random_graph(rng: random.Random, n: int) -> Graph:
    nodes = [Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, rng.randint(1, 5))]
    for i in range(1, n):
        if rng.random() < 0.25:
            nodes.append(Node(i, OP_INT_CONST, (), DEFAULT_POLICY, 1, rng.randint(1, 5)))
        else:
            deps = (rng.randrange(0, i), rng.randrange(0, i))
            op = rng.choice([OP_INT_ADD, OP_INT_MUL])
            nodes.append(Node(i, op, deps, DEFAULT_POLICY, 1, 0))
    return Graph(nodes=nodes)


def test_mutation_sequences_agree():
    rng = random.Random(1)
    graphs, muts = 30, 6
    total = 0
    for _ in range(graphs):
        g = random_graph(rng, rng.randint(8, 35))
        v = IncrementalVerifier(default_registry())
        assert v.initial_verify(g).accepted
        for _ in range(muts):
            inputs = [n for n in v.graph.nodes if n.op == OP_INT_CONST]
            target = rng.choice(inputs)
            new_ev = int(target.evidence) + rng.randint(1, 3)
            report = v.apply_node_changes(
                [Node(target.id, OP_INT_CONST, (), DEFAULT_POLICY, 1, new_ev)]
            )
            fresh = fresh_verify(v.graph, v.registry)
            total += 1
            assert report.accepted == fresh.accepted
            if report.accepted:
                assert report.outputs == fresh.outputs
                assert report.agrees_with_fresh
    assert total == graphs * muts
