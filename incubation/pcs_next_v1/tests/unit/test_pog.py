from pcs_next_v1.translation.pog import ProofObligationGraph, ObligationNode
from pcs_next_v1.core.statuses import AssuranceStatus

def test_invalidate_and_minimal():
    g = ProofObligationGraph()
    g.add(ObligationNode("n1", "c1", artifact_ids=["a"], status=AssuranceStatus.COMPUTATIONALLY_TESTED))
    g.add(ObligationNode("n2", "c2", depends_on=["n1"], artifact_ids=["b"], status=AssuranceStatus.COMPUTATIONALLY_TESTED))
    changed = g.invalidate_from("a")
    assert "n1" in changed and "n2" in changed
    g.nodes["n1"].status = AssuranceStatus.REFUTED
    g.nodes["n2"].status = AssuranceStatus.REFUTED
    assert g.minimal_failed() == ["n1"]
