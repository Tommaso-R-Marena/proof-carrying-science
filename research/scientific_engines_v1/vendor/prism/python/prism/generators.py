"""Deterministic (seeded) instance generators used by tests and benchmarks."""
from __future__ import annotations

import random
from fractions import Fraction
from itertools import product

from .core import Problem


def random_problem(seed: int, n: int, k: int, r: int, qmax: int = 4, costs=(1, 2, 3),
                   allow_zero_cost: bool = True, oracle_cost=None) -> Problem:
    """Random instance.  If `oracle_cost` is given, an extra experiment revealing the
    model identity (cost `oracle_cost`) guarantees a finite optimal value."""
    rng = random.Random(seed)
    obs = [[rng.randrange(r) for _ in range(k)] for _ in range(n)]
    q = [Fraction(rng.randrange(qmax + 1), rng.choice([1, 2])) for _ in range(n)]
    cs = list(costs) + ([0] if allow_zero_cost else [])
    cost = [Fraction(rng.choice(cs)) for _ in range(k)]
    exps = [f"e{j}" for j in range(k)]
    outs = [[f"o{t}" for t in range(r)] for _ in range(k)]
    if oracle_cost is not None:
        for i in range(n):
            obs[i].append(i)
        cost.append(Fraction(oracle_cost))
        exps.append("oracle")
        outs.append([f"id{i}" for i in range(n)])
    return Problem([f"m{i}" for i in range(n)], exps, outs, obs, q, cost)


def or_family(n: int) -> Problem:
    """2^n regulator-activity vectors; query = whether any regulator is active;
    experiment j assays regulator j (cost 1)."""
    models, obs, q = [], [], []
    for bitsv in product([0, 1], repeat=n):
        models.append("".join(map(str, bitsv)))
        obs.append(list(bitsv))
        q.append(Fraction(1 if any(bitsv) else 0))
    return Problem(models, [f"assay{j}" for j in range(n)], [["off", "on"]] * n, obs, q,
                   [Fraction(1)] * n)


def lesion_family(n: int, k: int) -> Problem:
    """Pathway-lesion localization with nuisance switches.

    Model (d, z): the lesion is at step d ∈ {0..n-1} of an n-step linear pathway;
    z ∈ {0,1}^k are k independent nuisance switches (e.g. isoform / compensatory
    branch states) that do not influence the query.
    Experiments:
      probe_t (t = 1..n-1): is the pathway intermediate after step t produced?
                            outcome = [d >= t]  (cost 1)
      switch_i (i < k):     reads nuisance switch z_i (cost 1)
    Query q(d, z) = d (which step is broken).  Tolerance 0 = identify the lesion.
    |M| = n 2^k.  A naive DP explores the product of interval states and
    nuisance sub-cubes; the core-guided sandwich discovers that nuisance probes
    are irrelevant from a core of n models."""
    models, obs, q = [], [], []
    for d in range(n):
        for z in product([0, 1], repeat=k):
            models.append(f"d{d}z{''.join(map(str, z))}")
            obs.append([1 if d >= t else 0 for t in range(1, n)] + list(z))
            q.append(Fraction(d))
    exps = [f"probe{t}" for t in range(1, n)] + [f"switch{i}" for i in range(k)]
    return Problem(models, exps, [["no", "yes"]] * (n - 1 + k), obs, q, [Fraction(1)] * (n - 1 + k))


def pointer_family(n: int) -> Problem:
    """Adaptivity-gap family: model (a, b), pointer a ∈ {0..n-1}, bits b ∈ {0,1}^n;
    query b[a].  Experiments: read the pointer (n outcomes) or read bit i."""
    models, obs, q = [], [], []
    for a in range(n):
        for b in product([0, 1], repeat=n):
            models.append(f"a{a}b{''.join(map(str, b))}")
            obs.append([a] + list(b))
            q.append(Fraction(b[a]))
    outs = [[f"p{i}" for i in range(n)]] + [["0", "1"]] * n
    return Problem(models, ["pointer"] + [f"bit{i}" for i in range(n)], outs, obs, q,
                   [Fraction(1)] * (n + 1))
