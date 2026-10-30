from pcs_causal.graphs.dag import CausalDAG, GraphError
from pcs_causal.graphs.d_separation import d_separated
import pytest


def test_acyclicity_rejected():
    with pytest.raises(GraphError):
        CausalDAG.from_edges(["A", "B"], [("A", "B"), ("B", "A")])


def test_ancestors_descendants():
    g = CausalDAG.from_edges(["A", "B", "C"], [("A", "B"), ("B", "C")])
    assert g.ancestors("C") == frozenset({"A", "B"})
    assert g.descendants("A") == frozenset({"B", "C"})


def test_mutilation_removes_incoming():
    g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("X", "Y"), ("Z", "Y")])
    m = g.mutilate(["X"])
    assert ("Z", "X") not in m.edges
    assert ("X", "Y") in m.edges


def test_d_separation_chain():
    g = CausalDAG.from_edges(["X", "M", "Y"], [("X", "M"), ("M", "Y")])
    assert d_separated(g, ["X"], ["Y"], ["M"])
    assert not d_separated(g, ["X"], ["Y"], [])


def test_d_separation_collider():
    g = CausalDAG.from_edges(["X", "C", "Y"], [("X", "C"), ("Y", "C")])
    assert d_separated(g, ["X"], ["Y"], [])
    assert not d_separated(g, ["X"], ["Y"], ["C"])


def test_topological_order():
    g = CausalDAG.from_edges(["A", "B", "C"], [("A", "C"), ("B", "C")])
    order = g.topological_order()
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("C")
