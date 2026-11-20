"""Issue a numerical sign only after constructing a compatible binary Markov model."""

import itertools
from collections import deque
from fractions import Fraction as F

from ..kernel.dag import CausalDAG
from ..kernel.scm import BinarySCM
from . import typed_language_v2 as scope

VERSION = "pccr-population-text/2.1"
Unsupported = scope.Unsupported


def _mid(bounds):
    return sum(bounds, F(0)) / 2


def _path(graph, start, finish):
    queue = deque([(start,)])
    seen = {start}
    while queue:
        path = queue.popleft()
        if path[-1] == finish:
            return path
        for child in sorted(graph.children(path[-1])):
            if child not in seen:
                seen.add(child)
                queue.append((*path, child))
    raise Unsupported("missing_witness_path")


def _empirical_joint(claim, xevent, independent):
    """Cell masses in the actual (unsigned) binary variables, indexed (x,y)."""
    x, y = scope.event(xevent), scope.event(claim.outcome)
    opp = scope.original._opposite(xevent)
    rate = lambda kind, e, c=None: scope.original._lookup(claim.facts, kind, e, c)
    if claim.kind == "association":
        w, a, b = (
            rate("marginal", xevent),
            rate("joint", claim.outcome, xevent),
            rate("joint", claim.outcome, opp),
        )
        w = _mid((max(w[0], a[0]), min(w[1], 1 - b[0])))
        if not 0 < w < 1:
            raise Unsupported("positivity_unresolved")
        a, b = _mid((a[0], min(a[1], w))), _mid((b[0], min(b[1], 1 - w)))
    else:
        w = F(1, 2) if claim.kind == "intervention" else _mid(rate("marginal", xevent))
        a, b = (
            rate("conditional", claim.outcome, xevent),
            rate("conditional", claim.outcome, opp),
        )
        if independent:
            a = b = _mid((max(a[0], b[0]), min(a[1], b[1])))
        else:
            a, b = _mid(a), _mid(b)
        a, b = w * a, (1 - w) * b
    signed = {(1, 1): a, (1, 0): w - a, (0, 1): b, (0, 0): 1 - w - b}
    return {
        (i if x.positive else 1 - i, j if y.positive else 1 - j): v
        for (i, j), v in signed.items()
    }


def _make_witness(scoped):
    claim = scoped.query
    y = scope.event(claim.outcome).variable
    xevent = claim.treatment
    if xevent is None and any(f.kind == "conditional" for f in claim.facts):
        strata = {f.condition for f in claim.facts if f.kind == "conditional"}
        candidates = [
            f.event
            for f in claim.facts
            if f.kind == "marginal"
            and {f.event, scope.original._opposite(f.event)} == strata
        ]
        if len(candidates) != 1:
            raise Unsupported("unresolved_binary_strata")
        xevent = candidates[0]
    x = scope.event(xevent).variable if xevent else None
    active = {y} | ({x} if x else set())
    if {e.variable for e in scoped.bindings} != active:
        raise Unsupported("additional_probability_constraints")
    randomized = {
        a.removeprefix("randomized:")
        for a in claim.assumptions
        if a.startswith("randomized:")
    }
    if not scoped.closed and randomized - {x}:
        raise Unsupported("unsupported_randomization_scope")
    graph = (
        CausalDAG.from_edges(scoped.declared_nodes, claim.edges)
        if scoped.closed
        else CausalDAG.from_edges(active, [(x, y)] if x else [])
    )
    # Unlisted dependencies in the source DAG may have zero influence in a
    # Markov-compatible model. Every unused source vertex gets a fair mechanism.
    tables = {v: (None, (F(1, 2),)) for v in graph.nodes}
    if not x:
        value = _mid(scope.original._lookup(claim.facts, "marginal", claim.outcome))
        tables[y] = (
            None,
            (value if scope.event(claim.outcome).positive else 1 - value,),
        )
    else:
        common = (graph.ancestors(x) | {x}) & (graph.ancestors(y) | {y})
        cell = _empirical_joint(claim, xevent, not common)
        if not common:
            tables[x] = (None, (sum(v for (i, j), v in cell.items() if i),))
            tables[y] = (None, (sum(v for (i, j), v in cell.items() if j),))
        else:
            ancestor = next(
                n for n in reversed(graph.topological_order()) if n in common
            )
            if ancestor == y:
                x, y = y, x
                cell = {(j, i): v for (i, j), v in cell.items()}
            first, second = _path(graph, ancestor, x), _path(graph, ancestor, y)
            if set(first) & set(second) != {ancestor}:
                raise Unsupported("non_disjoint_witness_paths")
            marginal = [
                sum(v for (i, j), v in cell.items() if i == bit) for bit in (0, 1)
            ]
            tables[ancestor] = (None, (marginal[1],))
            for path in (first, second):
                for parent, node in itertools.pairwise(path):
                    tables[node] = (parent, (F(0), F(1)))
            tables[y] = (
                second[-2],
                tuple(
                    cell[(i, 1)] / marginal[i] if marginal[i] else F(1, 2)
                    for i in (0, 1)
                ),
            )
    return [
        {"node": n, "parent": parent, "p1": [str(v) for v in rates]}
        for n, (parent, rates) in sorted(tables.items())
    ]


