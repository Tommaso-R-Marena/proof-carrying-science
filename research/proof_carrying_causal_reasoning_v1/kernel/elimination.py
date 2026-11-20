"""Exact sum-product variable elimination for modular interventions on binary DAGs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from math import prod

from .scm import BinarySCM


@dataclass(frozen=True)
class EliminationResult:
    probability: Fraction
    ancestral_nodes: int
    peak_bucket_variables: int
    assignments_scanned: int
    elimination_order: tuple[str, ...]


@dataclass(frozen=True)
class _Factor:
    variables: tuple[str, ...]
    weights: dict[tuple[int, ...], Fraction]


def _check_limit(arity, maximum):
    if arity > maximum:
        raise ValueError("factor exceeds the declared binary variable budget")


def _sum_out(bucket, variable, maximum):
    scope = tuple(
        sorted({n for factor in bucket for n in factor.variables} - {variable})
    )
    _check_limit(len(scope) + 1, maximum)
    ordered = (*scope, variable)
    projections = [tuple(ordered.index(n) for n in f.variables) for f in bucket]
    weights = {}
    for bits in product((0, 1), repeat=len(scope)):
        total = Fraction(0)
        for value in (0, 1):
            full = (*bits, value)
            mass = Fraction(1)
            for f, coords in zip(bucket, projections, strict=True):
                mass *= f.weights.get(tuple(full[i] for i in coords), 0)
                if mass == 0:
                    break
            total += mass
        if total:
            weights[bits] = total
    return _Factor(scope, weights)


def exact_mass(
    scm: BinarySCM,
    evidence: Mapping[str, int],
    do: Mapping[str, int] | None = None,
    *,
    max_bucket_variables: int = 18,
) -> EliminationResult:
    """Compute P(evidence | do) from exact, pure CPTs. Max scope includes the eliminated bit."""
    if type(max_bucket_variables) is not int or not 1 <= max_bucket_variables <= 24:
        raise ValueError("binary variable budget must be an integer between 1 and 24")
    do = {} if do is None else do
    for mapping in (evidence, do):
        if not set(mapping) <= scm.graph.nodes or any(
            type(v) is not int or v not in (0, 1) for v in mapping.values()
        ):
            raise ValueError("unknown variable or invalid binary assignment")
    # Reverse reachability stops at fixed mechanisms. Every other normalized
    # mechanism outside this closure integrates to 1 in reverse topological order.
    needed = set(evidence)
    order = scm.graph.topological_order()
    for n in reversed(order):
        if n in needed and n not in do:
            needed.update(scm.graph.parents(n))
    fixed = {**do, **evidence}
    factors = []
    peak = scanned = 0
    for n in order:
        parents = tuple(sorted(scm.graph.parents(n)))
        _check_limit(len(parents), max_bucket_variables)
        scope = (*parents, n)
        free = tuple(v for v in scope if v not in fixed)
        retain = n in needed and n not in do
        if retain:
            _check_limit(len(free), max_bucket_variables)
            peak = max(peak, len(free))
        weights = {}
        # Validate even discarded and impossible CPT rows as the exact model
        # class requires a properly normalized mechanism at every assignment.
        for bits in product((0, 1), repeat=len(parents)):
            env = dict(zip(parents, bits, strict=True))
            rate = scm.mechanisms[n](env)
            if type(rate) not in (int, Fraction) or not 0 <= rate <= 1:
                raise ValueError("expected rational binary mechanism probability")
            if not retain or any(p in fixed and fixed[p] != v for p, v in env.items()):
                continue
            for bit in (fixed[n],) if n in fixed else (0, 1):
                mass = rate if bit else 1 - rate
                if mass:
                    env[n] = bit
                    weights[tuple(env[v] for v in free)] = Fraction(mass)
        if retain:
            factors.append(_Factor(free, weights))
    if any(n in do and do[n] != bit for n, bit in evidence.items()):
        return EliminationResult(Fraction(0), len(needed), peak, 0, ())
    eliminated = []
    remaining = needed - set(fixed)
    while remaining:
        # Min-neighbors ordering. The factor scopes are the current cliques.
        neighbors = {n: set() for n in remaining}
        for f in factors:
            for n in f.variables:
                neighbors[n].update(f.variables)
        chosen = min(neighbors, key=lambda n: (len(neighbors[n]), n))
        arity = len(neighbors[chosen])
        bucket = [f for f in factors if chosen in f.variables]
        reduced = _sum_out(bucket, chosen, max_bucket_variables)
        factors = [f for f in factors if chosen not in f.variables] + [reduced]
        eliminated.append(chosen)
        remaining.remove(chosen)
        scanned += 2**arity
        peak = max(peak, arity)
    mass = prod((f.weights.get((), 0) for f in factors), start=Fraction(1))
    return EliminationResult(mass, len(needed), peak, scanned, tuple(eliminated))
