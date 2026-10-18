from pcs_causal.identification.do_calculus import try_action_exchange
from pcs_causal.graphs.dag import CausalDAG


def test_action_exchange_module_is_executable():
    graph = CausalDAG.from_edges(["X", "Y"], [("X", "Y")])
    result = try_action_exchange(graph, "Y", "X", ())
    assert isinstance(result.justified, bool)
