from fractions import Fraction

import pytest

from pcs_causal.probability.rational_pmf import ConditioningError, FiniteDistribution


def test_uniform_and_marginal():
    d = FiniteDistribution.uniform({"X": (0, 1), "Y": (0, 1)})
    m = d.marginal(["X"])
    assert m.prob({"X": 0}) == Fraction(1, 2)


def test_zero_conditioning_raises():
    d = FiniteDistribution.from_mapping(
        {"X": (0, 1)},
        [({"X": 0}, Fraction(1))],
    )
    with pytest.raises(ConditioningError):
        d.condition({"X": 1})


def test_independence():
    d = FiniteDistribution.uniform({"X": (0, 1), "Y": (0, 1)})
    assert d.are_independent(["X"], ["Y"])


def test_reject_float():
    with pytest.raises(TypeError):
        FiniteDistribution.from_mapping(
            {"X": (0, 1)},
            [({"X": 0}, 0.5), ({"X": 1}, 0.5)],
        )
