"""Empirical accounting, separate from native authorization and kernel proofs."""
from collections import Counter

from research.progress_supervisor_v1.broker import parse_proposal
from research.progress_supervisor_v1.certificate import groups
from research.progress_supervisor_v1.example import model


def classify(state, raw, selected):
    proposal, classification = parse_proposal(raw)
    spec = model()
    outcomes = groups(spec).get((state, proposal), [])
    return dict(proposal=proposal, parsing=classification,
                intervention=proposal != selected,
                malformed=classification == "MALFORMED_FALLBACK",
                forbidden=proposal in spec["forbidden"],
                disabled=not outcomes,
                unsafe_possible=any(t not in spec["safe"] for t in outcomes),
                nonprogress_possible=bool(outcomes) and any(t == state or t == 6 for t in outcomes))


def summarize(episodes):
    counts = Counter()
    for episode in episodes:
        counts["episodes"] += 1
        counts["completed"] += int(episode["final"]["state"] == 4)
        for turn in episode["turns"]:
            counts["proposals"] += 1
            for key in ("intervention", "malformed", "forbidden", "disabled",
                        "unsafe_possible", "nonprogress_possible"):
                counts[key] += int(turn["assessment"][key])
    return {k: counts[k] for k in ("episodes", "completed", "proposals", "intervention",
                                  "malformed", "forbidden", "disabled", "unsafe_possible",
                                  "nonprogress_possible")}


def counterfactual(turns):
    """Replay *these same proposals* against the declared graph without fallback.

    All possible branches are retained. No SQL is executed by this negative
    control, and diverged observations invalidate a causal model-only comparison.
    Thus this is a graph diagnostic, not an ungated deployment experiment.
    """
    spec = model()
    edges = groups(spec)
    states, unsafe, forbidden, disabled = {0}, False, False, False
    for turn in turns:
        action, _ = parse_proposal(bytes.fromhex(turn["proposal_hex"]))
        forbidden |= action in spec["forbidden"]
        next_states = set()
        for state in states:
            targets = edges.get((state, action), [])
            if not targets:
                disabled = True
                next_states.add(state)  # explicit no-effect disabled-action policy
            next_states.update(targets)
        states = next_states
        unsafe |= bool(states-set(spec["safe"]))
    return dict(final_states=sorted(states), all_completed=states == {4},
                unsafe_possible=unsafe, forbidden_requested=forbidden,
                disabled_requested=disabled, effects_executed=False,
                scope="Same proposal sequence, declared graph only; divergent observations not regenerated")
