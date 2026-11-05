"""Independent certificate checker (Python reference; Lean is authoritative for proved kinds).

The checker recomputes mathematical obligations from claim+witness and does not
trust a generator-provided verdict field.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, List, Tuple

from certnum.certificate.schema import CERT_FORMAT, SUPPORTED_KINDS
from certnum.expr.ast import expr_from_json
from certnum.expr.eval import eval_exact, eval_interval, mean_value_enclosure
from certnum.expr.simplify import simplify
from certnum.interval.interval import Interval
from certnum.linalg.basic import residual_certificate
from certnum.opt.branch_bound import verify_coverage
from certnum.opt.coverage import verify_coverage_1d
from certnum.ode.euler import linear_scalar_enclosure
from certnum.root.isolation import RootStatus, classify_interval
from certnum.stochastic.markov import ProbDist, StochasticMatrix
from certnum.thermo.partition import partition_function_energy_bins, partition_function_exact_enum


@dataclass
class CheckResult:
    accepted: bool
    reasons: List[str]

    def to_json(self) -> dict:
        return {"accepted": self.accepted, "reasons": self.reasons}


def _fail(msg: str) -> CheckResult:
    return CheckResult(False, [msg])


def _ok(msg: str = "ok") -> CheckResult:
    return CheckResult(True, [msg])


def check_certificate(cert: Dict[str, Any]) -> CheckResult:
    if cert.get("format") != CERT_FORMAT:
        return _fail(f"bad format {cert.get('format')}")
    kind = cert.get("kind")
    if kind not in SUPPORTED_KINDS:
        return _fail(f"unsupported kind {kind}")
    claim = cert.get("claim") or {}
    witness = cert.get("witness") or {}

    if kind == "interval_enclosure":
        return _check_interval_enclosure(claim, witness)
    if kind == "root_isolation":
        return _check_root_isolation(claim, witness)
    if kind == "global_optimization":
        return _check_global_opt(claim, witness)
    if kind == "linear_residual":
        return _check_linear_residual(claim, witness)
    if kind == "markov_step":
        return _check_markov(claim, witness)
    if kind == "thermo_partition":
        return _check_thermo(claim, witness)
    if kind == "ode_linear_scalar":
        return _check_ode(claim, witness)
    if kind == "expression_equivalence":
        return _check_equiv(claim, witness)
    return _fail("unreachable")


def _check_interval_enclosure(claim, witness) -> CheckResult:
    expr = expr_from_json(claim["expr"])
    box = {k: Interval.from_json(v) for k, v in claim["box"].items()}
    claimed = Interval.from_json(claim["enclosure"])
    method = claim.get("method", "natural")
    if method == "mean_value":
        enc = mean_value_enclosure(expr, box)
    else:
        enc = eval_interval(expr, box)
    if not enc.is_ok:
        return _fail(f"re-evaluation failed: {enc.status}")
    # Recomputed enclosure is sound for the method; claimed is sound if claimed ⊇ recomputed.
    if not enc.interval.subset(claimed):
        return _fail(f"claimed enclosure does not contain recomputed {method} enclosure")
    for pt in witness.get("sample_points", []):
        env = {k: Fraction(v) for k, v in pt.items()}
        try:
            val = eval_exact(expr, env)
        except Exception as e:
            return _fail(f"sample eval failed: {e}")
        if val not in claimed:
            return _fail(f"sample {val} outside claimed enclosure")
        for k, v in env.items():
            if v not in box[k]:
                return _fail(f"sample outside box for {k}")
    return _ok(f"interval enclosure sound w.r.t. {method} extension")


def _check_root_isolation(claim, witness) -> CheckResult:
    expr = expr_from_json(claim["expr"])
    var = claim["var"]
    results = witness.get("roots", [])
    if not results:
        return _fail("no root witnesses")
    for r in results:
        I = Interval.from_json(r["interval"])
        status = RootStatus[r["status"]]
        recomputed = classify_interval(expr, var, I)
        if status is RootStatus.UNIQUE:
            if recomputed.status is not RootStatus.UNIQUE:
                return _fail(f"UNIQUE claim failed reclassification: {recomputed}")
        elif status is RootStatus.EXISTS:
            if recomputed.status not in (RootStatus.EXISTS, RootStatus.UNIQUE):
                return _fail(f"EXISTS claim failed: {recomputed}")
        elif status is RootStatus.EXCLUDED:
            if recomputed.status is not RootStatus.EXCLUDED:
                return _fail("EXCLUDED claim failed")
        # POSSIBLE/UNRESOLVED: accept as non-theorems (informational)
    return _ok("root isolation claims reclassified")


def _check_global_opt(claim, witness) -> CheckResult:
    expr = expr_from_json(claim["expr"])
    domain = {k: Interval.from_json(v) for k, v in claim["domain"].items()}
    L = Fraction(claim["lower_bound"])
    U = Fraction(claim["upper_bound"])
    coverage = [{k: Interval.from_json(v) for k, v in b.items()} for b in witness["coverage"]]
    vars_ = sorted(domain.keys())
    if not verify_coverage(domain, coverage, vars_):
        return _fail("coverage does not prove the entire domain")
    # Recompute lower bound as min of leaf natural enclosures
    from certnum.expr.eval import eval_interval

    lbs = []
    for leaf in coverage:
        enc = eval_interval(expr, leaf)
        if not enc.is_ok or enc.interval.is_empty:
            return _fail("leaf enclosure failed")
        lbs.append(enc.interval.lo)
    L_re = min(lbs)  # type: ignore[type-var]
    if L > L_re:
        return _fail(f"claimed lower bound {L} exceeds recomputed {L_re}")
    # Upper bound: incumbent must evaluate to ≤ U and be in domain
    inc = claim.get("incumbent")
    if inc is None:
        return _fail("optimization upper bound requires an in-domain incumbent")
    if set(inc) != set(domain):
        return _fail("incumbent variables do not match the domain")
    if inc is not None:
        env = {k: Fraction(v) for k, v in inc.items()}
        for k, v in env.items():
            if v not in domain[k]:
                return _fail("incumbent outside domain")
        val = eval_exact(expr, env)
        if val > U:
            return _fail("incumbent value exceeds claimed upper bound")
        if U < val:
            return _fail("upper bound below incumbent")
        # U must be ≥ val; allow U > val
        if U < val:
            return _fail("inconsistent U")
    if L > U:
        return _fail("lower > upper")
    return _ok("optimization bounds consistent with coverage")


def _check_linear_residual(claim, witness) -> CheckResult:
    A = [[Fraction(x) for x in row] for row in claim["A"]]
    b = [Fraction(x) for x in claim["b"]]
    x = [Fraction(x) for x in claim["x_hat"]]
    bound = Fraction(claim["residual_bound"])
    cert = residual_certificate(A, b, x)
    if cert.residual_inf_norm > bound:
        return _fail(f"residual {cert.residual_inf_norm} > bound {bound}")
    return _ok("residual within bound")


def _check_markov(claim, witness) -> CheckResult:
    P = StochasticMatrix([[Fraction(x) for x in row] for row in claim["P"]])
    pi = ProbDist([Fraction(x) for x in claim["pi"]])
    claimed = ProbDist([Fraction(x) for x in claim["pi_next"]])
    got = P.apply(pi)
    if got.probs != claimed.probs:
        return _fail("markov step mismatch")
    return _ok("markov step exact")


def _check_thermo(claim, witness) -> CheckResult:
    beta = Fraction(claim["beta"])
    claimed = Interval.from_json(claim["Z"])
    method = witness.get("method")
    if method == "exact_state_sum_with_certified_exp":
        energies = [Fraction(e) for e in witness["energies"]]
        cert = partition_function_exact_enum(energies, beta)
    elif method == "energy_bin_bounds":
        bins = [(int(c), Fraction(lo), Fraction(hi)) for c, lo, hi in witness["bins"]]
        cert = partition_function_energy_bins(bins, beta)
    else:
        return _fail("unknown thermo method")
    # claimed must contain recomputed
    if not cert.Z_enclosure.subset(claimed):
        # allow claimed == recomputed via mutual subset
        if claimed.subset(cert.Z_enclosure) and cert.Z_enclosure.subset(claimed):
            return _ok()
        # soundness: claimed ⊇ recomputed
        re = cert.Z_enclosure
        if claimed.lo is not None and re.lo is not None and claimed.lo <= re.lo and re.hi <= claimed.hi:
            return _ok()
        return _fail("thermo Z claim does not contain recomputation")
    return _ok("thermo Z enclosure sound")


def _check_ode(claim, witness) -> CheckResult:
    a = Fraction(claim["a"])
    b = Fraction(claim["b"])
    x0 = Fraction(claim["x0"])
    t = Fraction(claim["t"])
    claimed = Interval.from_json(claim["enclosure"])
    enc = linear_scalar_enclosure(a, b, x0, t)
    if not enc.is_ok:
        return _fail(f"ode re-eval failed {enc.status}")
    if not enc.interval.subset(claimed):
        re = enc.interval
        if claimed.lo <= re.lo and re.hi <= claimed.hi:  # type: ignore[operator]
            return _ok()
        return _fail("ode enclosure claim too tight / incorrect")
    return _ok("ode linear scalar enclosure sound")


def _check_equiv(claim, witness) -> CheckResult:
    e1 = expr_from_json(claim["left"])
    e2 = expr_from_json(claim["right"])
    # Accept if simplify equal OR random samples agree on a box
    if simplify(e1) == simplify(e2):
        return _ok("syntactic simplify equal")
    box = {k: Interval.from_json(v) for k, v in claim.get("box", {}).items()}
    samples = witness.get("samples", [])
    if not samples:
        return _fail("no equivalence evidence")
    for s in samples:
        env = {k: Fraction(v) for k, v in s.items()}
        if eval_exact(e1, env) != eval_exact(e2, env):
            return _fail("sample mismatch")
    return _ok("samples agree (not a universal proof)")
