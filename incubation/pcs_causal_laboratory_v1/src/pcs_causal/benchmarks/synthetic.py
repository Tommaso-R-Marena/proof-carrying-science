"""Synthetic SCM generators with exact interventional ground truth."""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, Tuple

from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.probability.rational_pmf import FiniteDistribution
from pcs_causal.scm.finite_scm import FiniteSCM


def generate_chain_scm() -> Tuple[FiniteSCM, dict]:
    """X → Y → Z with known ATE of X on Z."""
    dag = CausalDAG.from_edges(["X", "Y", "Z"], [("X", "Y"), ("Y", "Z")])
    exo_domains = {"UX": (0, 1), "UY": (0, 1), "UZ": (0, 1)}
    # Independent Bern(1/2)
    mass = {}
    from itertools import product

    names = sorted(exo_domains)
    for vals in product(*[exo_domains[k] for k in names]):
        a = dict(zip(names, vals))
        mass[tuple(sorted(a.items()))] = Fraction(1, 8)
    exo = FiniteDistribution(variables=tuple(names), domains=exo_domains, mass=mass)

    def mech_x(a):
        return a["UX"]

    def mech_y(a):
        return a["X"] ^ a["UY"]  # xor

    def mech_z(a):
        return a["Y"] if a["UZ"] == 0 else 1 - a["Y"]

    scm = FiniteSCM(
        endogenous=("X", "Y", "Z"),
        exogenous=tuple(names),
        domains={**{v: (0, 1) for v in ["X", "Y", "Z"]}, **exo_domains},
        dag=dag,
        mechanisms={"X": mech_x, "Y": mech_y, "Z": mech_z},
        exogenous_dist=exo,
        noise_of={"X": "UX", "Y": "UY", "Z": "UZ"},
    )
    ate = scm.ate("X", "Z", 1, 0)
    meta = {
        "name": "chain_X_Y_Z",
        "true_ate_X_on_Z": [ate.numerator, ate.denominator],
        "notes": "Synthetic ground truth; not a biological discovery.",
    }
    return scm, meta


def generate_backdoor_scm() -> Tuple[FiniteSCM, dict]:
    """Z → X, Z → Y, X → Y — classic confounding with valid backdoor {Z}."""
    dag = CausalDAG.from_edges(
        ["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")]
    )
    exo_domains = {
        "UZ": (0, 1),
        "EX0": (0, 1),
        "EX1": (0, 1),
        "EY00": (0, 1),
        "EY01": (0, 1),
        "EY10": (0, 1),
        "EY11": (0, 1),
    }
    factors = {
        "UZ": {0: Fraction(1, 2), 1: Fraction(1, 2)},
        "EX0": {0: Fraction(3, 4), 1: Fraction(1, 4)},  # P(X=1|Z=0)=1/4
        "EX1": {0: Fraction(1, 4), 1: Fraction(3, 4)},  # P(X=1|Z=1)=3/4
        "EY00": {0: Fraction(4, 5), 1: Fraction(1, 5)},
        "EY01": {0: Fraction(2, 5), 1: Fraction(3, 5)},
        "EY10": {0: Fraction(3, 5), 1: Fraction(2, 5)},
        "EY11": {0: Fraction(1, 5), 1: Fraction(4, 5)},
    }
    from itertools import product

    names = sorted(exo_domains)
    mass = {}
    for vals in product(*[exo_domains[k] for k in names]):
        a = dict(zip(names, vals))
        p = Fraction(1)
        for k, v in a.items():
            p *= factors[k][v]
        mass[tuple(sorted(a.items()))] = p
    exo = FiniteDistribution(variables=tuple(names), domains=exo_domains, mass=mass)

    def mech_z(a):
        return a["UZ"]

    def mech_x(a):
        return a["EX1"] if a["Z"] == 1 else a["EX0"]

    def mech_y(a):
        return a[f"EY{a['X']}{a['Z']}"]

    scm = FiniteSCM(
        endogenous=("Z", "X", "Y"),
        exogenous=tuple(names),
        domains={**{v: (0, 1) for v in ["Z", "X", "Y"]}, **exo_domains},
        dag=dag,
        mechanisms={"Z": mech_z, "X": mech_x, "Y": mech_y},
        exogenous_dist=exo,
        noise_of={"Z": "UZ", "X": "EX0", "Y": "EY00"},
    )
    true_ate = scm.ate("X", "Y", 1, 0)
    meta = {
        "name": "backdoor_confounding",
        "valid_adjustment": ["Z"],
        "invalid_adjustment_empty": True,
        "true_ate": [true_ate.numerator, true_ate.denominator],
        "notes": "Synthetic; confounding makes naive association ≠ ATE.",
    }
    return scm, meta
