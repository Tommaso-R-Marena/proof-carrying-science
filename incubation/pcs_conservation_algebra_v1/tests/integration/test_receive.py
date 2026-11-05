import json
from pathlib import Path

from pcca.receiver.replay import receive_contract, receive_path

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def test_receive_glucose_positive(tmp_path):
    path = EXAMPLES / "mass_action" / "glucose_cleavage.json"
    report = receive_path(path, tmp_path)
    assert report.accepted
    assert set(law["name"] for law in report.laws) >= {"C", "H", "O"}
    assert report.trajectory_pools["C"] == "6"
    assert report.pcs_authority is False
    assert (tmp_path / "receive-report.json").exists()
    assert any(tmp_path.glob("conservation_law-C.json"))
    assert any(tmp_path.glob("trajectory_conservation-C.json"))


def test_receive_mass_leak_rejected():
    contract = json.loads((EXAMPLES / "adversarial" / "mass_leak.json").read_text())
    report = receive_contract(contract)
    assert report.accepted is False
    assert any("elemental" in r for r in report.reasons)


def test_receive_transport_reduction():
    contract = json.loads(
        (EXAMPLES / "transport_reduction" / "two_cell_exchange.json").read_text()
    )
    report = receive_contract(contract)
    assert report.accepted
    assert any(law["name"] == "X" for law in report.laws)
    # 3/2 + 1/4 = 7/4
    assert report.trajectory_pools["X"] in {"7/4", "1.75"}
