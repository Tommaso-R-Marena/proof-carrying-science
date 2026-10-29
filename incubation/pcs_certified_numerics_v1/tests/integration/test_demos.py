from fractions import Fraction

from certnum.ode.euler import linear_scalar_enclosure, simulate_linear_scalar
from certnum.ode.exp_enclosure import exp_enclosure
from certnum.thermo.partition import partition_function_energy_bins, partition_function_exact_enum
from certnum.linalg.basic import gershgorin_real_enclosure, residual_certificate, solve_2x2
from certnum.stochastic.markov import ProbDist, StochasticMatrix, reachability_prob


def test_exp_and_linear_ode():
    enc = exp_enclosure(Fraction(1, 2))
    assert enc.is_ok
    assert enc.interval.lo > 1
    assert enc.interval.hi < 2
    # x' = -x, x(0)=1 ⇒ x(1)=e^{-1}
    sol = linear_scalar_enclosure(Fraction(-1), Fraction(0), Fraction(1), Fraction(1))
    assert sol.is_ok
    assert sol.interval.lo > 0
    assert sol.interval.hi < 1


def test_thermo_matches_bins():
    energies = [Fraction(0), Fraction(1), Fraction(1), Fraction(2)]
    beta = Fraction(1)
    exact = partition_function_exact_enum(energies, beta)
    bins = [(1, Fraction(0), Fraction(0)), (2, Fraction(1), Fraction(1)), (1, Fraction(2), Fraction(2))]
    binned = partition_function_energy_bins(bins, beta)
    # Exact should be subset of (equal to) binned when bins are singletons
    assert exact.Z_enclosure.subset(binned.Z_enclosure) or (
        exact.Z_enclosure.lo == binned.Z_enclosure.lo
    )


def test_linalg_residual_and_gershgorin():
    A = [[Fraction(2), Fraction(1)], [Fraction(1), Fraction(2)]]
    b = [Fraction(1), Fraction(1)]
    x = solve_2x2(A, b)
    cert = residual_certificate(A, b, x)
    assert cert.residual_inf_norm == 0
    lo, hi = gershgorin_real_enclosure(A)
    assert lo <= 1 and hi >= 3


def test_markov_reachability():
    P = StochasticMatrix([[Fraction(0), Fraction(1)], [Fraction(1, 2), Fraction(1, 2)]])
    start = ProbDist([Fraction(1), Fraction(0)])
    p = reachability_prob(P, start, targets=[1], steps=1)
    assert p == 1
