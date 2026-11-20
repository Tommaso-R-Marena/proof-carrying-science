"""Causal reasoning tasks with graph + SCM ground truth.

Each task has:
- a natural-language prompt for models
- an explicit DAG
- an exact binary SCM (executable interventions)
- ground-truth identifiability and minimal adjustment sets
- authored control claims (positive and negative)
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import FrozenSet, List, Mapping, Optional, Sequence, Tuple

from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG
from research.proof_carrying_causal_reasoning_v1.kernel.backdoor import (
    find_minimal_backdoor_sets,
)
from research.proof_carrying_causal_reasoning_v1.kernel.scm import (
    BinarySCM,
    bernoulli,
    logistic_from_parents,
)
from research.proof_carrying_causal_reasoning_v1.kernel.certificate import CausalClaim
from research.proof_carrying_causal_reasoning_v1.kernel.counterfactual import (
    counterfactual_probability,
)


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    title: str
    domain: str
    prompt: str
    graph: CausalDAG
    scm: BinarySCM
    treatment: str
    outcome: str
    identifiable: bool
    notes: Tuple[str, ...]
    control_claims: Tuple[CausalClaim, ...]
    allowed_strategies: Tuple[str, ...] = ("backdoor",)

    def minimal_sets(self) -> List[FrozenSet[str]]:
        return [
            r.adjustment_set
            for r in find_minimal_backdoor_sets(self.graph, self.treatment, self.outcome)
        ]

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "domain": self.domain,
            "treatment": self.treatment,
            "outcome": self.outcome,
            "identifiable": self.identifiable,
            "graph": self.graph.to_dict(),
            "minimal_adjustment_sets": [sorted(s) for s in self.minimal_sets()],
            "ate": f"{self.scm.ate(self.treatment, self.outcome)}",
            "notes": list(self.notes),
            "allowed_strategies": list(self.allowed_strategies),
        }


def _claim(
    task_id: str,
    treatment: str,
    outcome: str,
    *,
    asserts_identifiable: bool,
    adjustment_set: Sequence[str] = (),
    claimed_p_do: Optional[str] = None,
    asserts_association_equals_effect: Optional[bool] = None,
    strategy: Optional[str] = None,
    evidence: Optional[Mapping[str, int]] = None,
    treatment_value: int = 1,
) -> CausalClaim:
    ev = None
    if evidence is not None:
        ev = tuple(sorted((k, int(v)) for k, v in evidence.items()))
    return CausalClaim(
        task_id=task_id,
        treatment=treatment,
        outcome=outcome,
        asserts_identifiable=asserts_identifiable,
        adjustment_set=frozenset(adjustment_set),
        claimed_p_do=claimed_p_do,
        asserts_association_equals_effect=asserts_association_equals_effect,
        strategy=strategy,
        evidence=ev,
        treatment_value=treatment_value,
        raw_text="",
    )


def _prompt(graph: CausalDAG, treatment: str, outcome: str, story: str) -> str:
    edges = ", ".join(f"{u}->{v}" for u, v in sorted(graph.edges))
    nodes = ", ".join(sorted(graph.nodes))
    return (
        "You are evaluating a causal identification query under an explicit DAG.\n"
        "Assumptions: the DAG is the correct causal graph; no unmodeled confounders "
        "among listed variables; positivity; consistency.\n"
        f"Variables: {nodes}\n"
        f"Directed edges: {edges}\n"
        f"Query: identify P({outcome} | do({treatment}=1)) from observational data "
        f"via backdoor adjustment if possible.\n"
        f"Context: {story}\n\n"
        "Respond with ONLY a JSON object of this exact shape:\n"
        "{\n"
        f'  "treatment": "{treatment}",\n'
        f'  "outcome": "{outcome}",\n'
        '  "asserts_identifiable": true or false,\n'
        '  "adjustment_set": ["Z1", ...],  // empty list if none or not identifiable\n'
        '  "claimed_p_do": null,  // optional "a/b" rational; prefer null\n'
        '  "asserts_association_equals_effect": false\n'
        "}\n"
        "Do not claim association equals causation unless it is identically true.\n"
        "Do not invent variables outside the listed set.\n"
    )


def build_tasks() -> Tuple[Task, ...]:
    tasks: List[Task] = []

    # T01: classic confounder Z → X, Z → Y, X → Y. Adjust for Z.
    g1 = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
    scm1 = BinarySCM(
        g1,
        {
            "Z": bernoulli(Fraction(1, 2)),
            "X": logistic_from_parents({"Z": Fraction(1, 2)}, Fraction(1, 4)),
            "Y": logistic_from_parents(
                {"X": Fraction(1, 4), "Z": Fraction(1, 2)}, Fraction(1, 8)
            ),
        },
    )
    tasks.append(
        Task(
            task_id="T01",
            title="Confounded treatment effect",
            domain="epidemiology-toy",
            prompt=_prompt(
                g1,
                "X",
                "Y",
                "Drug X, recovery Y, severity confounder Z. Observational association is biased.",
            ),
            graph=g1,
            scm=scm1,
            treatment="X",
            outcome="Y",
            identifiable=True,
            notes=("backdoor via {Z}", "ATE ≠ observational association"),
            control_claims=(
                _claim("T01", "X", "Y", asserts_identifiable=True, adjustment_set=["Z"]),
                _claim("T01", "X", "Y", asserts_identifiable=True, adjustment_set=[]),
                _claim(
                    "T01",
                    "X",
                    "Y",
                    asserts_identifiable=True,
                    adjustment_set=["Z"],
                    asserts_association_equals_effect=True,
                ),
            ),
        )
    )

    # T02: mediator only X → M → Y. Empty adjustment identifies total effect.
    g2 = CausalDAG.from_edges(["X", "M", "Y"], [("X", "M"), ("M", "Y")])
    scm2 = BinarySCM(
        g2,
        {
            "X": bernoulli(Fraction(1, 2)),
            "M": logistic_from_parents({"X": Fraction(1, 2)}, Fraction(1, 4)),
            "Y": logistic_from_parents({"M": Fraction(1, 2)}, Fraction(1, 4)),
        },
    )
    tasks.append(
        Task(
            task_id="T02",
            title="Pure mediation (total effect)",
            domain="mechanisms-toy",
            prompt=_prompt(
                g2,
                "X",
                "Y",
                "X affects Y only through mediator M. Total effect of do(X) needs no adjustment; "
                "conditioning on M blocks the causal path.",
            ),
            graph=g2,
            scm=scm2,
            treatment="X",
            outcome="Y",
            identifiable=True,
            notes=("empty set is valid; {M} is invalid (descendant)",),
            control_claims=(
                _claim("T02", "X", "Y", asserts_identifiable=True, adjustment_set=[]),
                _claim("T02", "X", "Y", asserts_identifiable=True, adjustment_set=["M"]),
            ),
        )
    )

    # T03: collider X → C ← Y. Conditioning on C opens a non-causal path.
    g3 = CausalDAG.from_edges(["X", "Y", "C"], [("X", "C"), ("Y", "C")])
    scm3 = BinarySCM(
        g3,
        {
            "X": bernoulli(Fraction(1, 2)),
            "Y": bernoulli(Fraction(1, 3)),
            "C": logistic_from_parents(
                {"X": Fraction(1, 2), "Y": Fraction(1, 2)}, Fraction(0)
            ),
        },
    )
    # No causal path X→Y; ATE is 0. Empty set works. Adjusting for C is wrong for association questions;
    # for P(Y|do(X)), empty is valid because there are no backdoors.
    tasks.append(
        Task(
            task_id="T03",
            title="Collider bias trap",
            domain="selection-toy",
            prompt=_prompt(
                g3,
                "X",
                "Y",
                "X and Y independently cause collider C. There is no causal effect of X on Y. "
                "Do not adjust for C.",
            ),
            graph=g3,
            scm=scm3,
            treatment="X",
            outcome="Y",
            identifiable=True,
            notes=("ATE=0; empty adjustment; {C} opens collider",),
            control_claims=(
                _claim("T03", "X", "Y", asserts_identifiable=True, adjustment_set=[]),
                _claim("T03", "X", "Y", asserts_identifiable=True, adjustment_set=["C"]),
            ),
        )
    )

    # T04: M-bias: U1→X, U1→C, U2→Y, U2→C. Adjusting for C induces bias.
    g4 = CausalDAG.from_edges(
        ["U1", "U2", "X", "Y", "C"],
        [("U1", "X"), ("U1", "C"), ("U2", "Y"), ("U2", "C"), ("X", "Y")],
    )
    scm4 = BinarySCM(
        g4,
        {
            "U1": bernoulli(Fraction(1, 2)),
            "U2": bernoulli(Fraction(1, 2)),
            "C": logistic_from_parents(
                {"U1": Fraction(1, 3), "U2": Fraction(1, 3)}, Fraction(1, 6)
            ),
            "X": logistic_from_parents({"U1": Fraction(1, 2)}, Fraction(1, 4)),
            "Y": logistic_from_parents(
                {"X": Fraction(1, 5), "U2": Fraction(1, 2)}, Fraction(1, 10)
            ),
        },
    )
    tasks.append(
        Task(
            task_id="T04",
            title="M-bias",
            domain="epidemiology-toy",
            prompt=_prompt(
                g4,
                "X",
                "Y",
                "Classic M-structure. C is a collider on a non-causal path. "
                "Empty adjustment identifies the effect; adjusting for C alone biases it.",
            ),
            graph=g4,
            scm=scm4,
            treatment="X",
            outcome="Y",
            identifiable=True,
            notes=("empty set valid; {C} invalid",),
            control_claims=(
                _claim("T04", "X", "Y", asserts_identifiable=True, adjustment_set=[]),
                _claim("T04", "X", "Y", asserts_identifiable=True, adjustment_set=["C"]),
            ),
        )
    )

    # T05: two confounders; need both or either sufficient? Z1 and Z2 both point to X and Y.
    g5 = CausalDAG.from_edges(
        ["Z1", "Z2", "X", "Y"],
        [("Z1", "X"), ("Z1", "Y"), ("Z2", "X"), ("Z2", "Y"), ("X", "Y")],
    )
    scm5 = BinarySCM(
        g5,
        {
            "Z1": bernoulli(Fraction(1, 2)),
            "Z2": bernoulli(Fraction(1, 3)),
            "X": logistic_from_parents(
                {"Z1": Fraction(1, 4), "Z2": Fraction(1, 4)}, Fraction(1, 5)
            ),
            "Y": logistic_from_parents(
                {"X": Fraction(1, 5), "Z1": Fraction(1, 4), "Z2": Fraction(1, 5)},
                Fraction(1, 10),
            ),
        },
    )
    tasks.append(
        Task(
            task_id="T05",
            title="Two independent confounders",
            domain="epidemiology-toy",
            prompt=_prompt(
                g5,
                "X",
                "Y",
                "Two independent confounders Z1 and Z2. A valid adjustment set must block both backdoors.",
            ),
            graph=g5,
            scm=scm5,
            treatment="X",
            outcome="Y",
            identifiable=True,
            notes=("minimal set is {Z1,Z2}",),
            control_claims=(
                _claim(
                    "T05", "X", "Y", asserts_identifiable=True, adjustment_set=["Z1", "Z2"]
                ),
                _claim("T05", "X", "Y", asserts_identifiable=True, adjustment_set=["Z1"]),
                _claim("T05", "X", "Y", asserts_identifiable=True, adjustment_set=[]),
            ),
        )
    )

    # T06: latent-style non-identifiability within modeled vars: only X←U→Y with U unobserved
    # We model this as a graph where the only nodes are X,Y with NO edge but the SCM has
    # dependence via... wait, without U in the graph we can't have dependence under Markov.
    # Instead: declare graph with unobserved confounder not in adjustment pool.
    # Graph shown to model: X → Y only, but TRUE graph has U. For honesty we present the
    # TRUE graph including U and mark U as unobserved (not adjustable). Identification
    # without U fails if we require adjustment using only observed {X,Y}.
    # Task framing: observed vars {X,Y}; true graph includes U; ask if identifiable from
    # observations of X,Y only → NO.
    g6 = CausalDAG.from_edges(["U", "X", "Y"], [("U", "X"), ("U", "Y"), ("X", "Y")])
    scm6 = BinarySCM(
        g6,
        {
            "U": bernoulli(Fraction(1, 2)),
            "X": logistic_from_parents({"U": Fraction(1, 2)}, Fraction(1, 4)),
            "Y": logistic_from_parents(
                {"X": Fraction(1, 5), "U": Fraction(1, 2)}, Fraction(1, 10)
            ),
        },
    )
    # For this task, "identifiable from observed {X,Y} only" is False.
    # We encode that by treating the task's identifiable flag as False and requiring
    # asserts_identifiable=False (adjustment among observed vars cannot include U).
    tasks.append(
        Task(
            task_id="T06",
            title="Unobserved confounding (non-identifiable from {X,Y})",
            domain="latent-confounding",
            prompt=(
                "You are evaluating a causal identification query.\n"
                "Observed variables only: X, Y.\n"
                "True causal graph (U is NOT observed): U->X, U->Y, X->Y.\n"
                "Query: can P(Y | do(X=1)) be identified from observations of X and Y alone "
                "via backdoor adjustment using only observed variables?\n"
                "Respond with ONLY JSON:\n"
                "{\n"
                '  "treatment": "X",\n'
                '  "outcome": "Y",\n'
                '  "asserts_identifiable": true or false,\n'
                '  "adjustment_set": [],\n'
                '  "claimed_p_do": null,\n'
                '  "asserts_association_equals_effect": false\n'
                "}\n"
                "If you claim identifiable, you may only list adjustment variables from {X,Y} "
                "(which cannot include treatment/outcome), so the set must be empty — and empty "
                "fails because of the open backdoor through U.\n"
            ),
            graph=g6,
            scm=scm6,
            treatment="X",
            outcome="Y",
            identifiable=False,  # from observed-only constraint; see checker wrapper
            notes=(
                "identifiable if U observed; NOT identifiable from {X,Y} alone",
                "models that claim empty-set identification fail",
            ),
            control_claims=(
                _claim("T06", "X", "Y", asserts_identifiable=False, adjustment_set=[]),
                _claim("T06", "X", "Y", asserts_identifiable=True, adjustment_set=[]),
                _claim("T06", "X", "Y", asserts_identifiable=True, adjustment_set=["U"]),
            ),
        )
    )

    # T07: chain with fork — X←Z→M→Y and X→Y. Need Z.
    g7 = CausalDAG.from_edges(
        ["Z", "X", "M", "Y"],
        [("Z", "X"), ("Z", "M"), ("X", "Y"), ("M", "Y")],
    )
    scm7 = BinarySCM(
        g7,
        {
            "Z": bernoulli(Fraction(2, 5)),
            "X": logistic_from_parents({"Z": Fraction(1, 2)}, Fraction(1, 5)),
            "M": logistic_from_parents({"Z": Fraction(1, 3)}, Fraction(1, 4)),
            "Y": logistic_from_parents(
                {"X": Fraction(1, 4), "M": Fraction(1, 4)}, Fraction(1, 8)
            ),
        },
    )
    tasks.append(
        Task(
            task_id="T07",
            title="Fork into mediator and treatment",
            domain="mechanisms-toy",
            prompt=_prompt(
                g7,
                "X",
                "Y",
                "Z confounds X and mediator M; X and M both affect Y. Adjust for Z; do not adjust for M if estimating total effect.",
            ),
            graph=g7,
            scm=scm7,
            treatment="X",
            outcome="Y",
            identifiable=True,
            notes=(
                "{Z} and {M} both valid backdoor sets on this graph; empty invalid",
                "M is not a descendant of X (common cause Z)",
            ),
            control_claims=(
                _claim("T07", "X", "Y", asserts_identifiable=True, adjustment_set=["Z"]),
                _claim("T07", "X", "Y", asserts_identifiable=True, adjustment_set=[]),
                _claim("T07", "X", "Y", asserts_identifiable=True, adjustment_set=["Y"]),
            ),
        )
    )

    # T08: no effect, common cause — association without causation if we wrongly include path.
    # Graph: X←Z→Y, no X→Y. ATE=0. Empty fails; {Z} works and gives 0.
    g8 = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y")])
    scm8 = BinarySCM(
        g8,
        {
            "Z": bernoulli(Fraction(1, 2)),
            "X": logistic_from_parents({"Z": Fraction(3, 5)}, Fraction(1, 10)),
            "Y": logistic_from_parents({"Z": Fraction(3, 5)}, Fraction(1, 10)),
        },
    )
    tasks.append(
        Task(
            task_id="T08",
            title="Association without causation",
            domain="spurious-correlation",
            prompt=_prompt(
                g8,
                "X",
                "Y",
                "X and Y are correlated through Z but X does not cause Y. "
                "Identify P(Y|do(X)). Asserting association equals effect is false.",
            ),
            graph=g8,
            scm=scm8,
            treatment="X",
            outcome="Y",
            identifiable=True,
            notes=("ATE=0; {Z} required; association ≠ 0",),
            control_claims=(
                _claim("T08", "X", "Y", asserts_identifiable=True, adjustment_set=["Z"]),
                _claim("T08", "X", "Y", asserts_identifiable=True, adjustment_set=[]),
                _claim(
                    "T08",
                    "X",
                    "Y",
                    asserts_identifiable=True,
                    adjustment_set=["Z"],
                    asserts_association_equals_effect=True,
                ),
            ),
        )
    )

    # T09: classic front-door — X→M→Y with U→X, U→Y. Backdoor via U not adjustable
    # if U unobserved; front-door via {M} identifies.
    g9 = CausalDAG.from_edges(
        ["U", "X", "M", "Y"],
        [("U", "X"), ("U", "Y"), ("X", "M"), ("M", "Y")],
    )
    scm9 = BinarySCM(
        g9,
        {
            "U": bernoulli(Fraction(1, 2)),
            "X": logistic_from_parents({"U": Fraction(1, 2)}, Fraction(1, 4)),
            "M": logistic_from_parents({"X": Fraction(1, 2)}, Fraction(1, 4)),
            "Y": logistic_from_parents(
                {"M": Fraction(1, 3), "U": Fraction(1, 3)}, Fraction(1, 6)
            ),
        },
    )
    tasks.append(
        Task(
            task_id="T09",
            title="Front-door identification with latent confounder",
            domain="frontdoor",
            prompt=(
                "You are evaluating a causal identification query under an explicit DAG.\n"
                "Variables: M, U, X, Y\n"
                "Directed edges: U->X, U->Y, X->M, M->Y\n"
                "U is a latent confounder of X and Y. Backdoor adjustment that requires U "
                "is unavailable if U is unobserved; the front-door criterion via mediator M "
                "can still identify P(Y|do(X)).\n"
                "Respond with ONLY JSON:\n"
                "{\n"
                '  "treatment": "X",\n'
                '  "outcome": "Y",\n'
                '  "asserts_identifiable": true,\n'
                '  "strategy": "frontdoor",\n'
                '  "adjustment_set": ["M"],\n'
                '  "claimed_p_do": null,\n'
                '  "asserts_association_equals_effect": false\n'
                "}\n"
                "Use strategy \"frontdoor\" and mediators in adjustment_set. "
                "Do not claim backdoor with empty set.\n"
            ),
            graph=g9,
            scm=scm9,
            treatment="X",
            outcome="Y",
            identifiable=True,
            notes=(
                "front-door via {M}",
                "empty backdoor fails due to U",
                "backdoor with {U} would work if U observed",
            ),
            allowed_strategies=("frontdoor", "backdoor"),
            control_claims=(
                _claim(
                    "T09",
                    "X",
                    "Y",
                    asserts_identifiable=True,
                    adjustment_set=["M"],
                    strategy="frontdoor",
                ),
                _claim(
                    "T09",
                    "X",
                    "Y",
                    asserts_identifiable=True,
                    adjustment_set=[],
                    strategy="backdoor",
                ),
                _claim(
                    "T09",
                    "X",
                    "Y",
                    asserts_identifiable=True,
                    adjustment_set=["U"],
                    strategy="frontdoor",
                ),
            ),
        )
    )

    # T10: instrumental variable Z→X→Y with U→X,U→Y. U unobserved → backdoor fails;
    # Z is a valid instrument; Balke–Pearl bounds (typically not point ID).
    g10 = CausalDAG.from_edges(
        ["U", "Z", "X", "Y"],
        [("Z", "X"), ("X", "Y"), ("U", "X"), ("U", "Y")],
    )
    scm10 = BinarySCM(
        g10,
        {
            "U": bernoulli(Fraction(1, 2)),
            "Z": bernoulli(Fraction(1, 2)),
            "X": logistic_from_parents(
                {"Z": Fraction(1, 3), "U": Fraction(1, 3)}, Fraction(1, 6)
            ),
            "Y": logistic_from_parents(
                {"X": Fraction(1, 4), "U": Fraction(1, 3)}, Fraction(1, 8)
            ),
        },
    )
    tasks.append(
        Task(
            task_id="T10",
            title="Instrumental variable with Balke–Pearl bounds",
            domain="instrument",
            prompt=(
                "You are evaluating a causal identification query under an explicit DAG.\n"
                "Variables: U, X, Y, Z\n"
                "Directed edges: U->X, U->Y, X->Y, Z->X\n"
                "U is unobserved. Empty backdoor adjustment fails. Z is a candidate instrument "
                "for the effect of X on Y.\n"
                "Under standard IV assumptions the effect is typically only partially identified; "
                "report asserts_identifiable=false with strategy \"instrument\" and "
                "adjustment_set [\"Z\"] to request Balke–Pearl bounds certification.\n"
                "Respond with ONLY JSON:\n"
                "{\n"
                '  "treatment": "X",\n'
                '  "outcome": "Y",\n'
                '  "asserts_identifiable": false,\n'
                '  "strategy": "instrument",\n'
                '  "adjustment_set": ["Z"],\n'
                '  "claimed_p_do": null,\n'
                '  "asserts_association_equals_effect": false\n'
                "}\n"
            ),
            graph=g10,
            scm=scm10,
            treatment="X",
            outcome="Y",
            identifiable=False,  # not point-identified without U / extra assumptions
            notes=(
                "Z is a valid instrument",
                "Balke–Pearl bounds contain true P(Y|do(X))",
                "backdoor empty fails; backdoor {U} would point-identify if U observed",
            ),
            allowed_strategies=("instrument", "backdoor"),
            control_claims=(
                _claim(
                    "T10",
                    "X",
                    "Y",
                    asserts_identifiable=False,
                    adjustment_set=["Z"],
                    strategy="instrument",
                ),
                _claim(
                    "T10",
                    "X",
                    "Y",
                    asserts_identifiable=True,
                    adjustment_set=[],
                    strategy="backdoor",
                ),
                _claim(
                    "T10",
                    "X",
                    "Y",
                    asserts_identifiable=False,
                    adjustment_set=["U"],
                    strategy="instrument",
                ),
            ),
        )
    )

    # T11: twin-network counterfactual on the Lean confounder SCM.
    # P(Y_{X=1}=1 | X=0) is identified by shared-noise abduction and differs
    # from P(Y=1 | do(X=1)) under confounding — beyond interventional ID alone.
    g11 = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])

    def _pz(_p: Mapping[str, int]) -> Fraction:
        return Fraction(1, 2)

    def _px(p: Mapping[str, int]) -> Fraction:
        return (1 + p.get("Z", 0)) / Fraction(4)

    def _py(p: Mapping[str, int]) -> Fraction:
        return (1 + p.get("X", 0) + 2 * p.get("Z", 0)) / Fraction(8)

    scm11 = BinarySCM(g11, {"Z": _pz, "X": _px, "Y": _py})
    cf_truth = counterfactual_probability(
        scm11, outcome="Y", treatment="X", treatment_value=1, evidence={"X": 0}
    )
    tasks.append(
        Task(
            task_id="T11",
            title="Twin-network counterfactual (CF ≠ do under confounding)",
            domain="counterfactual",
            prompt=(
                "You are evaluating a counterfactual query under an explicit finite SCM.\n"
                "Variables: X, Y, Z\n"
                "Directed edges: Z->X, Z->Y, X->Y\n"
                "Mechanisms (exact rationals):\n"
                "  P(Z=1)=1/2; P(X=1|Z=z)=(1+z)/4; P(Y=1|X=x,Z=z)=(1+x+2z)/8\n"
                "Query: identify P(Y_{do(X=1)}=1 | X=0) via twin-network shared-noise "
                "abduction (not the interventional P(Y|do(X=1)) alone).\n"
                "Respond with ONLY JSON:\n"
                "{\n"
                '  "treatment": "X",\n'
                '  "outcome": "Y",\n'
                '  "asserts_identifiable": true,\n'
                '  "strategy": "counterfactual",\n'
                '  "adjustment_set": [],\n'
                '  "evidence": {"X": 0},\n'
                '  "treatment_value": 1,\n'
                '  "claimed_p_do": "7/20",\n'
                '  "asserts_association_equals_effect": false\n'
                "}\n"
                "Do not report the interventional probability 3/8; the correct "
                "counterfactual given X=0 is 7/20.\n"
            ),
            graph=g11,
            scm=scm11,
            treatment="X",
            outcome="Y",
            identifiable=True,
            notes=(
                f"exact twin-network P(Y_1=1|X=0)={cf_truth.probability}",
                "differs from interventional P(Y|do(X=1))=3/8",
                "consistency: P(Y_1=1|X=1)=P(Y=1|X=1)=5/12",
            ),
            allowed_strategies=("counterfactual",),
            control_claims=(
                _claim(
                    "T11",
                    "X",
                    "Y",
                    asserts_identifiable=True,
                    strategy="counterfactual",
                    evidence={"X": 0},
                    treatment_value=1,
                    claimed_p_do="7/20",
                ),
                _claim(
                    "T11",
                    "X",
                    "Y",
                    asserts_identifiable=True,
                    strategy="counterfactual",
                    evidence={"X": 0},
                    treatment_value=1,
                    claimed_p_do="3/8",  # interventional trap
                ),
                _claim(
                    "T11",
                    "X",
                    "Y",
                    asserts_identifiable=True,
                    strategy="backdoor",
                    adjustment_set=["Z"],
                ),
            ),
        )
    )

    return tuple(tasks)


ALL_TASKS: Tuple[Task, ...] = build_tasks()


def load_tasks(ids: Optional[Sequence[str]] = None) -> Tuple[Task, ...]:
    if ids is None:
        return ALL_TASKS
    wanted = set(ids)
    out = tuple(t for t in ALL_TASKS if t.task_id in wanted)
    missing = wanted - {t.task_id for t in out}
    if missing:
        raise KeyError(f"unknown task ids: {sorted(missing)}")
    return out
