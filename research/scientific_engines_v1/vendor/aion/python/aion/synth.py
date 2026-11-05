"""Untrusted certificate synthesiser.

Uses floating point Gauss-Seidel iterations to *propose* certificate tables, then
converts every float exactly to a dyadic rational.  Soundness never depends on this
file: the output is accepted only if `checker.py` (and, for exported certificates,
the Lean checker) accepts it.  If the exact check fails, the synthesiser enlarges its
safety margin and retries (a simple counterexample-guided repair loop).
"""
from __future__ import annotations

import math
from fractions import Fraction
from typing import Dict, List, Sequence, Tuple

from .crn import CRN
from . import checker as ck

State = Tuple[int, ...]


def qstr(q: Fraction) -> str:
    return f"{q.numerator}/{q.denominator}" if q.denominator != 1 else str(q.numerator)


def key(x: State) -> str:
    return ",".join(map(str, x))


def candidate_rhos():
    vals = set()
    for num in range(101, 400):
        vals.add(Fraction(num, 100))
    for num in range(4, 41):
        vals.add(Fraction(num))
    return sorted(vals)


def choose_tail(crn: CRN, jB: int, lvl: int, zero, box, other_rho=None):
    """Pick the largest rho_jB (others fixed, default 1) passing every tail cell check."""
    best = None
    for r in candidate_rhos():
        rho = [Fraction(1)] * crn.d if other_rho is None else list(other_rho)
        rho[jB] = r
        ok = True
        for j in range(crn.d):
            if j == jB:
                continue
            corner = [box[j] if i == j else (1 if zero[i] else 0) for i in range(crn.d)]
            if not ck.cell_check(crn, rho, corner)[0]:
                ok = False
                break
        if ok:
            best = rho
    if best is None:
        return None
    C = Fraction(1) / best[jB] ** lvl
    return best, C


def _neighbors(crn: CRN, states: List[State]):
    nb = {}
    for x in states:
        lst = []
        for r in range(len(crn.reactions)):
            a = crn.propf(r, x)
            if a > 0:
                lst.append((a, crn.nxt(r, x)))
        nb[x] = lst
    return nb


def gauss_seidel(crn, interior, value_fn, factor, iters=200000, tol=1e-15):
    """Iterate h(x) = factor * sum_r a_r h(y_r) / a(x) on `interior`, with fixed values
    elsewhere given by `value_fn`.  Returns dict."""
    nb = _neighbors(crn, interior)
    h = {x: 0.0 for x in interior}
    inside = set(interior)
    for it in range(iters):
        delta = 0.0
        for x in interior:
            s = 0.0
            a = 0.0
            for ar, y in nb[x]:
                a += ar
                s += ar * (h[y] if y in inside else value_fn(y))
            new = factor * s / a if a > 0 else 0.0
            old = h[x]
            if old != new:
                rel = abs(new - old) / max(abs(new), 1e-300)
                if rel > delta:
                    delta = rel
            h[x] = new
        if delta < tol:
            break
    return h


RHO_JB = [Fraction(v) for v in ["21/20", "11/10", "6/5", "13/10", "3/2", "7/4", "2", "5/2",
                                   "3", "4", "5", "6", "8", "10"]]
RHO_OTHER = [Fraction(v) for v in ["1", "21/20", "11/10", "5/4", "3/2", "2", "3", "5"]]


def tail_candidates(crn: CRN, jB: int, zero, box):
    """All (rho) on a small grid passing every tail cell check (others share one value)."""
    out = []
    for ro in RHO_OTHER:
        for rj in RHO_JB:
            rho = [ro] * crn.d
            rho[jB] = rj
            ok = True
            for j in range(crn.d):
                if j == jB:
                    continue
                corner = [box[j] if i == j else (1 if zero[i] else 0) for i in range(crn.d)]
                if not ck.cell_check(crn, rho, corner)[0]:
                    ok = False
                    break
            if ok:
                out.append(rho)
    return out


