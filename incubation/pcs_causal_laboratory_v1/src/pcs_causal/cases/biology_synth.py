"""Synthetic drug-response causal case (computational demonstration only).

Does NOT make clinical recommendations or claim biological pathway discovery.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import product
from typing import Any, Dict

from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.identification.backdoor import verify_backdoor_set
from pcs_causal.probability.rational_pmf import FiniteDistribution
from pcs_causal.scm.finite_scm import FiniteSCM


def drug_response_confounding_case() -> Dict[str, Any]:
    """Confounding by indication: Severity → Drug, Severity → Outcome, Drug → Outcome."""
    dag = CausalDAG.from_edges(
        ["Severity", "Drug", "Outcome"],
        [("Severity", "Drug"), ("Severity", "Outcome"), ("Drug", "Outcome")],
    )
    # Binary encoding
    exo_domains = {
        "US": (0, 1),
        "ED0": (0, 1),
        "ED1": (0, 1),
        "EO00": (0, 1),
        "EO01": (0, 1),
        "EO10": (0, 1),
        "EO11": (0, 1),
    }
    factors = {
        "US": {0: Fraction(3, 5), 1: Fraction(2, 5)},
        # sicker patients more likely treated
        "ED0": {0: Fraction(4, 5), 1: Fraction(1, 5)},
        "ED1": {0: Fraction(1, 5), 1: Fraction(4, 5)},
        # drug helps, severity harms
        "EO00": {0: Fraction(3, 10), 1: Fraction(7, 10)},  # P(out=1|d=0,s=0)
        "EO01": {0: Fraction(7, 10), 1: Fraction(3, 10)},
        "EO10": {0: Fraction(2, 10), 1: Fraction(8, 10)},
        "EO11": {0: Fraction(5, 10), 1: Fraction(5, 10)},
    }
    names = sorted(exo_domains)
    mass = {}
    for vals in product(*[exo_domains[k] for k in names]):
        a = dict(zip(names, vals))
        p = Fraction(1)
        for k, v in a.items():
            p *= factors[k][v]
        mass[tuple(sorted(a.items()))] = p
    exo = FiniteDistribution(variables=tuple(names), domains=exo_domains, mass=mass)

    def mech_s(a):
        return a["US"]

    def mech_d(a):
        return a["ED1"] if a["Severity"] == 1 else a["ED0"]

    def mech_o(a):
        return a[f"EO{a['Drug']}{a['Severity']}"]

    scm = FiniteSCM(
        endogenous=("Severity", "Drug", "Outcome"),
        exogenous=tuple(names),
        domains={
            **{v: (0, 1) for v in ["Severity", "Drug", "Outcome"]},
            **exo_domains,
        },
        dag=dag,
        mechanisms={"Severity": mech_s, "Drug": mech_d, "Outcome": mech_o},
        exogenous_dist=exo,
        noise_of={"Severity": "US", "Drug": "ED0", "Outcome": "EO00"},
    )

    obs = scm.observational_distribution()
    # Naive association: E[Outcome|Drug=1] - E[Outcome|Drug=0]
    from pcs_causal.probability.rational_pmf import ConditioningError

    def e_out(drug_val):
        c = obs.condition({"Drug": drug_val})
        return c.expectation(lambda a: Fraction(a["Outcome"]))

    naive = e_out(1) - e_out(0)
    true_ate = scm.ate("Drug", "Outcome", 1, 0)
    backdoor = verify_backdoor_set(dag, "Drug", "Outcome", ["Severity"])
    empty = verify_backdoor_set(dag, "Drug", "Outcome", [])

    return {
        "title": "Synthetic confounding-by-indication (drug response)",
        "disclaimer": (
            "Synthetic computational model only. Not clinical advice. "
            "Not a claim about any real drug, pathway, or patient population."
        ),
        "graph": dag.to_dict(),
        "naive_observational_contrast": [naive.numerator, naive.denominator],
        "true_ate": [true_ate.numerator, true_ate.denominator],
        "naive_equals_ate": naive == true_ate,
        "empty_adjustment_valid": empty.valid,
        "severity_adjustment_valid": backdoor.valid,
        "identification_formula": backdoor.formula,
        "scientific_status_notes": [
            "Observational association is misleading under confounding by indication.",
            "Backdoor adjustment by Severity identifies ATE under declared assumptions.",
            "Assumptions are not empirically validated by this demonstration.",
        ],
    }
