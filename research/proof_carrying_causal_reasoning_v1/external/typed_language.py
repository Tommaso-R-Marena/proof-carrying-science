"""Population causal questions in a bounded, explicit English fragment.

The source model and the target label do not enter this module. Every sentence
must belong to the fragment. Each probability is a rounded population fact.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from fractions import Fraction as F
from itertools import product

from ..kernel.d_separation import d_separated
from ..kernel.dag import CausalDAG

CLOSED = (
    "imagine a self-contained, hypothetical world with only the following conditions, "
    "and without any unmentioned factors or causal relationships: "
)
NAME = r"[a-z][a-z0-9' -]{0,79}"
PERCENT = r"(0|[1-9][0-9]?|100)%"
TEXT_FIELDS = {"background", "given_info", "question"}


class Unsupported(ValueError):
    """The next operation would require an unsupported semantic assumption."""


@dataclass(frozen=True)
class Fact:
    kind: str  # marginal(event), joint(condition,event), conditional(event|condition)
    event: str
    condition: str | None
    percent: int

    @property
    def bounds(self):
        return max(F(0), F(2 * self.percent - 1, 200)), min(
            F(1), F(2 * self.percent + 1, 200)
        )


@dataclass(frozen=True)
class Claim:
    kind: str
    treatment: str | None
    outcome: str
    direction: str
    arms: tuple[bool, ...]
    assumptions: tuple[str, ...]
    facts: tuple[Fact, ...]
    edges: tuple[tuple[str, str], ...]
    latent: tuple[str, ...]
    methods: tuple[tuple[str, ...], ...]


def _name(s):
    if (
        not re.fullmatch(NAME, s)
        or s != s.strip()
        or re.search(
            r"\b(and|or|except|unless|if|only|rather|possibly|maybe|either|probably|provided|is)\b",
            s,
        )
    ):
        raise Unsupported("ambiguous_variable")
    return s


def _sentences(s):
    if not s:
        return []
    if not s.endswith("."):
        raise Unsupported("incomplete_sentence")
    return re.split(r"\.\s+", s[:-1])


def _background(s):
    closed = s.startswith((CLOSED, "the complete causal graph is as follows. "))
    if closed:
        s = s.removeprefix(CLOSED).removeprefix(
            "the complete causal graph is as follows. "
        )
    edges, latent, randomized = [], [], []
    for line in _sentences(s):
        if re.fullmatch(
            r"the report was printed on (monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            line,
        ):
            continue
        if m := re.fullmatch(r"treatment (.+) was randomized", line):
            randomized.append(_name(m[1]))
        elif closed and (m := re.fullmatch(r"(.+) is unobserved", line)):
            latent.append(_name(m[1]))
        elif closed and (m := re.fullmatch(r"(.+) has a direct effect on (.+)", line)):
            parent = _name(m[1])
            for child in re.split(r", and | and |, ", m[2]):
                edges.append((parent, _name(child)))
        else:
            raise Unsupported("unsupported_background")
    if (
        len(edges) > 48
        or len(set(edges)) != len(edges)
        or len(set(latent)) != len(latent)
    ):
        raise Unsupported("invalid_graph")
    nodes = {v for edge in edges for v in edge}
    if closed:
        if not edges or not set(latent) <= nodes:
            raise Unsupported("incomplete_graph")
        try:
            CausalDAG.from_edges(nodes, edges)
        except ValueError as err:
            raise Unsupported("invalid_graph") from err
    if closed and not set(randomized) <= nodes:
        raise Unsupported("unknown_randomized_variable")
    if any(child in randomized for _, child in edges) or set(latent) & set(randomized):
        raise Unsupported("conflicting_randomization")
    assumptions = (["complete_causal_DAG"] if closed else []) + [
        "randomized:" + name for name in sorted(set(randomized))
    ]
    return tuple(sorted(edges)), tuple(sorted(latent)), tuple(assumptions)


def _group(s):
    for prefix in ("those who are ", "people who are ", "individuals who are "):
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    return _name(s)


def _facts(s):
    facts = []
    for line in _sentences(s):
        if m := re.fullmatch(r"the overall probability of (.+) is " + PERCENT, line):
            fact = Fact("marginal", _name(m[1]), None, int(m[2]))
        elif m := re.fullmatch(r"the probability of (.+) and (.+) is " + PERCENT, line):
            fact = Fact("joint", _name(m[2]), _name(m[1]), int(m[3]))
            if fact.condition == fact.event:
                raise Unsupported("repeated_joint_event")
        elif m := re.fullmatch(
            r"(?:for|among) ([^,]+), the probability of (.+) is " + PERCENT, line
        ):
            fact = Fact("conditional", _name(m[2]), _group(m[1]), int(m[3]))
        else:
            raise Unsupported("unsupported_probability_statement")
        facts.append(fact)
    keys = [(f.kind, f.event, f.condition) for f in facts]
    if len(set(keys)) != len(keys):
        raise Unsupported("duplicate_probability")
    return tuple(facts)


def _method(s, x, y, allow_anaphora):
    prefix = f"we look directly at how {x} correlates with {y} in general"
    if s == prefix:
        return ()
    prefixes = [f"we look at how {x} correlates with {y} case by case according to "]
    if allow_anaphora:
        prefixes.append("we look at this correlation case by case according to ")
    for start in prefixes:
        if s.startswith(start):
            names = [_name(n) for n in re.split(r", and | and |, ", s[len(start) :])]
            if len(set(names)) != len(names):
                raise Unsupported("duplicate_covariate")
            return tuple(sorted(names))
    raise Unsupported("unsupported_comparison_method")


def _opposite(event):
    return event.removeprefix("not ") if event.startswith("not ") else "not " + event


def interpret(public):
    if (
        type(public) is not dict
        or set(public) != TEXT_FIELDS
        or any(
            type(s) is not str or len(s) > 6000 or not s.isascii()
            for s in public.values()
        )
    ):
        raise Unsupported("invalid_public_fields")
    bg, info, q = (
        " ".join(public[k].lower().split())
        for k in ("background", "given_info", "question")
    )
    edges, latent, assumptions = _background(bg)
    x, methods, arms = None, (), ()
    if m := re.fullmatch(
        r"to understand how (.+) affects (.+), is it more correct to use the method 1 than method 2\?",
        q,
    ):
        x, y = _name(m[1]), _name(m[2])
        pair = re.fullmatch(r"method 1: ([^.]+)\. method 2: ([^.]+)\.", info)
        if not pair:
            raise Unsupported("missing_comparison_methods")
        methods = (_method(pair[1], x, y, False), _method(pair[2], x, y, True))
        kind, direction, facts = "adjustment", "first_valid", ()
    else:
        if m := re.fullmatch(r"is (.+) (more|less) likely than (.+) overall\?", q):
            y = _name(m[1])
            if _opposite(y) != _name(m[3]):
                raise Unsupported("unresolved_outcome_complement")
            kind, direction = "marginal", {"more": "increase", "less": "decrease"}[m[2]]
        elif m := re.fullmatch(
            r"is the chance of (.+) (larger|smaller) when observing (.+)\?", q
        ):
            x, y = _name(m[3]), _name(m[1])
            kind, direction = (
                "association",
                {"larger": "increase", "smaller": "decrease"}[m[2]],
            )
        elif m := re.fullmatch(
            r"(?:will (.+?) (increase|decrease) the chance of (.+)|does setting (.+?) to true rather than false (increase|decrease) the probability of (.+))\?",
            q,
        ):
            x, direction, y = m.groups()[:3] if m[1] else m.groups()[3:]
            x, y = _name(x), _name(y)
            kind, arms = "intervention", (True, False)
        else:
            raise Unsupported("unsupported_question")
        facts = _facts(info)
    if x in (y, _opposite(y)):
        raise Unsupported("overlapping_treatment_outcome")
    if kind in ("intervention", "adjustment"):
        assumptions += ("modular_intervention", "consistency", "positive_arm_support")
    if kind != "adjustment":
        assumptions += ("binary_events", "population_probabilities_rounded_to_percent")
    return Claim(
        kind, x, y, direction, arms, assumptions, facts, edges, latent, methods
    )


def _graph(claim):
    return CausalDAG.from_edges({n for p in claim.edges for n in p}, claim.edges)


def valid_adjustment(graph, x, y, z):
    """Complete adjustment criterion for a singleton exposure in a causal DAG."""
    # van der Zander, Liśkiewicz & Textor (2014): test separation in the
    # proper back-door graph and exclude descendants of causal-path vertices.
    path_nodes = graph.descendants(x) & (graph.ancestors(y) | {y})
    forbidden = set(path_nodes)
    for v in path_nodes:
        forbidden.update(graph.descendants(v))
    if forbidden.intersection(z):
        return False
    backdoor = CausalDAG.from_edges(
        graph.nodes,
        [(u, v) for u, v in graph.edges if not (u == x and v in path_nodes)],
    )
    return d_separated(backdoor, [x], [y], z)


def _adjustment(claim):
    graph = _graph(claim)
    x, y = claim.treatment, claim.outcome
    if not {x, y} <= graph.nodes or {x, y} & set(claim.latent):
        raise Unsupported("unresolved_graph_endpoints")
    verdicts = []
    for z in claim.methods:
        if not set(z) <= graph.nodes or set(z) & ({x, y} | set(claim.latent)):
            raise Unsupported("unavailable_covariate")
        verdicts.append(valid_adjustment(graph, x, y, z))
    if verdicts[0] == verdicts[1]:
        raise Unsupported("methods_equally_valid_or_invalid")
    return "yes" if verdicts[0] else "no"


def _lookup(facts, kind, event, condition=None):
    for f in facts:
        if f.kind == kind and (f.event, f.condition) == (event, condition):
            return f.bounds
        if (
            kind == "joint"
            and f.kind == kind
            and (f.event, f.condition) == (condition, event)
        ):
            return f.bounds
    raise Unsupported("missing_probability")


def _bounds(claim):
    x, y, facts = claim.treatment, claim.outcome, claim.facts
    # Only disjoint, explicitly marginal distractors can be discarded. A
    # second law for the same quantity could contradict the purported model.
    if y in claim.latent or _opposite(y) in claim.latent:
        raise Unsupported("unobserved_probability")
    if claim.kind == "marginal":
        if len(facts) == 1 and facts[0].kind == "marginal" and facts[0].event == y:
            lo, hi = facts[0].bounds
            return 2 * lo - 1, 2 * hi - 1
        strata = {
            f.condition for f in facts if f.kind == "conditional" and f.event == y
        }
        candidates = {
            f.event
            for f in facts
            if f.kind == "marginal" and {f.event, _opposite(f.event)} == strata
        }
        if len(candidates) != 1:
            raise Unsupported("unresolved_binary_strata")
        x = candidates.pop()
        if x in (y, _opposite(y)):
            raise Unsupported("overlapping_stratum_outcome")
    graph = _graph(claim)
    endpoints = [event.removeprefix("not ") for event in (x, y)]
    independent = set(endpoints) <= graph.nodes and d_separated(
        graph, endpoints[:1], endpoints[1:]
    )
    if {x, y, _opposite(x), _opposite(y)} & set(claim.latent):
        raise Unsupported("unobserved_probability")
    relevant = {x, y, _opposite(x), _opposite(y)}
    records = [f for f in facts if f.kind != "marginal" or f.event in relevant]
    if any(
        f.kind == "marginal"
        and _opposite(f.event)
        in {other.event for other in facts if other.kind == "marginal"}
        for f in facts
    ):
        raise Unsupported("redundant_complement_laws")
    if claim.kind == "association":
        if len(records) != 3:
            raise Unsupported("missing_or_extraneous_probability")
        p = _lookup(records, "marginal", x)
        a = _lookup(records, "joint", y, x)
        b = _lookup(records, "joint", y, _opposite(x))
        # a<=p and b<=1-p. For fixed feasible p, a/p-b/(1-p)
        # increases in a and decreases in b. Each conditional extremum
        # decreases with p, including when a or b saturates its arm.
        pmin, pmax = max(p[0], a[0]), min(p[1], 1 - b[0])
        if pmin > pmax:
            raise Unsupported("inconsistent_probability_table")
        if pmin == 0 or pmax == 1:
            raise Unsupported("positivity_unresolved")
        lo = a[0] / pmax - min(b[1], 1 - pmax) / (1 - pmax)
        hi = min(a[1], pmin) / pmin - b[0] / (1 - pmin)
        if independent:
            if not lo <= 0 <= hi:
                raise Unsupported("graph_probability_conflict")
            return F(0), F(0)
        return lo, hi

    a = _lookup(records, "conditional", y, x)
    b = _lookup(records, "conditional", y, _opposite(x))
    if independent:
        common = max(a[0], b[0]), min(a[1], b[1])
        if common[0] > common[1]:
            raise Unsupported("graph_probability_conflict")
        a = b = common
    if claim.kind == "marginal":
        if len(records) != 3:
            raise Unsupported("missing_or_extraneous_probability")
        p = _lookup(records, "marginal", x)
        values = [2 * (w * u + (1 - w) * v) - 1 for w, u, v in product(p, a, b)]
        return min(values), max(values)
    if len(records) != 2:
        raise Unsupported("missing_or_extraneous_probability")
    if "randomized:" + x not in claim.assumptions:
        graph = _graph(claim)
        if not {x, y} <= graph.nodes or not valid_adjustment(graph, x, y, ()):
            raise Unsupported("exchangeability_unestablished")
    return (F(0), F(0)) if independent else (a[0] - b[1], a[1] - b[0])


def decide(claim):
    if claim.kind == "adjustment":
        return _adjustment(claim), None
    lo, hi = _bounds(claim)
    if claim.direction == "decrease":
        lo, hi = -hi, -lo
    prediction = "yes" if lo > 0 else ("no" if hi < 0 else None)
    return prediction, [str(lo), str(hi)]


def predict(public):
    claim = None
    try:
        claim = interpret(public)
        answer, interval = decide(claim)
        reason = "strict_rounded_sign" if answer else "rounding_or_tie"
        if claim.kind == "adjustment":
            reason = "unique_valid_adjustment"
    except Unsupported as err:
        answer, reason, interval = None, str(err), None
    return {
        "prediction": answer,
        "reason": reason,
        "claim": asdict(claim) if claim else None,
        "interval": interval,
    }
