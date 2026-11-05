import json
from fractions import Fraction
from pathlib import Path

from pcca.certificate.checker import (
    build_conservation_certificate,
    check_certificate,
)
from pcca.stoich.matrix import from_mass_action_contract, elemental_laws

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def test_positive_conservation_certificate():
    contract = json.loads((EXAMPLES / "mass_action" / "glucose_cleavage.json").read_text())
    net = from_mass_action_contract(contract)
    carbon = next(law for law in elemental_laws(net) if law.name == "C")
    cert = build_conservation_certificate(net, "C", carbon.weights)
    result = check_certificate(cert)
    assert result.accepted
    assert result.to_json()["pcs_authority"] is False


def test_rejects_producer_verdict_field():
    contract = json.loads((EXAMPLES / "mass_action" / "glucose_cleavage.json").read_text())
    net = from_mass_action_contract(contract)
    carbon = next(law for law in elemental_laws(net) if law.name == "C")
    cert = build_conservation_certificate(net, "C", carbon.weights)
    cert["verdict"] = "PASS"
    assert check_certificate(cert).accepted is False


def test_rejects_wrong_weights():
    contract = json.loads((EXAMPLES / "mass_action" / "glucose_cleavage.json").read_text())
    net = from_mass_action_contract(contract)
    bad = (Fraction(1), Fraction(0), Fraction(0))
    cert = build_conservation_certificate(net, "bogus", bad)
    assert check_certificate(cert).accepted is False


def test_refutation_of_leak_weights():
    contract = json.loads((EXAMPLES / "adversarial" / "mass_leak.json").read_text())
    net = from_mass_action_contract(contract)
    carbon = (Fraction(6), Fraction(3), Fraction(3))
    assert net.annihilates(carbon) is False
    cert = build_conservation_certificate(
        net, "C", carbon, kind="conservation_refutation"
    )
    result = check_certificate(cert)
    assert result.accepted


def test_refutation_rejects_true_law():
    contract = json.loads((EXAMPLES / "mass_action" / "glucose_cleavage.json").read_text())
    net = from_mass_action_contract(contract)
    carbon = next(law for law in elemental_laws(net) if law.name == "C")
    cert = build_conservation_certificate(
        net, "C", carbon.weights, kind="conservation_refutation"
    )
    assert check_certificate(cert).accepted is False
