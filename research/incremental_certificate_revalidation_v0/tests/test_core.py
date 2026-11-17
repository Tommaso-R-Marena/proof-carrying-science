from __future__ import annotations

from model.graph import Graph, Node, CycleError, WellFormedError
from model.ops import OP_INT_ADD, OP_INT_CONST, OP_INT_MUL, DEFAULT_POLICY, default_registry
from reference.fresh import fresh_verify
from verifier.incremental import IncrementalVerifier


def tiny():
    return Graph(
        nodes=[
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 2),
            Node(1, OP_INT_CONST, (), DEFAULT_POLICY, 1, 3),
            Node(2, OP_INT_ADD, (0, 1), DEFAULT_POLICY, 1, 0),
            Node(3, OP_INT_MUL, (2, 1), DEFAULT_POLICY, 1, 0),
        ]
    )


def test_well_formed_and_fresh():
    g = tiny()
    g.check_well_formed()
    r = fresh_verify(g)
    assert r.accepted
    assert r.outputs[3] == 15


def test_cycle_rejected():
    g = Graph(
        nodes=[
            Node(0, OP_INT_ADD, (1,), DEFAULT_POLICY, 1, 0),
            Node(1, OP_INT_ADD, (0,), DEFAULT_POLICY, 1, 0),
        ]
    )
    try:
        g.topo_order()
        assert False, "expected cycle"
    except CycleError:
        pass


def test_duplicate_id_rejected():
    g = Graph(
        nodes=[
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 1),
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 2),
        ]
    )
    try:
        g.check_well_formed()
        assert False
    except WellFormedError:
        pass


def test_incremental_reuse_and_agree():
    v = IncrementalVerifier(default_registry())
    assert v.initial_verify(tiny()).accepted
    report = v.apply_node_changes(
        [Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 4)]
    )
    assert report.accepted
    assert report.outputs[3] == 21  # (4+3)*3
    assert 1 in report.reused
    assert 0 in report.rechecked
    assert report.agrees_with_fresh


def test_no_change_full_reuse():
    v = IncrementalVerifier(default_registry())
    g = tiny()
    assert v.initial_verify(g).accepted
    report = v.revalidate(g.copy(), changes=[], compare_fresh=True)
    assert report.accepted
    assert set(report.reused) == {0, 1, 2, 3}
    assert report.rechecked == []
    assert report.agrees_with_fresh


def test_ops_int_rat_eq_compose():
    from fractions import Fraction
    from model.ops import OP_EQ, OP_COMPOSE, OP_INT_SUB, OP_RAT_ADD, OP_RAT_MUL

    reg = default_registry()
    assert reg.compute(OP_INT_SUB, [9, 4], 0) == 5
    assert reg.compute(OP_RAT_ADD, [Fraction(1, 2), Fraction(1, 3)], 0) == Fraction(5, 6)
    assert reg.compute(OP_RAT_MUL, [Fraction(2, 3), Fraction(3, 4)], 0) == Fraction(1, 2)
    assert reg.compute(OP_EQ, [1, 1], 0) == 1
    assert reg.compute(OP_COMPOSE, [42], 0) == 42


def test_cache_lookup_not_authority():
    from cache.store import Cache, CacheEntry, reuse_permitted
    from model.graph import Certificate, ObligationKey

    key = ObligationKey(1, OP_INT_ADD, 1, 1, 0, (("int", 2), ("int", 3)))
    cert = Certificate(("ok", OP_INT_ADD, ("int", 5)), 5)
    c = Cache()
    c.put(CacheEntry(key=key, cert=cert, prior_accepted=False))
    assert c.lookup(key) is not None
    assert not reuse_permitted(c.lookup(key), key)
    assert c.try_reuse(key) is None


def test_affected_closure():
    g = tiny()
    assert g.affected_closure([0]) == {0, 2, 3}
    assert g.affected_closure([3]) == {3}


def test_load_example_json():
    from pathlib import Path

    v = IncrementalVerifier(default_registry())
    path = Path(__file__).resolve().parents[1] / "examples" / "tiny_dag.json"
    g = v.load_json(path)
    assert v.initial_verify(g).accepted
    assert v.valid_state is not None
    assert v.valid_state.cache.authoritative_count() == 4