def verify_model(scoped, rows):
    """Replay the proposed mechanisms against every typed probability sentence."""
    try:
        claim = scoped.query
        if (
            type(rows) is not list
            or len(rows) > 64
            or any(
                type(r) is not dict
                or set(r) != {"node", "parent", "p1"}
                or type(r["node"]) is not str
                or (r["parent"] is not None and type(r["parent"]) is not str)
                or type(r["p1"]) is not list
                or len(r["p1"]) > 2
                or any(type(s) is not str or len(s) > 128 for s in r["p1"])
                for r in rows
            )
        ):
            return False
        names = [row["node"] for row in rows]
        expected = (
            set(scoped.declared_nodes)
            if scoped.closed
            else {e.variable for e in scoped.bindings}
        )
        if len(names) != len(set(names)) or set(names) != expected:
            return False
        randomized = {
            a.removeprefix("randomized:")
            for a in claim.assumptions
            if a.startswith("randomized:")
        }
        edges = []
        mechanisms = {}
        for row in rows:
            n, p = row["node"], row["parent"]
            values = tuple(F(s) for s in row["p1"])
            if (
                [str(v) for v in values] != row["p1"]
                or len(values) != (1 if p is None else 2)
                or any(not 0 <= v <= 1 for v in values)
            ):
                return False
            if p is not None:
                if n in randomized or (scoped.closed and (p, n) not in claim.edges):
                    return False
                edges.append((p, n))
            mechanisms[n] = lambda env, p=p, values=values: (
                values[env[p]] if p is not None else values[0]
            )
        model = BinarySCM(CausalDAG.from_edges(names, edges), mechanisms)

        def assignment(term):
            e = scope.event(term)
            return {e.variable: int(e.positive)}

        for f in claim.facts:
            outcomes = assignment(f.event)
            cond = assignment(f.condition) if f.condition else {}
            numerator = model.p_obs(outcomes | cond)
            denominator = model.p_obs(cond) if f.kind == "conditional" else F(1)
            low, high = f.bounds
            if (
                denominator <= 0
                or not low * denominator <= numerator <= high * denominator
            ):
                return False
        if claim.kind == "intervention":
            exposure = scope.event(claim.treatment).variable
            if any(model.p_obs({exposure: i}) <= 0 for i in (0, 1)):
                return False
        return True
    except (ValueError, TypeError, KeyError, ZeroDivisionError):
        return False


def predict(public):
    result = scope.predict(public)
    result["version"] = VERSION
    result["feasibility_witness"] = None
    if result["prediction"] is None or result["claim"]["kind"] == "adjustment":
        return result
    try:
        scoped = scope.interpret(public)
        rows = _make_witness(scoped)
        if not verify_model(scoped, rows):
            raise Unsupported("no_checked_feasibility_witness")
        result["feasibility_witness"] = rows
    except Unsupported as err:
        result.update(prediction=None, interval=None, reason=str(err))
    return result
