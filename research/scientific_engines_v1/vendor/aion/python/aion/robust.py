"""Parameter-robust certificates for interval rate constants.

Every rate constant k_r ranges over an exact rational interval [lo_r, hi_r]; all
reactions are mass-action, so every quantity the checker inspects is *affine* in the
parameter vector theta = (k_r).  One certificate then covers the whole box:

  * core:   sum_r max(lo_r s_r, hi_r s_r) <= 0, s_r = (x)_{alpha_r} (g(y_r) - g(x));
  * tails:  for each falling-factorial basis element e of the shifted drift
            polynomial, sum_r max(lo_r W_r(e), hi_r W_r(e)) <= 0, where W_r(e) is the
            coefficient contributed by reaction r with unit rate constant;
  * lower:  the same with min / max exchanged, plus a robust escape certificate.

This is the executable counterpart of `AffineFamily.robust_supersolution`
(Lean, `RequestProject/AION/Composition.lean`), which proves that the robust drift
bound implies the probability bound for every parameter in the box.  The tail and
lower-bound extensions follow by the same one-line affine argument (see
docs/MAIN_THEOREMS.md, Theorem R); this executable robust checker is *not* itself
machine-checked in Lean (documented in docs/TRUST_BOUNDARIES.md).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence, Tuple

from .crn import CRN, desc_fact
from . import checker as ck
from .synth import key, qstr

Interval = Tuple[Fraction, Fraction]


def dfac(crn: CRN, r: int, x) -> int:
    p = 1
    for xi, a in zip(x, crn.reactions[r].inp):
        p *= desc_fact(xi, a)
    return p


def robust_cell_check(crn: CRN, iv: Sequence[Interval], rho, corner):
    G = {}
    for r, R in enumerate(crn.reactions):
        Lr = ck.shift_all(corner, [(R.inp, ck.jump_factor(crn, rho, r))])
        Gr = ck.grouped(Lr)
        for e, w in Gr.items():
            lo, hi = iv[r]
            G[e] = G.get(e, Fraction(0)) + max(lo * w, hi * w)
    bad = {e: c for e, c in G.items() if c > 0}
    return not bad, bad


def check_upper_robust(crn: CRN, iv, target, zero, up):
    reasons: List[str] = []
    jB = int(target["species"]); lvl = int(target["level"])
    box = [int(b) for b in up["box"]]
    C = ck.parse_q(up["C"]); rho = [ck.parse_q(r) for r in up["rho"]]
    T = ck.parse_table(up["table"], box, "upper.table")
    if any(lo < 0 or hi < lo for lo, hi in iv):
        reasons.append("invalid parameter interval")
    if not lvl <= box[jB]:
        reasons.append("box must cover target level")
    if not (C > 0 and all(r >= 1 for r in rho) and C * rho[jB] ** lvl >= 1):
        reasons.append("tail normalisation conditions fail")
    cu = (jB, lvl, box, C, rho)
    g = lambda x: ck.upper_g(cu, T, x)
    J = max([max(R.inp) for R in crn.reactions] + [0])
    for x in ck.box_states(box):
        if T[x] < 0:
            reasons.append(f"negative table value at {x}")
        if any(i != jB and box[i] <= x[i] + J for i in range(crn.d)) and x[jB] < lvl:
            if not T[x] <= C * ck.exp_bar(rho, x):
                reasons.append(f"interface layer violated at {x}")
        if not ck.taboo(zero, x) and x[jB] < lvl:
            gx = g(x)
            s = Fraction(0)
            for r in range(len(crn.reactions)):
                d = dfac(crn, r, x)
                if d:
                    sr = d * (g(crn.nxt(r, x)) - gx)
                    s += max(iv[r][0] * sr, iv[r][1] * sr)
            if s > 0:
                reasons.append(f"robust supersolution inequality fails at {x}")
    for j in range(crn.d):
        if j == jB:
            continue
        corner = [box[j] if i == j else (1 if zero[i] else 0) for i in range(crn.d)]
        ok, bad = robust_cell_check(crn, iv, rho, corner)
        if not ok:
            reasons.append(f"robust tail cell {corner} fails")
    return {"ok": not reasons, "reasons": reasons[:8], "g": g}


def check_lower_robust(crn: CRN, iv, target, zero, lo):
    reasons: List[str] = []
    jB = int(target["species"]); lvl = int(target["level"])
    box = [int(b) for b in lo["box"]]
    F = ck.parse_table(lo["F"], box, "lower.F")
    V = ck.parse_table(lo["V"], box, "lower.V")

    def f(x):
        if x[jB] >= lvl:
            return Fraction(1)
        if ck.in_box(x, box) and not ck.taboo(zero, x):
            return F[x]
        return Fraction(0)

    def Vf(x):
        return V[x] if ck.in_box(x, box) else Fraction(0)

    for x in ck.box_states(box):
        if V[x] < 0:
            reasons.append(f"negative V at {x}")
        if not ck.taboo(zero, x) and x[jB] < lvl and F[x] > 0:
            amin = Fraction(0); gf = Fraction(0); gv = Fraction(0)
            fx = f(x); vx = Vf(x)
            for r in range(len(crn.reactions)):
                d = dfac(crn, r, x)
                if not d:
                    continue
                lo_r, hi_r = iv[r]
                y = crn.nxt(r, x)
                amin += lo_r * d
                sf = d * (f(y) - fx)
                gf += min(lo_r * sf, hi_r * sf)
                sv = d * (Vf(y) - vx + 1)
                gv += max(lo_r * sv, hi_r * sv)
            if not amin > 0:
                reasons.append(f"total rate may vanish at {x}")
            if gf < 0:
                reasons.append(f"robust subsolution fails at {x}")
            if gv > 0:
                reasons.append(f"robust escape inequality fails at {x}")
    return {"ok": not reasons, "reasons": reasons[:8], "f": f}


# ------------------------------------------------------------------ synthesis

def _worst_ratio(terms, maximize):
    """Dinkelbach: extremise sum(theta w) / sum(theta a) over theta in a box;
    terms = list of (a_lo, a_hi, value)."""
    lam = sum(t[2] for t in terms) / max(len(terms), 1)
    for _ in range(50):
        num = 0.0; den = 0.0
        for alo, ahi, v in terms:
            a = (ahi if v > lam else alo) if maximize else (ahi if v < lam else alo)
            num += a * v; den += a
        new = num / den if den > 0 else 0.0
        if abs(new - lam) <= 1e-17 * max(abs(new), 1e-300):
            lam = new
            break
        lam = new
    return lam


def robust_value_iteration(crn, iv, interior, value_fn, maximize, factor, iters=100000, tol=1e-13):
    inside = set(interior)
    nb = {}
    for x in interior:
        lst = []
        for r in range(len(crn.reactions)):
            d = dfac(crn, r, x)
            if d:
                lst.append((float(iv[r][0]) * d, float(iv[r][1]) * d, crn.nxt(r, x)))
        nb[x] = lst
    h = {x: 0.0 for x in interior}
    for _ in range(iters):
        delta = 0.0
        for x in interior:
            terms = [(alo, ahi, (h[y] if y in inside else value_fn(y))) for alo, ahi, y in nb[x]]
            new = factor * _worst_ratio(terms, maximize) if terms else 0.0
            rel = abs(new - h[x]) / max(abs(new), 1e-300)
            delta = max(delta, rel)
            h[x] = new
        if delta < tol:
            break
    return h


def synth_robust(crn: CRN, iv, jB, lvl, zero, box, x0, rho, eta=1e-8):
    """Robust sandwich with a user-chosen tail exponent vector `rho`."""
    target = {"species": jB, "level": lvl}
    C = Fraction(1) / rho[jB] ** lvl
    Cf = float(C); rf = [float(r) for r in rho]

    def tailf(y):
        if y[jB] >= lvl:
            return 1.0
        if ck.in_box(y, box) and ck.taboo(zero, y):
            return 0.0
        v = Cf
        for r, yi in zip(rf, y):
            v *= r ** yi
        return v
    interior = [x for x in ck.box_states(box) if x[jB] < lvl and not ck.taboo(zero, x)]
    hu = robust_value_iteration(crn, iv, interior, tailf, True, 1 + eta)
    table = {}
    for x in ck.box_states(box):
        v = 1.0 if x[jB] >= lvl else (0.0 if ck.taboo(zero, x) else hu[x])
        table[key(x)] = qstr(Fraction(v))
    up = {"box": list(box), "C": qstr(C), "rho": [qstr(r) for r in rho], "table": table}
    hl = robust_value_iteration(crn, iv, interior, lambda y: 1.0 if y[jB] >= lvl else 0.0,
                                False, 1 / (1 + eta))
    D = [x for x in interior if hl[x] > 0]
    # robust escape function: worst-case expected jumps, times 2, plus 1
    Ds = set(D)
    W = {x: 0.0 for x in D}
    for _ in range(100000):
        delta = 0.0
        for x in D:
            terms = []
            for r in range(len(crn.reactions)):
                d = dfac(crn, r, x)
                if d:
                    y = crn.nxt(r, x)
                    terms.append((float(iv[r][0]) * d, float(iv[r][1]) * d, W[y] if y in Ds else 0.0))
            new = 1.0 + _worst_ratio(terms, True)
            delta = max(delta, abs(new - W[x]) / new)
            W[x] = new
        if delta < 1e-12:
            break
    F = {}; V = {}
    for x in ck.box_states(box):
        F[key(x)] = qstr(Fraction(hl.get(x, 0.0)))
        V[key(x)] = qstr(Fraction(2 * W[x] + 1) if x in Ds else Fraction(0))
    lo = {"box": list(box), "F": F, "V": V}
    ru = check_upper_robust(crn, iv, target, zero, up)
    rl = check_lower_robust(crn, iv, target, zero, lo)
    out = {"upper_ok": ru["ok"], "lower_ok": rl["ok"],
           "upper_reasons": ru["reasons"], "lower_reasons": rl["reasons"]}
    if ru["ok"]:
        out["U"] = ru["g"](tuple(x0))
    if rl["ok"]:
        out["L"] = rl["f"](tuple(x0))
    out["upper"] = up; out["lower"] = lo
    return out
