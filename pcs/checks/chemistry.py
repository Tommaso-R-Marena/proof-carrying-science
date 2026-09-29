from __future__ import annotations
import re
from collections import Counter

_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")


def parse_formula(formula: str) -> Counter[str]:
    if not formula:
        raise ValueError("empty formula")
    pos = 0
    out: Counter[str] = Counter()
    for m in _TOKEN.finditer(formula):
        if m.start() != pos:
            raise ValueError(f"unsupported molecular formula syntax near {formula[pos:]!r}")
        elem, n = m.groups()
        out[elem] += int(n or "1")
        pos = m.end()
    if pos != len(formula):
        raise ValueError(f"unsupported molecular formula syntax near {formula[pos:]!r}")
    if not out:
        raise ValueError(f"could not parse molecular formula {formula!r}")
    return out


def _side(entries: list[dict]) -> Counter[str]:
    total: Counter[str] = Counter()
    for entry in entries:
        coeff = entry.get("coefficient", 1)
        if not isinstance(coeff, int) or coeff <= 0:
            raise ValueError("reaction coefficients must be positive integers")
        for element, count in parse_formula(entry["formula"]).items():
            total[element] += coeff * count
    return total


def reaction_balanced(reactants: list[dict], products: list[dict]) -> tuple[bool, dict]:
    left, right = _side(reactants), _side(products)
    elements = sorted(set(left) | set(right))
    delta = {e: right[e] - left[e] for e in elements if right[e] != left[e]}
    return (not delta, {
        "reactant_atoms": dict(left),
        "product_atoms": dict(right),
        "delta_product_minus_reactant": delta,
    })
