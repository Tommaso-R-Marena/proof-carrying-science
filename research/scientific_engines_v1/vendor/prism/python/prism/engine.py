"""The PRISM research cycle.

ASSUMPTIONS → COMPATIBLE MODELS → JUSTIFIED KNOWLEDGE → REMAINING AMBIGUITY →
OPTIMAL EXPERIMENT → NEW OBSERVATION → UPDATED MODEL SPACE → NEW CERTIFICATE.

Every verdict carries a certificate that is re-checked by the independent
checker (`prism.reference.checker`) before it is reported; the search
components are never trusted.  The engine never adds assumptions on its own:
`with_assumption` requires an explicit justification and approval, and every
change is recorded in the contract log.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional

from .core import bits, popcount
from .reference import checker
from .search.sandwich import find_equiv_gap_pair, sandwich_certify
from .serialize import Spec


class Engine:
    def __init__(self, spec: Spec, claims: Optional[Dict[str, int]] = None,
                 allowed_experiments: Optional[List[int]] = None):
        self.spec = spec
        self.P = spec.P
        self.eps = spec.eps
        self.data: List = list(spec.data)
        self.claims = dict(claims or {})       # claim id -> mask of models where it holds
        self.contract_log: List[str] = [f"assumption {a['id']}: {a['description']}"
                                        for a in spec.assumptions]
        self.extra_assumptions: List[Dict] = []
        self.allowed = allowed_experiments      # None = all experiments

    # ------------------------------------------------------------ contract
    def with_assumption(self, aid: str, mask: int, justification: str, approved: bool):
        if not approved:
            raise PermissionError("assumptions may only be added with explicit approval")
        if not justification.strip():
            raise PermissionError("an added assumption must carry a justification")
        self.extra_assumptions.append({"id": aid, "mask": mask})
        self.contract_log.append(f"ADDED assumption {aid} (approved): {justification}")
        return self

    def version_space(self) -> int:
        P = self.P
        K = P.full
        for a in self.spec.assumptions + self.extra_assumptions:
            K &= a["mask"]
        for (e, o) in self.data:
            K &= P.cellmask[e][o]
        return K

    def observe(self, e: int, o: int):
        self.data.append((e, o))

    def restricted_problem(self):
        """Problem with only the allowed experiments (if restricted)."""
        if self.allowed is None:
            return self.P, list(range(self.P.k))
        from .core import Problem
        P = self.P
        ex = list(self.allowed)
        return Problem(P.models, [P.experiments[e] for e in ex], [P.outcomes[e] for e in ex],
                       [[P.obs[m][e] for e in ex] for m in range(P.n)], P.q,
                       [P.cost[e] for e in ex], P.meta), ex

    # ------------------------------------------------------------ analysis
    def inconsistency_explanation(self) -> List[str]:
        P = self.P
        out = []
        amask = P.full
        for a in self.spec.assumptions + self.extra_assumptions:
            amask &= a["mask"]
        for m in range(P.n):
            reason = None
            for a in self.spec.assumptions + self.extra_assumptions:
                if not (a["mask"] >> m) & 1:
                    reason = f"violates assumption {a['id']}"
                    break
            if reason is None:
                for i, (e, o) in enumerate(self.data):
                    if P.obs[m][e] != o:
                        reason = (f"predicts {P.outcomes[e][P.obs[m][e]]} for {P.experiments[e]} "
                                  f"but datum #{i} observed {P.outcomes[e][o]}")
                        break
            out.append(f"{P.models[m]}: {reason}")
        return out

    def analyze(self, plan: bool = True, budget_states: Optional[int] = None) -> Dict:
        P, eps = self.P, self.eps
        K = self.version_space()
        rep: Dict = {"n_admissible": popcount(K), "admissible": [P.models[m] for m in bits(K)],
                     "data": [(P.experiments[e], P.outcomes[e][o]) for e, o in self.data],
                     "verdicts": []}
        if K == 0:
            rep["verdicts"].append(("INCONSISTENT", self.inconsistency_explanation()))
            return rep
        lo, hi, mlo, mhi = P.bounds(K)
        checker.check_bounds(P, K, lo, hi, mlo, mhi)
        rep["bounds"] = (lo, hi, P.models[mlo], P.models[mhi])
        rep["bounds_idx"] = (lo, hi, mlo, mhi)
        rep["verdicts"].append(("BOUNDED", f"query ∈ [{lo}, {hi}] (sharp: attained by "
                                f"{P.models[mlo]} and {P.models[mhi]})"))
        for cid, cmask in self.claims.items():
            bad = K & ~cmask
            if bad == 0:
                rep["verdicts"].append(("CERTIFIED", f"claim {cid} holds in all {popcount(K)} admissible models"))
            else:
                m = next(iter(bits(bad)))
                assert (K >> m) & 1 and not (cmask >> m) & 1  # countermodel check
                rep["verdicts"].append(("FALSIFIED-WITHIN-MODEL", f"claim {cid}: countermodel {P.models[m]}"))
        if hi - lo <= eps:
            rep["verdicts"].append(("CERTIFIED", f"query identified to tolerance {eps}"))
            return rep
        Pr, ex = self.restricted_problem()
        pair = find_equiv_gap_pair(Pr, K, eps)
        if pair is not None:
            checker.check_impossible(Pr, K, eps, *pair)
            rep["impossible"] = pair
            rep["verdicts"].append(("UNIDENTIFIABLE", f"{P.models[pair[0]]} and {P.models[pair[1]]} agree on "
                                    f"every permitted experiment but have query {P.q[pair[0]]} vs {P.q[pair[1]]}"))
            rep["verdicts"].append(("IMPOSSIBLE", "no adaptive strategy over the permitted experiments "
                                    f"reaches tolerance {eps} (two-model certificate, Lean: impossibility)"))
            return rep
        if not plan:
            return rep
        res = sandwich_certify(Pr, K, eps, budget_states=budget_states)
        if res["status"] == "optimal":
            cert = {"policy": res["policy"], "bound": res["value"], "core": res["core"],
                    "adversary": list(res["adversary"].items())}
            checker.check_optimal(Pr, K, eps, cert)
            pol = res["policy"]
            first = ex[pol["e"]] if pol != "stop" else None
            rep["optimal"] = res
            rep["experiment_map"] = ex
            rep["verdicts"].append(("EXPERIMENT", f"run {P.experiments[first]} first; exact minimax optimal "
                                    f"total cost {res['value']} (certificate: core of {res['core_size']} models, "
                                    f"{len(res['adversary'])} adversary entries; independently checked)"))
        else:
            rep["verdicts"].append(("EXPERIMENT-UNRESOLVED", f"best verified bounds on optimal cost: "
                                    f"[{res.get('lower')}, {res.get('upper')}] — optimality unresolved"))
        return rep


def render(rep: Dict, title: str = "") -> str:
    lines = [f"== {title} ==" if title else "=="]
    lines.append(f"data: {rep['data']}")
    lines.append(f"admissible models ({rep['n_admissible']}): {', '.join(rep['admissible'][:12])}"
                 + (" ..." if rep['n_admissible'] > 12 else ""))
    for kind, msg in rep["verdicts"]:
        if isinstance(msg, list):
            lines.append(f"[{kind}]")
            lines.extend("   " + x for x in msg)
        else:
            lines.append(f"[{kind}] {msg}")
    return "\n".join(lines)
