"""Pearl front-door criterion for finite DAGs (exact graphical check).

A set M satisfies the front-door criterion relative to (X, Y) if:
  (i)   M intercepts all directed paths from X to Y
  (ii)  there is no unblocked backdoor path from X to M
  (iii) all backdoor paths from M to Y are blocked by X

Under these conditions (plus positivity / consistency / DAG correctness):
  P(Y | do(X=x)) = Σ_m P(M=m | X=x) Σ_{x'} P(Y | X=x', M=m) P(X=x')
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import FrozenSet, Iterable, List, Optional, Sequence, Tuple

from .dag import CausalDAG, GraphError
from .d_separation import find_backdoor_paths, path_blocked, d_separated


ASSUMPTIONS = (
    "dag_is_correct_causal_graph",
    "front_door_graphical_conditions",
    "consistency_Yx_equals_Y_when_X_x",
    "positivity_for_front_door_conditionals",
)


@dataclass(frozen=True, slots=True)
class FrontDoorResult:
    treatment: str
    outcome: str
    mediators: FrozenSet[str]
    valid: bool
    reasons: Tuple[str, ...]
    formula: Optional[str]
    assumptions: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "treatment": self.treatment,
            "outcome": self.outcome,
            "mediators": sorted(self.mediators),
            "valid": self.valid,
            "reasons": list(self.reasons),
            "formula": self.formula,
            "assumptions": list(self.assumptions),
            "criterion": "frontdoor",
        }


def _directed_paths(graph: CausalDAG, src: str, dst: str) -> list[list[str]]:
    """Enumerate simple directed paths src ⇝ dst."""
    paths: list[list[str]] = []

    def dfs(cur: str, path: list[str]) -> None:
        if cur == dst and len(path) > 1:
            paths.append(list(path))
            return
        for c in graph.children(cur):
            if c in path:
                continue
            path.append(c)
            dfs(c, path)
            path.pop()

    dfs(src, [src])
    return paths


def verify_frontdoor_set(
    graph: CausalDAG,
    treatment: str,
    outcome: str,
    m: Iterable[str],
) -> FrontDoorResult:
    if treatment not in graph.nodes or outcome not in graph.nodes:
        raise GraphError("unknown treatment or outcome")
    M = frozenset(m)
    unknown = M - graph.nodes
    if unknown:
        return FrontDoorResult(
            treatment=treatment,
            outcome=outcome,
            mediators=M,
            valid=False,
            reasons=(f"mediator set contains unknown variables: {sorted(unknown)}",),
            formula=None,
            assumptions=ASSUMPTIONS,
        )
    if treatment in M or outcome in M:
        return FrontDoorResult(
            treatment=treatment,
            outcome=outcome,
            mediators=M,
            valid=False,
            reasons=("mediator set must not contain treatment or outcome",),
            formula=None,
            assumptions=ASSUMPTIONS,
        )

    reasons: List[str] = []

    # (i) M intercepts every directed path from X to Y
    dpaths = _directed_paths(graph, treatment, outcome)
    if not dpaths:
        reasons.append("no directed path from treatment to outcome")
    for p in dpaths:
        interior = set(p[1:-1])
        if not (interior & M):
            reasons.append(
                "directed path not intercepted by M: " + "→".join(p)
            )

    # (ii) no unblocked backdoor from X to any m in M (equivalently: empty
    # adjustment blocks all backdoors X ⇢ m). Pearl: no backdoor path from X to M.
    for med in sorted(M):
        bds = find_backdoor_paths(graph, treatment, med)
        open_xm = [p for p in bds if not path_blocked(graph, p, set())]
        if open_xm:
            reasons.append(
                f"unblocked backdoor from treatment to mediator {med}: "
                + "; ".join("-".join(p) for p in open_xm[:3])
            )

    # (iii) X blocks all backdoors from M to Y
    for med in sorted(M):
        bds = find_backdoor_paths(graph, med, outcome)
        open_my = [p for p in bds if not path_blocked(graph, p, {treatment})]
        if open_my:
            reasons.append(
                f"backdoor from mediator {med} to outcome not blocked by treatment: "
                + "; ".join("-".join(p) for p in open_my[:3])
            )

    valid = not reasons and bool(dpaths)
    if valid:
        mnames = ",".join(sorted(M))
        formula = (
            f"P({outcome}|do({treatment}=x)) = "
            f"Σ_{{{mnames}}} P({mnames}|{treatment}=x) "
            f"Σ_{{x'}} P({outcome}|{treatment}=x',{mnames}) P({treatment}=x')"
        )
        reasons = ("front-door criterion satisfied under declared assumptions",)
    else:
        formula = None
        if not reasons:
            reasons = ("front-door criterion not satisfied",)

    return FrontDoorResult(
        treatment=treatment,
        outcome=outcome,
        mediators=M,
        valid=valid,
        reasons=tuple(reasons),
        formula=formula,
        assumptions=ASSUMPTIONS,
    )


def find_frontdoor_sets(
    graph: CausalDAG,
    treatment: str,
    outcome: str,
    max_size: Optional[int] = None,
) -> List[FrontDoorResult]:
    pool = sorted(n for n in graph.nodes if n not in {treatment, outcome})
    if max_size is None:
        max_size = min(3, len(pool))
    out: List[FrontDoorResult] = []
    for r in range(1, max_size + 1):
        for subset in combinations(pool, r):
            res = verify_frontdoor_set(graph, treatment, outcome, subset)
            if res.valid:
                out.append(res)
    out.sort(key=lambda x: (len(x.mediators), sorted(x.mediators)))
    return out
