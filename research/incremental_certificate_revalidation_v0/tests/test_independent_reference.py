"""Cross-check shared OpRegistry against independent arithmetic reference."""
from __future__ import annotations

from model.graph import Graph, Node
from model.ops import DEFAULT_POLICY, OP_INT_ADD, OP_INT_CONST, OP_INT_MUL, default_registry
from reference.fresh import fresh_verify
from reference.independent_arith import evaluate_int_dag
from verifier.incremental import IncrementalVerifier


def test_independent_matches_fresh_and_incremental():
    g = Graph(
        nodes=[
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 2),
            Node(1, OP_INT_CONST, (), DEFAULT_POLICY, 1, 3),
            Node(2, OP_INT_ADD, (0, 1), DEFAULT_POLICY, 1, 0),
            Node(3, OP_INT_MUL, (2, 1), DEFAULT_POLICY, 1, 0),
        ]
    )
    spec = [
        (0, "int_const", (), 2),
        (1, "int_const", (), 3),
        (2, "int_add", (0, 1), 0),
        (3, "int_mul", (2, 1), 0),
    ]
    ind = evaluate_int_dag(spec)
    fresh = fresh_verify(g, default_registry())
    assert fresh.accepted
    assert [fresh.outputs[i] for i in range(4)] == ind

    v = IncrementalVerifier(default_registry())
    assert v.initial_verify(g).accepted
    new_g = g.replace_nodes([Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 5)])
    report = v.revalidate(new_g, changes=[], auto_compute_changes=True, compare_fresh=True)
    assert report.accepted and report.agrees_with_fresh
    ind2 = evaluate_int_dag(
        [
            (0, "int_const", (), 5),
            (1, "int_const", (), 3),
            (2, "int_add", (0, 1), 0),
            (3, "int_mul", (2, 1), 0),
        ]
    )
    assert [report.outputs[i] for i in range(4)] == ind2
