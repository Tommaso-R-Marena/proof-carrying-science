"""Exact scalar-input integer ReLU-network analysis (Python reference only).

All-integer equivalence and no-forgetting are decidable because finite sums
of integer ReLUs are affine on cells cut by their activation thresholds.
Neither a Lean proof nor protected model-promotion authorization.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Term:
    coefficient: int
    weight: int
    bias: int

    def __post_init__(self):
        if any(type(v) is not int for v in (self.coefficient, self.weight, self.bias)):
            raise TypeError("noninteger coefficient or parameter")

    def cut(self) -> int | None:
        """Sign remains constant for integers <=cut and >=cut+1."""
        if self.weight > 0:
            return (-self.bias) // self.weight
        if self.weight < 0:
            # ceil(-b/w)-1 == -floor(b/w)-1
            return -(self.bias // self.weight) - 1
        return None

    def value(self, x: int) -> int:
        return self.coefficient * max(0, self.weight*x + self.bias)

@dataclass(frozen=True)
class Net:
    terms: tuple[Term, ...]
    bias: int = 0

    def __post_init__(self):
        if type(self.terms) is not tuple or type(self.bias) is not int or not all(
            isinstance(t, Term) for t in self.terms
        ):
            raise TypeError("expected exact integer ReLU term tuple")

    def predict(self, x: int) -> int:
        if type(x) is not int:
            raise TypeError("input must be exact integer")
        return self.bias + sum(t.value(x) for t in self.terms)

    def affine(self, x: int) -> tuple[int, int]:
        """Slope/intercept where every ReLU active pattern matches that at x."""
        a, b = 0, self.bias
        for t in self.terms:
            if t.weight*x+t.bias > 0:
                a += t.coefficient*t.weight
                b += t.coefficient*t.bias
        return a, b

@dataclass(frozen=True)
class Cell:
    low: int | None
    high: int | None

    def contains(self, x: int) -> bool:
        return (self.low is None or x >= self.low) and (
            self.high is None or x <= self.high)

    def point(self) -> int:
        return self.low if self.low is not None else (
            self.high if self.high is not None else 0)

    def singleton(self) -> bool:
        return self.low is not None and self.low == self.high

    def pair(self) -> tuple[int, int]:
        if self.singleton():
            raise ValueError("singleton has no distinct pair")
        if self.low is not None:
            return self.low, self.low + 1
        if self.high is not None:
            return self.high - 1, self.high
        return 0, 1

@dataclass(frozen=True)
class Decision:
    passes: bool
    property_name: str
    cells_checked: int
    cuts: tuple[int, ...]
    counterexample: int | None

def integer_cells(*nets: Net) -> tuple[tuple[int, ...], tuple[Cell, ...]]:
    cuts = tuple(sorted({c for n in nets for t in n.terms
                         if (c := t.cut()) is not None}))
    cells = []
    low = None
    for cut in cuts:
        cells.append(Cell(low, cut))
        low = cut + 1
    cells.append(Cell(low, None))
    return cuts, tuple(cells)

def _delta(a: Net, b: Net, x: int) -> tuple[int, int]:
    aa, ab = a.affine(x)
    ba, bb = b.affine(x)
    return aa-ba, ab-bb

def _zero(a: int, b: int, cell: Cell) -> bool:
    return a*cell.low+b == 0 if cell.singleton() else a == b == 0

def _counterexample(a: int, b: int, cell: Cell) -> int:
    if cell.singleton():
        x = cell.low
        if a*x+b:
            return x
    else:
        x, y = cell.pair()
        if a*x+b:
            return x
        if a*y+b:
            return y
    raise AssertionError("claimed unequal affines coincide at two distinct points")

def all_integer_equal(a: Net, b: Net) -> Decision:
    """Exact (no bounded enumeration): forall integer x, a(x)==b(x)."""
    cuts, cells = integer_cells(a, b)
    for cell in cells:
        slope, offset = _delta(a, b, cell.point())
        if not _zero(slope, offset, cell):
            x = _counterexample(slope, offset, cell)
            if a.predict(x) == b.predict(x):
                raise AssertionError('invalid equivalence witness')
            return Decision(False, "all_integer_equal", len(cells), cuts, x)
    return Decision(True, "all_integer_equal", len(cells), cuts, None)

def universal_correctness_preserved(old: Net, new: Net, target: Net) -> Decision:
    """Exact forall integer x: old(x)==target(x) -> new(x)==target(x)."""
    cuts, cells = integer_cells(old, new, target)
    for cell in cells:
        a, b = _delta(old, target, cell.point())
        na, nb = _delta(new, target, cell.point())
        if a == 0 and b == 0:
            if _zero(na, nb, cell):
                continue
            x = _counterexample(na, nb, cell)
        elif a == 0 or (-b) % a != 0:
            continue  # old is never correct on this cell
        else:
            x = (-b) // a  # sole old-correct point if within cell
            if not cell.contains(x) or na*x+nb == 0:
                continue
        if old.predict(x) != target.predict(x) or new.predict(x) == target.predict(x):
            raise AssertionError('invalid lost-correctness witness')
        return Decision(False, "universal_correctness_preserved",
                        len(cells), cuts, x)
    return Decision(True, "universal_correctness_preserved",
                    len(cells), cuts, None)

def exact_interval_max_error(net: Net, target: Net,
                             low: int, high: int) -> tuple[int, int]:
    """Max |net-target| for ALL integer x in interval, using cell endpoints."""
    if type(low) is not int or type(high) is not int or low > high:
        raise ValueError("bad integer interval")
    _, cells = integer_cells(net, target)
    points = {low, high}
    for cell in cells:
        lo = low if cell.low is None else max(low, cell.low)
        hi = high if cell.high is None else min(high, cell.high)
        if lo <= hi:
            points.update((lo, hi))
    return max((abs(net.predict(x)-target.predict(x)), x) for x in points)

def single_neuron(relu: bool, weight: int, bias: int) -> Net:
    """Embed the existing (relu or linear) model exactly into the ReLU basis."""
    if type(relu) is not bool or type(weight) is not int or type(bias) is not int:
        raise TypeError("invalid neuron")
    if relu:
        return Net((Term(1, weight, bias),))
    # For ALL integers z, z = max(0,z) - max(0,-z).
    return Net((Term(1, weight, bias), Term(-1, -weight, -bias)))
