"""Negative tests: removing essential IncrementalAccept premises breaks guarantees."""
from __future__ import annotations

from cache.store import CacheEntry
from model.graph import (
    Certificate,
    Graph,
    Node,
    changes_complete,
    missing_definitional_changes,
    obligation_of,
)
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


def test_incomplete_changes_detected_and_blocks_accept():
    v = IncrementalVerifier(default_registry())
    assert v.initial_verify(_base()).accepted
    new_g = v.graph.replace_nodes([Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 9)])
    assert missing_definitional_changes(v.valid_state.graph, new_g, []) == [0]
    assert not changes_complete(v.valid_state.graph, new_g, [])
    report = v.revalidate(new_g, changes=[], require_changes_complete=True)
    assert not report.accepted
    assert "ChangesComplete" in (report.error or "")


def test_forged_authority_plus_incomplete_changes_false_accept():
    """Without ChangesComplete and without reuse recheck, forged new-key authority
    yields a stale accepted graph that disagrees with fresh verification."""
    v = IncrementalVerifier(default_registry())
    g = _base()
    assert v.initial_verify(g).accepted
    new_g = g.replace_nodes([Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 9)])
    # Plant authoritative forged entry for the *new* obligation key of node 0,
    # claiming the old output 2.
    forged_key = obligation_of(
        Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 9), []
    )
    v.cache.put(
        CacheEntry(
            key=forged_key,
            cert=Certificate(payload=("ok", OP_INT_CONST, ("int", 2)), output=2),
            prior_accepted=True,
        )
    )
    report = v.revalidate(
        new_g,
        changes=[],
        require_changes_complete=False,
        recheck_on_reuse=False,
        compare_fresh=False,
    )
    fresh = fresh_verify(new_g, default_registry())
    assert fresh.outputs[3] == 36
    assert report.accepted
    assert report.outputs.get(0) == 2  # forged stale
    assert report.outputs.get(3) == 15  # cascading stale reuse
    assert report.outputs != fresh.outputs


def test_prior_affected_misses_new_edge_completeness():
    """Prior-graph Affected is not complete for new dependency edges (set-level)."""
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
    changes = [0]
    prior_aff = g.affected_closure(changes)
    new_aff = new_g.affected_closure(changes)
    # New edge 0→3 makes 3 Affected on the updated graph only.
    assert 3 not in prior_aff
    assert 3 in new_aff
    assert prior_aff < new_aff  # proper incompleteness of prior-only invalidation


def test_prior_invalidation_plus_forgery_false_accept():
    """Prior-graph invalidation + incomplete changes + forged new-key authority
    accepts a stale assignment that fresh verification rejects as unequal."""
    g = Graph(
        nodes=[
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 2),
            Node(1, OP_INT_CONST, (), DEFAULT_POLICY, 1, 3),
            Node(2, OP_INT_ADD, (0, 1), DEFAULT_POLICY, 1, 0),
            Node(3, OP_INT_MUL, (1, 1), DEFAULT_POLICY, 1, 0),
        ]
    )
    v = IncrementalVerifier(default_registry())
    assert v.initial_verify(g).accepted
    new_g = g.replace_nodes(
        [
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 5),
            Node(3, OP_INT_MUL, (2, 0), DEFAULT_POLICY, 1, 0),
        ]
    )
    # Under prior Affected({0}) = {0,2}; node 3 is wrongly treated as unaffected.
    # Plant forged authority for the *new* obligation of node 3 claiming old output 9.
    # After rechecking 0→5 and 2→add(5,3)=8, forged reuse of 3 yields 9 instead of 40.
    forged_key = obligation_of(
        Node(3, OP_INT_MUL, (2, 0), DEFAULT_POLICY, 1, 0), [8, 5]
    )
    v.cache.put(
        CacheEntry(
            key=forged_key,
            cert=Certificate(payload=("ok", OP_INT_MUL, ("int", 9)), output=9),
            prior_accepted=True,
        )
    )
    report = v.revalidate(
        new_g,
        changes=[0],  # incomplete: omits definitional edit of node 3
        require_changes_complete=False,
        invalidation_graph="prior",
        recheck_on_reuse=False,
        compare_fresh=False,
    )
    fresh = fresh_verify(new_g, default_registry())
    assert report.accepted
    assert 3 in report.unaffected
    assert 3 in report.reused
    assert report.outputs[3] == 9
    assert fresh.outputs[3] == 40
    assert report.outputs != fresh.outputs


def test_sound_path_new_graph_and_complete_changes():
    g = Graph(
        nodes=[
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 2),
            Node(1, OP_INT_CONST, (), DEFAULT_POLICY, 1, 3),
            Node(2, OP_INT_ADD, (0, 1), DEFAULT_POLICY, 1, 0),
            Node(3, OP_INT_MUL, (1, 1), DEFAULT_POLICY, 1, 0),
        ]
    )
    v = IncrementalVerifier(default_registry())
    assert v.initial_verify(g).accepted
    new_g = g.replace_nodes(
        [
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 5),
            Node(3, OP_INT_MUL, (2, 0), DEFAULT_POLICY, 1, 0),
        ]
    )
    report = v.revalidate(new_g, changes=[0, 3], compare_fresh=True)
    assert report.accepted and report.agrees_with_fresh
    assert report.outputs[3] == 40


def test_no_authority_blocks_reuse():
    v = IncrementalVerifier(default_registry())
    g = _base()
    assert v.initial_verify(g).accepted
    for e in list(v.cache.entries):
        v.cache.put(CacheEntry(key=e.key, cert=e.cert, prior_accepted=False))
    report = v.revalidate(g.copy(), changes=[], recheck_on_reuse=False, compare_fresh=True)
    assert report.accepted
    assert report.reused == []
    assert report.agrees_with_fresh
