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
from typing import FrozenSet, List, Optional, Sequence, Tuple

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
) -> CausalClaim:
    return CausalClaim(
        task_id=task_id,
        treatment=treatment,
        outcome=outcome,
        asserts_identifiable=asserts_identifiable,
        adjustment_set=frozenset(adjustment_set),
        claimed_p_do=claimed_p_do,
        asserts_association_equals_effect=asserts_association_equals_effect,
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
