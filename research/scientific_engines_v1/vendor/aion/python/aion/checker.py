"""Independent exact certificate checker (pure Python, `fractions` only).

This file mirrors, condition by condition, the executable checker whose soundness
is machine-checked in `RequestProject/AION/Checker.lean`:

  * `checkUpper`  <->  `check_upper`
  * `checkLower`  <->  `check_lower`
  * `cellCheck`   <->  `cell_check`

It is intentionally small and has no dependency on the synthesiser.  Every
rejection carries an explicit reason.  Certificates are JSON documents; all numbers
are exact rationals written as strings "p/q".
"""
from __future__ import annotations

import itertools
from fractions import Fraction
from math import comb
from typing import Dict, List, Sequence, Tuple

from .crn import CRN, desc_fact

State = Tuple[int, ...]


class Rejected(Exception):
    pass


# ---------------------------------------------------------------- utilities

def parse_q(v) -> Fraction:
    if isinstance(v, bool):
        raise Rejected(f"malformed rational {v!r}")
    if isinstance(v, int):
        return Fraction(v)
    if isinstance(v, str):
        try:
            return Fraction(v)
        except (ValueError, ZeroDivisionError):
            raise Rejected(f"malformed rational {v!r}")
    raise Rejected(f"non-exact number {v!r} (floats are not accepted)")


def box_states(box: Sequence[int]):
    return itertools.product(*[range(b) for b in box])


def in_box(x: State, box: Sequence[int]) -> bool:
    return all(0 <= xi < b for xi, b in zip(x, box))


def taboo(zero: Sequence[bool], x: State) -> bool:
    return any(z and xi == 0 for z, xi in zip(zero, x))


def exp_bar(rho: Sequence[Fraction], x: State) -> Fraction:
    v = Fraction(1)
    for r, xi in zip(rho, x):
        v *= r ** xi
    return v


def gen(crn: CRN, g, x: State) -> Fraction:
    gx = g(x)
    s = Fraction(0)
    for r in range(len(crn.reactions)):
        a = crn.prop(r, x)
        if a:
            s += a * (g(crn.nxt(r, x)) - gx)
    return s


def total(crn: CRN, x: State) -> Fraction:
    return sum((crn.prop(r, x) for r in range(len(crn.reactions))), Fraction(0))


# ------------------------------------------------- falling-factorial cell check

def jump_factor(crn: CRN, rho, r: int) -> Fraction:
    R = crn.reactions[r]
    num = Fraction(1)
    den = Fraction(1)
    for i in range(crn.d):
        num *= rho[i] ** R.out[i]
        den *= rho[i] ** R.inp[i]
    return num / den - 1


def drift_terms(crn: CRN, rho) -> List[Tuple[State, Fraction]]:
    return [(crn.reactions[r].inp, crn.reactions[r].k * jump_factor(crn, rho, r))
            for r in range(len(crn.reactions))]


def shift1(j: int, m: int, L):
    out = []
    for e, c in L:
        n = e[j]
        for kk in range(n + 1):
            e2 = e[:j] + (kk,) + e[j + 1:]
            out.append((e2, c * comb(n, kk) * desc_fact(m, n - kk)))
    return out


def shift_all(m: Sequence[int], L):
    # same order as Lean's `shiftList m (List.finRange d)` (innermost = last coordinate)
    for j in reversed(range(len(m))):
        L = shift1(j, m[j], L)
    return L


def grouped(L) -> Dict[State, Fraction]:
    G: Dict[State, Fraction] = {}
    for e, c in L:
        G[e] = G.get(e, Fraction(0)) + c
    return G


def cell_check(crn: CRN, rho, corner: Sequence[int]):
    """Return (ok, offending_basis_elements)."""
    G = grouped(shift_all(corner, drift_terms(crn, rho)))
    bad = {e: c for e, c in G.items() if c > 0}
    return (len(bad) == 0, bad)


def drift_val(crn: CRN, rho, x: State) -> Fraction:
    s = Fraction(0)
    for r, R in enumerate(crn.reactions):
        p = 1
        for xi, a in zip(x, R.inp):
            p *= desc_fact(xi, a)
        s += R.k * jump_factor(crn, rho, r) * p
    return s


# ---------------------------------------------------------------- tables

def parse_table(tab, box, name) -> Dict[State, Fraction]:
    """Table given as dict "i,j,..." -> "p/q"; missing core entries are an error."""
    if not isinstance(tab, dict):
        raise Rejected(f"{name}: table must be an object")
    T: Dict[State, Fraction] = {}
    for k, v in tab.items():
        try:
            x = tuple(int(s) for s in k.split(","))
        except ValueError:
            raise Rejected(f"{name}: malformed state key {k!r}")
        if len(x) != len(box):
            raise Rejected(f"{name}: state {k!r} has wrong dimension")
        T[x] = parse_q(v)
    for x in box_states(box):
        if x not in T:
            raise Rejected(f"{name}: missing core entry for state {x}")
    return T


# ---------------------------------------------------------------- upper

def upper_g(cert_u, T, x: State) -> Fraction:
    jB, lvl, box, C, rho = cert_u
    if x[jB] >= lvl:
        return Fraction(1)
    if in_box(x, box):
        return T[x]
    return C * exp_bar(rho, x)