def synth_upper(crn: CRN, jB: int, lvl: int, zero, box, x0=None, eta=1e-9, max_tries=4,
                verbose=False):
    cands = tail_candidates(crn, jB, zero, box)
    if not cands:
        return None, "no exponential tail barrier on the search grid passes the cell checks"
    interior = [x for x in ck.box_states(box) if x[jB] < lvl and not ck.taboo(zero, x)]
    J = max([max(R.inp) for R in crn.reactions] + [0])
    layer = [x for x in ck.box_states(box)
             if x[jB] < lvl and any(i != jB and box[i] <= x[i] + J for i in range(crn.d))]
    x0 = tuple(x0) if x0 is not None else interior[0]
    scored = []
    for rho in cands:
        C = Fraction(1) / rho[jB] ** lvl
        Cf = float(C)
        rhof = [float(r) for r in rho]

        def tailf(y, Cf=Cf, rhof=rhof):
            if y[jB] >= lvl:
                return 1.0
            if ck.in_box(y, box) and ck.taboo(zero, y):
                return 0.0
            v = Cf
            for r, yi in zip(rhof, y):
                v *= r ** yi
            return v
        h = gauss_seidel(crn, interior, tailf, 1.0 + eta, tol=1e-10)
        # float pre-screen of the interface-layer condition
        ok = all(h[x] <= Cf * math.prod(r ** xi for r, xi in zip(rhof, x)) * (1 - 1e-6)
                 for x in layer if x in h)
        if ok:
            scored.append((h.get(x0, 1.0), rho))
            if verbose:
                print("  tail", [str(r) for r in rho], "U(x0)~", h.get(x0))
    if not scored:
        return None, "no candidate tail dominates the core solution on the interface layer"
    scored.sort(key=lambda t: t[0])
    for _, rho in scored[:3]:
        C = Fraction(1) / rho[jB] ** lvl
        Cf = float(C)
        rhof = [float(r) for r in rho]

        def tailf(y):
            if y[jB] >= lvl:
                return 1.0
            if ck.in_box(y, box) and ck.taboo(zero, y):
                return 0.0
            v = Cf
            for r, yi in zip(rhof, y):
                v *= r ** yi
            return v
        e = eta
        for attempt in range(max_tries):
            h = gauss_seidel(crn, interior, tailf, 1.0 + e)
            table = {}
            for x in ck.box_states(box):
                if x[jB] >= lvl:
                    v = 1.0
                elif ck.taboo(zero, x):
                    v = 0.0
                else:
                    v = h[x]
                table[key(x)] = qstr(Fraction(v))
            up = {"box": list(box), "C": qstr(C), "rho": [qstr(r) for r in rho], "table": table}
            res = ck.check_upper(crn, {"species": jB, "level": lvl}, zero, up)
            if res["ok"]:
                return up, None
            if verbose:
                print("  upper attempt", attempt, "eta", e, res["reasons"][:2])
            e *= 10
    return None, "exact check failed after repairs"


def synth_lower(crn: CRN, jB: int, lvl: int, zero, box, eta=1e-9, max_tries=6, verbose=False):
    interior = [x for x in ck.box_states(box) if x[jB] < lvl and not ck.taboo(zero, x)]

    def outside(y):
        return 1.0 if y[jB] >= lvl else 0.0

    for attempt in range(max_tries):
        h = gauss_seidel(crn, interior, outside, 1.0 / (1.0 + eta))
        D = [x for x in interior if h[x] > 0]
        Dset = set(D)
        W = gauss_seidel_affine(crn, D)
        F = {}
        V = {}
        for x in ck.box_states(box):
            F[key(x)] = qstr(Fraction(h.get(x, 0.0)))
            V[key(x)] = qstr(Fraction(2.0 * W.get(x, 0.0) + 1.0) if x in Dset else Fraction(0))
        lo = {"box": list(box), "F": F, "V": V}
        res = ck.check_lower(crn, {"species": jB, "level": lvl}, zero, lo)
        if res["ok"]:
            return lo, None
        if verbose:
            print("  lower attempt", attempt, "eta", eta, res["reasons"][:2])
        eta *= 10
    return None, "exact check failed after repairs"


def gauss_seidel_affine(crn, D, iters=200000, tol=1e-13):
    """Expected number of jumps before leaving D: W = 1 + P W on D, 0 outside."""
    nb = _neighbors(crn, D)
    Ds = set(D)
    W = {x: 0.0 for x in D}
    for it in range(iters):
        delta = 0.0
        for x in D:
            s = 0.0
            a = 0.0
            for ar, y in nb[x]:
                a += ar
                if y in Ds:
                    s += ar * W[y]
            new = 1.0 + s / a
            rel = abs(new - W[x]) / new
            if rel > delta:
                delta = rel
            W[x] = new
        if delta < tol:
            break
    return W


def synth_sandwich(crn: CRN, jB: int, lvl: int, zero, box, x0, verbose=False, digits=8):
    up, err = synth_upper(crn, jB, lvl, zero, box, x0=x0, verbose=verbose)
    if up is None:
        return None, "upper: " + err
    lo, err = synth_lower(crn, jB, lvl, zero, box, verbose=verbose)
    if lo is None:
        return None, "lower: " + err
    target = {"species": jB, "level": lvl}
    U = ck.check_upper(crn, target, zero, up)["g"](tuple(x0))
    L = ck.check_lower(crn, target, zero, lo)["f"](tuple(x0))
    # round claims outward to a short decimal-scientific rational
    Lc = round_down(L, digits)
    Uc = round_up(U, digits)
    cert = {
        "format": "AION-sandwich-1",
        "model": crn.to_json(),
        "target": target,
        "taboo_zero": [bool(z) for z in zero],
        "x0": list(x0),
        "upper": up,
        "lower": lo,
        "claim": {"lower": qstr(Lc), "upper": qstr(Uc)},
    }
    return cert, None


def _sci(q: Fraction, digits: int, up: bool) -> Fraction:
    if q == 0:
        return Fraction(0)
    e = math.floor(math.log10(float(q))) - (digits - 1)
    scale = Fraction(10) ** e
    m = q / scale
    mi = math.ceil(m) if up else math.floor(m)
    return mi * scale


def round_down(q: Fraction, digits: int) -> Fraction:
    return _sci(q, digits, up=False)


def round_up(q: Fraction, digits: int) -> Fraction:
    return _sci(q, digits, up=True)
