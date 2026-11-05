from pcs_causal.identification.do_calculus import try_action_exchange
from pcs_causal.graphs.dag import CausalDAG


def test_action_exchange_module_is_executable():
    graph = CausalDAG.from_edges(["X", "Y"], [("X", "Y")])
    result = try_action_exchange(graph, "Y", "X", ())
    assert result.justified is True


def test_confounding_fork_cannot_exchange_observation_for_intervention():
    # U is fair, X=U, Y=U: P(Y=1|X=1)=1 but P(Y=1|do(X=1))=1/2.
    graph = CausalDAG.from_edges(["U", "X", "Y"], [("U", "X"), ("U", "Y")])
    assert try_action_exchange(graph, "Y", "X", ()).justified is False
