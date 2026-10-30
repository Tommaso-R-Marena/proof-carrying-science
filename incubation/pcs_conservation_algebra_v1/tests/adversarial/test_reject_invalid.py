from fractions import Fraction

from pcca.certificate.checker import build_conservation_certificate as build_cert
from pcca.certificate.checker import check_certificate
from pcca.formula import parse_formula
from pcca.stoich.matrix import StoichiometricNetwork


def _net():
    return StoichiometricNetwork(
        species=("a", "b"),
        reactions=("r",),
        matrix=((Fraction(-1),), (Fraction(1),)),
        formulas=("X", "X"),
    )


def test_reject_bad_format():
    assert check_certificate({"format": "nope", "kind": "conservation_law"}).accepted is False


def test_reject_executable_field():
    cert = {
        "format": "pcca-cert-v1",
        "kind": "conservation_law",
        "lean_source": "theorem sorry",
        "claim": {},
    }
    assert check_certificate(cert).accepted is False


def test_reject_boolean_rational():
    net = _net()
    cert = build_cert(net, "X", (Fraction(1), Fraction(1)))
    cert["claim"]["weights"] = {"a": True, "b": True}
    assert check_certificate(cert).accepted is False


def test_reject_unicode_formula():
    try:
        parse_formula("C₆H₁₂O₆")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_reject_non_stoichiometric_trajectory_step():
    net = _net()
    weights = (Fraction(1), Fraction(1))
    states = [(Fraction(1), Fraction(0)), (Fraction(0), Fraction(2))]  # not a unit fire
    xis = [(Fraction(1),)]
    cert = build_cert(
        net,
        "X",
        weights,
        kind="trajectory_conservation",
        states=states,
        xis=xis,
        expected_pool=Fraction(1),
    )
    assert check_certificate(cert).accepted is False
