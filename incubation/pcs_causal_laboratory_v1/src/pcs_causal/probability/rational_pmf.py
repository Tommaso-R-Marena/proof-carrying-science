"""Exact finite probability mass functions over named discrete variables.

All probabilities are Python fractions.Rational (fractions.Fraction).
Zero-probability conditioning raises ConditioningError; values are never invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

Rational = Fraction

Assignment = Tuple[Tuple[str, object], ...]  # canonical sorted tuple


class ConditioningError(ValueError):
    """Raised when conditioning on a zero-probability event."""


def _canon(assignment: Mapping[str, object]) -> Assignment:
    return tuple(sorted((str(k), v) for k, v in assignment.items()))


def _as_frac(x: object) -> Rational:
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x, 1)
    if isinstance(x, float):
        raise TypeError(
            "float probabilities are rejected for exact mathematical ground truth; "
            "use fractions.Fraction"
        )
    return Fraction(x)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class FiniteDistribution:
    """Joint PMF over a finite set of discrete variables.

    Parameters
    ----------
    variables:
        Ordered variable names (canonical order is sorted for hashing).
    domains:
        Map variable → finite tuple of admissible values.
    mass:
        Map canonical assignment → non-negative rational probability.
        Missing assignments are treated as probability 0.
    """

    variables: Tuple[str, ...]
    domains: Mapping[str, Tuple[object, ...]]
    mass: Mapping[Assignment, Rational]

    def __post_init__(self) -> None:
        vs = tuple(sorted(self.variables))
        if vs != tuple(self.variables):
            object.__setattr__(self, "variables", vs)
        if set(self.domains) != set(self.variables):
            raise ValueError("domains must match variables exactly")
        total = Fraction(0)
        for a, p in self.mass.items():
            if p < 0:
                raise ValueError(f"negative probability for {a}: {p}")
            keys = {k for k, _ in a}
            if keys != set(self.variables):
                raise ValueError(f"assignment keys mismatch: {a}")
            for k, v in a:
                if v not in self.domains[k]:
                    raise ValueError(f"value {v!r} not in domain of {k}")
            total += p
        if total != 1:
            raise ValueError(f"probabilities must sum to 1; got {total}")

    @classmethod
    def from_mapping(
        cls,
        domains: Mapping[str, Sequence[object]],
        probs: Mapping[Assignment, object]
        | Mapping[tuple, object]
        | Sequence[tuple[Mapping[str, object], object]],
    ) -> "FiniteDistribution":
        """Build from domains and a probability table.

        ``probs`` may be:
        - a sequence of ``(assignment_dict, probability)`` pairs (preferred),
        - a mapping from canonical assignment tuples to probabilities.
        """
        dom = {k: tuple(v) for k, v in domains.items()}
        mass: Dict[Assignment, Rational] = {}
        if isinstance(probs, (list, tuple)):
            items = list(probs)
            for a, p in items:
                mass[_canon(a)] = _as_frac(p)
        else:
            for a, p in probs.items():  # type: ignore[union-attr]
                if isinstance(a, tuple) and a and isinstance(a[0], tuple):
                    mass[a] = _as_frac(p)  # type: ignore[index]
                elif isinstance(a, tuple):
                    mass[_canon(dict(a))] = _as_frac(p)
                else:
                    mass[_canon(a)] = _as_frac(p)  # type: ignore[arg-type]
        return cls(variables=tuple(sorted(dom)), domains=dom, mass=mass)

    @classmethod
    def uniform(cls, domains: Mapping[str, Sequence[object]]) -> "FiniteDistribution":
        dom = {k: tuple(v) for k, v in domains.items()}
        keys = sorted(dom)
        assignments = list(product(*[dom[k] for k in keys]))
        n = len(assignments)
        if n == 0:
            raise ValueError("empty domain product")
        p = Fraction(1, n)
        mass = {tuple(zip(keys, vals)): p for vals in assignments}
        return cls(variables=tuple(keys), domains=dom, mass=mass)

    def prob(self, assignment: Mapping[str, object]) -> Rational:
        return self.mass.get(_canon(assignment), Fraction(0))

    def event_prob(self, predicate) -> Rational:
        return sum((p for a, p in self.mass.items() if predicate(dict(a))), Fraction(0))

    def marginal(self, keep: Iterable[str]) -> "FiniteDistribution":
        keep_set = set(keep)
        if not keep_set <= set(self.variables):
            raise ValueError("marginalize to unknown variables")
        if keep_set == set(self.variables):
            return self
        domains = {k: self.domains[k] for k in keep_set}
        acc: Dict[Assignment, Rational] = {}
        for a, p in self.mass.items():
            sub = _canon({k: v for k, v in a if k in keep_set})
            acc[sub] = acc.get(sub, Fraction(0)) + p
        return FiniteDistribution(
            variables=tuple(sorted(keep_set)),
            domains=domains,
            mass=acc,
        )

    def condition(self, evidence: Mapping[str, object]) -> "FiniteDistribution":
        """Condition on evidence. Raises ConditioningError if P(evidence)=0."""
        ev = dict(evidence)
        if not set(ev) <= set(self.variables):
            raise ValueError("conditioning on unknown variables")
        # Check values in domain
        for k, v in ev.items():
            if v not in self.domains[k]:
                raise ValueError(f"evidence value {v!r} outside domain of {k}")

        filtered: Dict[Assignment, Rational] = {}
        z = Fraction(0)
        for a, p in self.mass.items():
            d = dict(a)
            if all(d[k] == v for k, v in ev.items()):
                filtered[a] = p
                z += p
        if z == 0:
            raise ConditioningError(f"zero-probability conditioning on {ev}")
        # Drop conditioned variables from the conditional distribution
        remain = [k for k in self.variables if k not in ev]
        if not remain:
            # Degenerate: only the empty assignment with mass 1
            return FiniteDistribution(
                variables=(),
                domains={},
                mass={(): Fraction(1)},
            )
        acc: Dict[Assignment, Rational] = {}
        for a, p in filtered.items():
            sub = _canon({k: v for k, v in a if k not in ev})
            acc[sub] = acc.get(sub, Fraction(0)) + p / z
        return FiniteDistribution(
            variables=tuple(sorted(remain)),
            domains={k: self.domains[k] for k in remain},
            mass=acc,
        )

    def conditional_prob(
        self, query: Mapping[str, object], evidence: Mapping[str, object]
    ) -> Rational:
        """P(query | evidence) for a full assignment of remaining vars, or joint query∪evidence pattern."""
        # Compute P(query ∪ evidence) / P(evidence)
        joint = dict(evidence)
        for k, v in query.items():
            if k in joint and joint[k] != v:
                return Fraction(0)
            joint[k] = v
        num = self.prob(joint) if set(joint) == set(self.variables) else self._partial_prob(joint)
        den = self._partial_prob(evidence)
        if den == 0:
            raise ConditioningError(f"zero-probability conditioning on {dict(evidence)}")
        return num / den

    def _partial_prob(self, partial: Mapping[str, object]) -> Rational:
        return sum(
            (
                p
                for a, p in self.mass.items()
                if all(dict(a).get(k) == v for k, v in partial.items())
            ),
            Fraction(0),
        )

    def expectation(self, fn) -> Rational:
        """E[fn(assignment_dict)] with rational-valued fn."""
        return sum((fn(dict(a)) * p for a, p in self.mass.items()), Fraction(0))

    def conditional_expectation(self, fn, evidence: Mapping[str, object]) -> Rational:
        return self.condition(evidence).expectation(fn)

    def are_independent(
        self, x: Iterable[str], y: Iterable[str], z: Iterable[str] = ()
    ) -> bool:
        """Exact conditional independence check on this finite distribution."""
        X, Y, Z = list(x), list(y), list(z)
        if set(X) & set(Y):
            raise ValueError("X and Y must be disjoint")
        # Compare P(X,Y|Z) vs P(X|Z)P(Y|Z) on support of Z
        z_dom_keys = Z
        if not z_dom_keys:
            # Check factorization of joint
            j_xy = self.marginal(X + Y)
            j_x = self.marginal(X)
            j_y = self.marginal(Y)
            for a, p in j_xy.mass.items():
                d = dict(a)
                px = j_x.prob({k: d[k] for k in X})
                py = j_y.prob({k: d[k] for k in Y})
                if p != px * py:
                    return False
            return True

        # Enumerate Z assignments with positive mass
        z_marg = self.marginal(Z)
        for za, pz in z_marg.mass.items():
            if pz == 0:
                continue
            ev = dict(za)
            try:
                cond = self.condition(ev)
            except ConditioningError:
                continue
            j_xy = cond.marginal(X + Y)
            j_x = cond.marginal(X)
            j_y = cond.marginal(Y)
            for a, p in j_xy.mass.items():
                d = dict(a)
                if p != j_x.prob({k: d[k] for k in X}) * j_y.prob({k: d[k] for k in Y}):
                    return False
        return True

    def total_variation(self, other: "FiniteDistribution") -> Rational:
        if set(self.variables) != set(other.variables) or dict(self.domains) != dict(
            other.domains
        ):
            raise ValueError("TV distance requires identical domains")
        keys = set(self.mass) | set(other.mass)
        s = Fraction(0)
        for k in keys:
            s += abs(self.mass.get(k, Fraction(0)) - other.mass.get(k, Fraction(0)))
        return s / 2

    def equals_exact(self, other: "FiniteDistribution") -> bool:
        return self.total_variation(other) == 0

    def to_dict(self) -> dict:
        return {
            "variables": list(self.variables),
            "domains": {k: list(v) for k, v in self.domains.items()},
            "mass": [
                {"assignment": dict(a), "p": [p.numerator, p.denominator]}
                for a, p in sorted(self.mass.items())
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "FiniteDistribution":
        domains = {k: tuple(v) for k, v in data["domains"].items()}
        mass = {
            _canon(item["assignment"]): Fraction(item["p"][0], item["p"][1])
            for item in data["mass"]
        }
        return cls(variables=tuple(sorted(domains)), domains=domains, mass=mass)
