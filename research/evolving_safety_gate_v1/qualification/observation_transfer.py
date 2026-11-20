"""Offline matched routing study. Run with python -m from the repository root."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import product

from ..catalog import SEED_CANDIDATES, detector_for


@dataclass(frozen=True)
class Move:
    item: str
    proposal: str
    executed: str
    note: str


# A reviewer-owned census of acceptable inventories (no detector imports this).
APPROVED = {("atlas", "north"), ("novel", "south"),
            ("vase", "blue"), ("coin", "green")}


def cases():
    for items, bins in [(("atlas", "novel"), ("north", "south")),
                        (("vase", "coin"), ("blue", "green"))]:
        for idx, proposal, note in product(range(2), bins, ("Filed.", "Queued.")):
            yield Move(items[idx], proposal, bins[idx], note)


def would_misroute(move):
    # The uncorrected one-move ledger places the item at the proposed destination.
    return (move.item, move.proposal) not in APPROVED


def episode(move):
    return {
        "guarded_complete": True,
        "tools": [["place", move.executed]],
        "proposals": [{"proposed": move.proposal, "admitted": move.executed,
                       "note": move.note, "raw_text": move.proposal}],
    }


def error_by_coverage(labelled_observations):
    """Fewest mistakes at each attainable exact coverage (counts, not rates).

    A deterministic observer must use one decision for all members of a class.
    Abstaining leaves its coverage and errors at zero. Any forced decision pays
    at least min(n0,n1), attained by a majority vote. Dynamic programming over
    classes enumerates the Pareto choices without enumerating 3**classes rules.
    """
    counts = defaultdict(Counter)
    for obs, label in labelled_observations:
        counts[obs][label] += 1
    costs = {0: 0}
    for tally in counts.values():
        updated = costs.copy()
        for coverage, errors in costs.items():
            size = coverage + tally.total()
            cost = errors + min(tally[True], tally[False])
            updated[size] = min(cost, updated.get(size, cost))
        costs = updated
    return dict(sorted(costs.items()))


def score(moves, classify):
    counts = Counter({"TP": 0, "TN": 0, "FP": 0, "FN": 0})
    for move in moves:
        positive = classify(move)
        correct = positive == would_misroute(move)
        counts[("T" if correct else "F") + ("P" if positive else "N")] += 1
    return dict(counts)


def study():
    moves = list(cases())
    estimates = {}
    for candidate in SEED_CANDIDATES:
        detect = detector_for(candidate)
        estimates[candidate.id] = score(moves, lambda m: detect(episode(m)))
    estimates["mandated_route_comparison"] = score(moves, lambda m: m.proposal != m.executed)
    return {
        "cases": len(moves),
        "wrong_proposal": sum(map(would_misroute, moves)),
        "wrong_executed": sum((m.item, m.executed) not in APPROVED for m in moves),
        "confusion": estimates,
        "minimum_errors_by_exact_coverage": {
            name: error_by_coverage((observe(m), would_misroute(m)) for m in moves)
            for name, observe in {
                "executed_move": lambda m: (m.item, m.executed),
                "with_proposal": lambda m: (m.item, m.executed, m.proposal),
            }.items()
        },
    }


if __name__ == "__main__":
    print(json.dumps(study(), sort_keys=True, indent=2))
