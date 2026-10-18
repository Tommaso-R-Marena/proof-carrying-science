import pytest

from pcs_next_v1.adapters.half_life import check_half_life, predicted_half_life
from pcs_next_v1.core.errors import PcsNextError
from pcs_next_v1.core.statuses import AssuranceStatus
from pcs_next_v1.translation.pog import (
    ObligationNode,
    ProofObligationGraph,
    aggregate_status,
    assert_well_formed,
)


def test_half_life():
    th = predicted_half_life(10.0, 1.0)
    assert check_half_life(volume=10.0, clearance=1.0, t_half=th, rel_tol=0.01)["status"] == "COMPUTATIONALLY_TESTED"
    assert check_half_life(volume=10.0, clearance=1.0, t_half=1000.0, rel_tol=0.5)["status"] == "REFUTED"


def test_pog_well_formed_and_aggregate():
    g = ProofObligationGraph()
    g.add(ObligationNode(id="a", claim="A", depends_on=["b"]))
    g.add(ObligationNode(id="b", claim="B"))
    assert assert_well_formed(g)["ok"]
    g2 = ProofObligationGraph()
    g2.add(ObligationNode(id="a", claim="A", depends_on=["b"]))
    g2.add(ObligationNode(id="b", claim="B", depends_on=["a"]))
    with pytest.raises(PcsNextError):
        assert_well_formed(g2)
    g3 = ProofObligationGraph()
    g3.add(ObligationNode(id="x", claim="x", status=AssuranceStatus.COMPUTATIONALLY_TESTED))
    g3.add(ObligationNode(id="y", claim="y", status=AssuranceStatus.REFUTED))
    assert aggregate_status(g3) == AssuranceStatus.REFUTED
