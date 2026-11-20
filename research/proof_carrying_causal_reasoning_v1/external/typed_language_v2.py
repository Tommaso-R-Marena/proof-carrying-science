"""Scope-checked successor to the locked Challenge II population text parser."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, replace
from fractions import Fraction

from ..kernel.d_separation import d_separated
from ..kernel.dag import CausalDAG, GraphError
from . import typed_language as original

VERSION = "pccr-population-text/2"
Unsupported = original.Unsupported
COMPLETE = "the complete causal graph is as follows. "
QUALIFIERS = re.compile(
    r"\b(and|or|nor|not|never|no|without|unless|given|even|under|over|before|after|"
    r"provided|assuming|because|despite|except|but|however|sometimes|always|"
    r"may|might|could|should|must|can|cannot|does|did|would|was|when|while|"
    r"otherwise|perhaps|allegedly|possibly|actually|conditionally|only|if|has|"
    r"affects|causes|cause|randomized|unobserved|isolated|depends|whether)\b"
)


@dataclass(frozen=True)
class Event:
    variable: str
    positive: bool


def event(text):
    name = original._name(text)
    base = name.removeprefix("not ")
    if (
        not base
        or QUALIFIERS.search(base)
        or any(t.endswith("n't") for t in base.split())
    ):
        raise Unsupported("ambiguous_event_or_qualifier")
    return Event(base, name == base)


def _background(text):
    closed = text.startswith((original.CLOSED, COMPLETE))
    if closed:
        text = text.removeprefix(original.CLOSED).removeprefix(COMPLETE)
    edges, isolated, hidden, randomized = set(), set(), set(), set()
    for line in original._sentences(text):
        if re.fullmatch(
            r"the report was printed on (monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            line,
        ):
            continue
        if m := re.fullmatch(r"treatment (.+) was randomized", line):
            randomized.add(event(m[1]).variable)
        elif closed and (
            m := re.fullmatch(r"(.+) is an isolated (?:node|variable)", line)
        ):
            isolated.add(event(m[1]).variable)
        elif closed and (m := re.fullmatch(r"(.+) is unobserved", line)):
            hidden.add(event(m[1]).variable)
        elif closed and (m := re.fullmatch(r"(.+) has a direct effect on (.+)", line)):
            parent = event(m[1]).variable
            for piece in re.split(r", and | and |, ", m[2]):
                edge = parent, event(piece).variable
                if edge in edges:
                    raise Unsupported("duplicate_causal_edge")
                edges.add(edge)
        else:
            raise Unsupported("unsupported_background")
    endpoints = {n for edge in edges for n in edge}
    if len(edges) > 48 or len(endpoints | isolated) > 64 or endpoints & isolated:
        raise Unsupported("invalid_graph")
    if hidden & randomized or any(child in randomized for _, child in edges):
        raise Unsupported("conflicting_randomization")
    nodes = endpoints | isolated
    if closed and (not nodes or not (hidden | randomized) <= nodes):
        raise Unsupported("undeclared_graph_variable")
    try:
        graph = CausalDAG.from_edges(nodes, edges)
    except GraphError as exc:
        raise Unsupported("invalid_graph") from exc
    return closed, graph, hidden, randomized


@dataclass(frozen=True)
class ScopedClaim:
    query: original.Claim
    declared_nodes: tuple[str, ...]
    bindings: tuple[Event, ...]
    closed: bool


def interpret(public):
    if (
        type(public) is not dict
        or set(public) != original.TEXT_FIELDS
        or any(
            type(s) is not str or not s.isascii() or len(s) > 6000
            for s in public.values()
        )
    ):
        raise Unsupported("invalid_public_fields")
    closed, graph, hidden, randomized = _background(
        " ".join(public["background"].lower().split())
    )
    claim = original.interpret({**public, "background": ""})
    named = [claim.outcome]
    if claim.treatment:
        named.append(claim.treatment)
    for f in claim.facts:
        named.append(f.event)
        if f.condition:
            named.append(f.condition)
    for method in claim.methods:
        named.extend(method)
    bindings = tuple(event(name) for name in sorted(set(named)))
    bound = {e.variable for e in bindings}
    if closed and not bound <= graph.nodes:
        raise Unsupported("undeclared_graph_variable")
    if bound & hidden:
        raise Unsupported("unobserved_variable_used")
    if (
        claim.treatment
        and event(claim.treatment).variable == event(claim.outcome).variable
    ):
        raise Unsupported("overlapping_treatment_outcome")
    marginal_variables = [
        event(f.event).variable for f in claim.facts if f.kind == "marginal"
    ]
    if len(marginal_variables) != len(set(marginal_variables)):
        raise Unsupported("duplicate_or_complementary_marginals")
    for fact in claim.facts:
        if (
            fact.condition
            and event(fact.event).variable == event(fact.condition).variable
        ):
            raise Unsupported("overlapping_probability_events")
    assumptions = tuple(
        (["complete_causal_DAG"] if closed else [])
        + ["randomized:" + x for x in sorted(randomized)]
    )
    query = replace(
        claim,
        edges=tuple(sorted(graph.edges)),
        latent=tuple(sorted(hidden)),
        assumptions=assumptions + claim.assumptions,
    )
    return ScopedClaim(query, tuple(sorted(graph.nodes)), bindings, closed)


def _strata(claim):
    variables = {
        event(f.condition).variable
        for f in claim.facts
        if f.kind == "conditional" and f.event == claim.outcome
    }
    return variables.pop() if len(variables) == 1 else None


def decide(scoped):
    claim = scoped.query
    graph = CausalDAG.from_edges(scoped.declared_nodes, claim.edges)
    y = event(claim.outcome).variable
    x = event(claim.treatment).variable if claim.treatment else _strata(claim)
    if x == y:
        raise Unsupported("overlapping_treatment_outcome")
    if claim.kind == "adjustment":
        if not scoped.closed:
            raise Unsupported("complete_graph_required")
        valid = []
        for method in claim.methods:
            z = [event(n).variable for n in method]
            if len(set(z)) != len(z) or {x, y} & set(z):
                raise Unsupported("unavailable_covariate")
            valid.append(original.valid_adjustment(graph, x, y, z))
        if valid[0] == valid[1]:
            raise Unsupported("methods_equally_valid_or_invalid")
        return ("yes" if valid[0] else "no"), None
    independent = scoped.closed and x is not None and d_separated(graph, [x], [y])
    if claim.kind == "intervention":
        if "randomized:" + x not in claim.assumptions and not (
            scoped.closed and original.valid_adjustment(graph, x, y, ())
        ):
            raise Unsupported("exchangeability_unestablished")
        used = [
            f
            for f in claim.facts
            if f.kind != "marginal" or event(f.event).variable in {x, y}
        ]
        if len(used) != 2 or any(f.kind != "conditional" for f in used):
            raise Unsupported("missing_or_extraneous_probability")
        a = original._lookup(used, "conditional", claim.outcome, claim.treatment)
        b = original._lookup(
            used, "conditional", claim.outcome, original._opposite(claim.treatment)
        )
        lo, hi = a[0] - b[1], a[1] - b[0]
    else:
        # Evaluate printed probabilities first; apply the full graph (including
        # explicitly isolated vertices) to this numerical interpretation below.
        lo, hi = original._bounds(replace(claim, edges=()))
    if independent:
        if claim.kind == "marginal":
            arms = [
                f.bounds
                for f in claim.facts
                if f.kind == "conditional" and f.event == claim.outcome
            ]
            low = max(a[0] for a in arms)
            high = min(a[1] for a in arms)
            if low > high:
                raise Unsupported("graph_probability_conflict")
            lo, hi = 2 * low - 1, 2 * high - 1
        else:
            if not lo <= 0 <= hi:
                raise Unsupported("graph_probability_conflict")
            lo = hi = Fraction(0)
    if claim.direction == "decrease":
        lo, hi = -hi, -lo
    return ("yes" if lo > 0 else "no" if hi < 0 else None), [str(lo), str(hi)]


def predict(public):
    claim = None
    try:
        claim = interpret(public)
        prediction, interval = decide(claim)
        reason = (
            "unique_valid_adjustment"
            if claim.query.kind == "adjustment"
            else "strict_rounded_sign"
            if prediction
            else "rounding_or_tie"
        )
    except Unsupported as err:
        prediction, interval, reason = None, None, str(err)
    return {
        "version": VERSION,
        "prediction": prediction,
        "reason": reason,
        "claim": asdict(claim.query) if claim else None,
        "bindings": [asdict(x) for x in claim.bindings] if claim else None,
        "declared_nodes": list(claim.declared_nodes) if claim else None,
        "interval": interval,
    }
