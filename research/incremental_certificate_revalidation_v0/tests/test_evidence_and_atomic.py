"""Evidence binding and transactional ValidState commit tests."""
from __future__ import annotations

from model.graph import Graph, Node, compute_changes, same_defn
from model.ops import DEFAULT_POLICY, OP_INT_ADD, OP_INT_CONST, OP_INT_MUL, default_registry
from reference.fresh import fresh_verify
from verifier.incremental import IncrementalVerifier


def _base() -> Graph:
    return Graph(
        nodes=[
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 2),
            Node(1, OP_INT_CONST, (), DEFAULT_POLICY, 1, 3),
            Node(2, OP_INT_ADD, (0, 1), DEFAULT_POLICY, 1, 0),
            Node(3, OP_INT_MUL, (2, 1), DEFAULT_POLICY, 1, 0),
        ]
    )


def test_evidence_change_breaks_local_check_and_eligibility():
    reg = default_registry()
    # Same numerical payload claiming output 2, but evidence id 9 ≠ 2.
    ok_right = reg.local_check_node(
        OP_INT_CONST, 1, DEFAULT_POLICY, 2, [], ("ok", OP_INT_CONST, ("int", 2)), 2
    )
    ok_wrong_ev = reg.local_check_node(
        OP_INT_CONST, 1, DEFAULT_POLICY, 9, [], ("ok", OP_INT_CONST, ("int", 2)), 2
    )
    assert ok_right
    assert not ok_wrong_ev  # evidence-bound: const value comes from evidence id


def test_evidence_change_is_definitional_and_computed():
    g = _base()
    new_g = g.replace_nodes([Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 9)])
    assert not same_defn(g.by_id()[0], new_g.by_id()[0])
    assert compute_changes(g, new_g) == [0]
    v = IncrementalVerifier(default_registry())
    assert v.initial_verify(g).accepted
    report = v.revalidate(new_g, changes=[], auto_compute_changes=True, compare_fresh=True)
    assert report.accepted and report.agrees_with_fresh
    assert report.outputs[0] == 9
    assert 0 in report.changes


def test_atomic_commit_preserves_prior_on_fresh_disagreement(monkeypatch):
    v = IncrementalVerifier(default_registry())
    g = _base()
    assert v.initial_verify(g).accepted
    prior_outputs = dict(v.valid_state.outputs)
    prior_ids = id(v.valid_state)

    # Force a fake fresh disagreement after a would-be successful incremental pass.
    import reference.fresh as fresh_mod

    real_fresh = fresh_mod.fresh_verify

    def lying_fresh(graph, registry, provided_certs=None):
        r = real_fresh(graph, registry, provided_certs=provided_certs)
        # Flip an output to force disagreement while keeping accepted True.
        if r.accepted and r.outputs:
            k = next(iter(r.outputs))
            r.outputs[k] = 999999
        return r

    monkeypatch.setattr(fresh_mod, "fresh_verify", lying_fresh)
    # Also patch the name imported into the verifier module.
    import verifier.incremental as incr_mod

    monkeypatch.setattr(incr_mod, "fresh_verify", lying_fresh)

    new_g = g.copy()
    report = v.revalidate(new_g, changes=[], compare_fresh=True)
    assert not report.accepted
    assert report.agrees_with_fresh is False
    assert id(v.valid_state) == prior_ids
    assert v.valid_state.outputs == prior_outputs


def test_auto_compute_changes_matches_lean_seeds():
    g = Graph(
        nodes=[
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 2),
            Node(1, OP_INT_CONST, (), DEFAULT_POLICY, 1, 3),
            Node(2, OP_INT_ADD, (0, 1), DEFAULT_POLICY, 1, 0),
            Node(3, OP_INT_MUL, (1, 1), DEFAULT_POLICY, 1, 0),
        ]
    )
    new_g = g.replace_nodes(
        [
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 5),
            Node(3, OP_INT_MUL, (2, 0), DEFAULT_POLICY, 1, 0),
        ]
    )
    assert compute_changes(g, new_g) == [0, 3]
    v = IncrementalVerifier(default_registry())
    assert v.initial_verify(g).accepted
    report = v.revalidate(new_g, changes=[], auto_compute_changes=True, compare_fresh=True)
    assert report.accepted and report.agrees_with_fresh
    assert report.outputs[3] == 40