def check_upper(crn: CRN, target, zero, up, max_report=5):
    """Mirror of `checkUpper`.  Returns dict with verdict, reasons and g."""
    reasons: List[str] = []
    try:
        errs = crn.validate()
        if errs:
            raise Rejected("; ".join(errs))
        jB = int(target["species"])
        lvl = int(target["level"])
        box = [int(b) for b in up["box"]]
        C = parse_q(up["C"])
        rho = [parse_q(r) for r in up["rho"]]
        if not (0 <= jB < crn.d) or len(box) != crn.d or len(rho) != crn.d or len(zero) != crn.d:
            raise Rejected("dimension mismatch")
        T = parse_table(up["table"], box, "upper.table")
    except Rejected as e:
        return {"ok": False, "reasons": [f"malformed: {e}"]}
    if not lvl <= box[jB]:
        reasons.append("box must cover the target species up to the target level")
    if not C > 0:
        reasons.append("C must be positive")
    if not all(r >= 1 for r in rho):
        reasons.append("all rho_i must be >= 1")
    if not C * rho[jB] ** lvl >= 1:
        reasons.append("C * rho_jB^level must be >= 1 (tail must dominate 1 on the target)")
    cu = (jB, lvl, box, C, rho)
    g = lambda x: upper_g(cu, T, x)
    J = max([max(R.inp) for R in crn.reactions] + [0])
    nbad = 0
    for x in box_states(box):
        if T[x] < 0:
            reasons.append(f"negative table value at {x}")
            nbad += 1
        if any(i != jB and box[i] <= x[i] + J for i in range(crn.d)) and x[jB] < lvl:
            if not T[x] <= C * exp_bar(rho, x):
                nbad += 1
                if nbad <= max_report:
                    reasons.append(f"interface layer: table exceeds tail barrier at {x}")
        if not taboo(zero, x) and x[jB] < lvl:
            Lg = gen(crn, g, x)
            if Lg > 0:
                nbad += 1
                if nbad <= max_report:
                    reasons.append(f"supersolution inequality fails at core state {x}: Lg = {float(Lg):.3e} > 0")
    if nbad > max_report:
        reasons.append(f"... {nbad} core violations in total")
    for j in range(crn.d):
        if j == jB:
            continue
        corner = [box[j] if i == j else (1 if zero[i] else 0) for i in range(crn.d)]
        ok, bad = cell_check(crn, rho, corner)
        if not ok:
            reasons.append(f"tail cell x >= {corner}: positive falling-factorial coefficients {dict((k, str(v)) for k, v in list(bad.items())[:3])}")
    return {"ok": not reasons, "reasons": reasons, "g": g}


# ---------------------------------------------------------------- lower

def check_lower(crn: CRN, target, zero, lo, max_report=5):
    """Mirror of `checkLower` (taboo set = some `zero` species extinct)."""
    reasons: List[str] = []
    try:
        errs = crn.validate()
        if errs:
            raise Rejected("; ".join(errs))
        jB = int(target["species"])
        lvl = int(target["level"])
        box = [int(b) for b in lo["box"]]
        if len(box) != crn.d or len(zero) != crn.d:
            raise Rejected("dimension mismatch")
        F = parse_table(lo["F"], box, "lower.F")
        V = parse_table(lo["V"], box, "lower.V")
    except Rejected as e:
        return {"ok": False, "reasons": [f"malformed: {e}"]}

    def f(x):
        if x[jB] >= lvl:
            return Fraction(1)
        if in_box(x, box) and not taboo(zero, x):
            return F[x]
        return Fraction(0)

    def Vf(x):
        return V[x] if in_box(x, box) else Fraction(0)

    nbad = 0
    for x in box_states(box):
        if V[x] < 0:
            nbad += 1
            reasons.append(f"negative escape function at {x}")
        if not taboo(zero, x) and x[jB] < lvl and F[x] > 0:
            a = total(crn, x)
            msgs = []
            if not a > 0:
                msgs.append("zero total rate")
            if gen(crn, f, x) < 0:
                msgs.append("subsolution inequality fails")
            if gen(crn, Vf, x) > -a:
                msgs.append("Lyapunov escape inequality fails")
            if msgs:
                nbad += 1
                if nbad <= max_report:
                    reasons.append(f"state {x}: " + ", ".join(msgs))
    if nbad > max_report:
        reasons.append(f"... {nbad} lower-certificate violations in total")
    return {"ok": not reasons, "reasons": reasons, "f": f}


# ---------------------------------------------------------------- full certificate

def check_certificate(cert) -> dict:
    """Check a full sandwich certificate.  Returns a report dict."""
    rep = {"ok": False, "reasons": []}
    try:
        crn = CRN.from_json(cert["model"])
    except Exception as e:  # malformed model
        rep["reasons"].append(f"malformed model: {e}")
        return rep
    try:
        target = cert["target"]
        zero = [bool(z) for z in cert["taboo_zero"]]
        x0 = tuple(int(v) for v in cert["x0"])
        claimed_L = parse_q(cert["claim"]["lower"])
        claimed_U = parse_q(cert["claim"]["upper"])
    except (KeyError, Rejected, TypeError, ValueError) as e:
        rep["reasons"].append(f"malformed certificate header: {e}")
        return rep
    U = check_upper(crn, target, zero, cert["upper"])
    Lr = check_lower(crn, target, zero, cert["lower"])
    rep["upper_reasons"] = U["reasons"]
    rep["lower_reasons"] = Lr["reasons"]
    if U["ok"]:
        gx0 = U["g"](x0)
        rep["upper_at_x0"] = str(gx0)
        if not gx0 <= claimed_U:
            rep["reasons"].append(f"claimed upper bound {claimed_U} is below certified value {float(gx0):.6e}")
    else:
        rep["reasons"].append("upper certificate rejected")
    if Lr["ok"]:
        fx0 = Lr["f"](x0)
        rep["lower_at_x0"] = str(fx0)
        if not claimed_L <= fx0:
            rep["reasons"].append(f"claimed lower bound {claimed_L} exceeds certified value {float(fx0):.6e}")
    else:
        rep["reasons"].append("lower certificate rejected")
    rep["ok"] = not rep["reasons"]
    return rep
