"""Exact finite-state adaptive rerandomization; research-only, not a PCS authority.

Every probabilistic guarantee presumes an externally pinned, outcome-blind
state machine, genuinely implemented by an independent randomization process.
"""
from __future__ import annotations
from functools import lru_cache
from fractions import Fraction
from itertools import combinations, product
import json
from research.evidencekernel_selective_v17.kernel import (
    Reject, insist, exact_keys, digest, load_strict, parse_fraction, effect_stat,
)

FORMAT = "pcs-evidencekernel-finite-state-v21"
POLICY = "registered_finite_state_outcome_blind"
RULE = "first_state_acceptable_else_last"
RANK = "conditional_lex_right_cdf_given_selected_and_stop"
FIELDS = ("format", "n", "k", "baseline_covariate", "max_attempts",
          "initial_state", "candidate_law", "candidate_weights_by_state",
          "reject_next_state", "accept_if_score_le_by_state", "selection_rule",
          "null_ate_upper", "max_interval_misses", "confidence_alpha", "tie_rule")

def design(p):
    exact_keys(p, FIELDS, "finite-state registration")
    insist(p["format"] == FORMAT and p["candidate_law"] == POLICY and
           p["selection_rule"] == RULE and p["tie_rule"] == RANK,
           "unsupported registration")
    n, k, horizon = p["n"], p["k"], p["max_attempts"]
    insist(type(n) is int and 2 <= n <= 8 and type(k) is int and 1 <= k < n,
           "invalid trial size")
    insist(type(horizon) is int and 1 <= horizon <= 64, "invalid horizon")
    x = p["baseline_covariate"]
    insist(type(x) is list and len(x) == n and
           all(type(v) is int and -16 <= v <= 16 for v in x), "invalid baseline")
    K = p["max_interval_misses"]
    insist(type(K) is int and 0 <= K <= n, "invalid interval miss budget")
    alpha, null = parse_fraction(p["confidence_alpha"]), parse_fraction(p["null_ate_upper"])
    insist(0 < alpha < 1 and -1 <= null <= 1, "invalid alpha/null")
    space = list(combinations(range(n), k))
    N = len(space)
    insist(N * 4**n <= 5_000_000, "potential-outcome budget exceeded")
    rows, transitions, cutoffs = (p["candidate_weights_by_state"],
                                  p["reject_next_state"],
                                  p["accept_if_score_le_by_state"])
    states = len(rows) if type(rows) is list else -1
    insist(1 <= states <= 8 and type(transitions) is list and
           len(transitions) == states and type(cutoffs) is list and
           len(cutoffs) == states, "invalid policy states")
    initial = p["initial_state"]
    insist(type(initial) is int and 0 <= initial < states, "invalid initial state")
    probs = []
    for s in range(states):
        row = rows[s]
        next_states = transitions[s]
        cutoff = cutoffs[s]
        insist(type(row) is list and len(row) == N and
               all(type(v) is int and 0 <= v <= 10000 for v in row) and
               sum(row) > 0, "invalid candidate weights")
        insist(type(next_states) is list and len(next_states) == N and
               all(type(v) is int and 0 <= v < states for v in next_states),
               "invalid rejection transitions")
        insist(type(cutoff) is int and 0 <= cutoff <= 10000,
               "invalid acceptance threshold")
        probs.append([Fraction(v, sum(row)) for v in row])
    score = [abs(n * sum(x[i] for i in z) - k * sum(x)) for z in space]
    accepted = [[v <= threshold for v in score] for threshold in cutoffs]
    alive = {initial: Fraction(1)}
    mass = [Fraction(0)] * N
    for t in range(1, horizon + 1):
        follow = {}
        for state, current in alive.items():
            for i, q in enumerate(probs[state]):
                if not q:
                    continue
                contribution = current * q
                if t == horizon or accepted[state][i]:
                    mass[i] += contribution
                else:
                    ns = transitions[state][i]
                    follow[ns] = follow.get(ns, Fraction(0)) + contribution
        alive = follow
    insist(sum(mass) == 1, "selection distribution not normalized")
    insist(all(v.numerator.bit_length() + v.denominator.bit_length() < 65536
               for v in mass), "oversized finite design")
    return dict(n=n, k=k, H=horizon, space=space, N=N, S=states,
                initial=initial, weights=probs, transitions=transitions,
                accepted=accepted, mass=mass, alpha=alpha, null=null, K=K)

def attempt_commitment(protocol_pin, attempts):
    return digest(dict(domain="pcs-evidencekernel-v21-adaptive-attempts",
                       protocol_sha256=protocol_pin, attempts=attempts))

def validate(p, e, d, protocol_pin, attempts_pin):
    for pin in (protocol_pin, attempts_pin):
        insist(type(pin) is str and len(pin) == 64 and
               all(c in "0123456789abcdef" for c in pin), "external pin required")
    insist(digest(p) == protocol_pin, "protocol commitment mismatch")
    exact_keys(e, ("attempts", "selected_assignment", "observed_intervals"), "evidence")
    attempts = e["attempts"]
    labels = e["observed_intervals"]
    insist(type(attempts) is list and 1 <= len(attempts) <= d["H"], "bad attempt count")
    insist(type(labels) is list and len(labels) == d["n"] and
           all(type(v) is str and v in ("0", "1", "01") for v in labels),
           "invalid observation intervals")
    lookup = {z: i for i, z in enumerate(d["space"])}
    state = d["initial"]
    states, ids = [], []
    for j, a in enumerate(attempts):
        insist(type(a) is list and tuple(a) in lookup, "unrecognized candidate")
        idx = lookup[tuple(a)]
        insist(d["weights"][state][idx] > 0, "zero-probability candidate")
        states.append(state)
        ids.append(idx)
        if j < len(attempts) - 1:
            insist(not d["accepted"][state][idx], "concealed prior acceptance")
            state = d["transitions"][state][idx]
        else:
            insist(len(attempts) == d["H"] or d["accepted"][state][idx],
                   "premature termination")
    insist(type(e["selected_assignment"]) is list and
           e["selected_assignment"] == attempts[-1], "terminal allocation mismatch")
    insist(attempt_commitment(protocol_pin, attempts) == attempts_pin,
           "attempt history mismatch")
    return ids, states, labels

def conditional_right_cdf(d, ids):
    """Exact right CDF of lexicographic transcript conditional on (Z=z,T=t)."""
    t, z = len(ids), ids[-1]
    @lru_cache(maxsize=None)
    def suffix(j, state):
        if j == t:
            return (d["weights"][state][z] if
                    (t == d["H"] or d["accepted"][state][z]) else Fraction(0))
        return sum((q * suffix(j + 1, d["transitions"][state][i])
                    for i, q in enumerate(d["weights"][state])
                    if q and not d["accepted"][state][i]), Fraction(0))
    total = suffix(1, d["initial"])
    insist(total > 0, "zero-probability terminal event")
    smaller = Fraction(0)
    prefix = Fraction(1)
    state = d["initial"]
    for j, actual in enumerate(ids[:-1], start=1):
        insist(d["weights"][state][actual] > 0 and
               not d["accepted"][state][actual], "invalid rejected prefix")
        for i, q in enumerate(d["weights"][state][:actual]):
            if q and not d["accepted"][state][i]:
                smaller += prefix * q * suffix(j + 1, d["transitions"][state][i])
        prefix *= d["weights"][state][actual]
        state = d["transitions"][state][actual]
    insist(t == d["H"] or d["accepted"][state][z], "invalid terminal acceptance")
    point = prefix * d["weights"][state][z]
    rank = (smaller + point) / total
    insist(0 < rank <= 1, "invalid transcript CDF")
    return rank, total, point

def audit(p, e, *, protocol_pin, attempts_pin):
    d = design(p)
    ids, states, labels = validate(p, e, d, protocol_pin, attempts_pin)
    u, terminal_event_mass, observed_mass = conditional_right_cdf(d, ids)
    z = d["space"][ids[-1]]
    zset = set(z)
    best = {}
    compatible = 0
    for digits in product(range(4), repeat=d["n"]):
        world = tuple(((v >> 1) & 1, v & 1) for v in digits)
        misses = sum(label != "01" and
                     label != str(world[i][int(i in zset)])
                     for i, label in enumerate(labels))
        if misses > d["K"]:
            continue
        compatible += 1
        ate = sum(b - a for a, b in world)
        statistics = [effect_stat(world, alt, d["n"], d["k"])
                      for alt in d["space"]]
        observed = statistics[ids[-1]]
        above = sum((v for v, t in zip(d["mass"], statistics) if t > observed),
                    Fraction(0))
        equal = sum((v for v, t in zip(d["mass"], statistics) if t == observed),
                    Fraction(0))
        value = above + u * equal
        best[ate] = max(value, best.get(ate, Fraction(-1)))
    insist(compatible > 0, "no compatible potential outcomes")
    curve = []
    peak = Fraction(-1)
    for h in range(-d["n"], d["n"] + 1):
        peak = max(peak, best.get(h, Fraction(-1)))
        curve.append(dict(ate_upper=str(Fraction(h, d["n"])),
                          null_feasible=peak >= 0,
                          max_p=str(peak) if peak >= 0 else None))
    curve[-1]["null_feasible"] = True
    curve[-1]["max_p"] = "1"
    relevant = [v for v in curve if Fraction(v["ate_upper"]) <= d["null"]][-1]
    lower = next((v["ate_upper"] for v in curve if v["null_feasible"] and
                  Fraction(v["max_p"]) > d["alpha"]), None)
    return dict(status=("CONDITIONALLY_VERIFIED" if relevant["null_feasible"]
                        else "INCONSISTENT_NULL"),
                conditional_p=relevant["max_p"], conditional_lower_ate=lower,
                confidence_alpha=str(d["alpha"]), compatible_worlds=compatible,
                design_selected_probability=str(d["mass"][ids[-1]]),
                stop_time=len(ids), state_history=states,
                conditional_rank=str(u),
                conditional_terminal_event_mass=str(terminal_event_mass),
                observed_transcript_mass=str(observed_mass),
                null_curve=curve, protocol_sha256=protocol_pin,
                attempts_sha256=attempts_pin,
                warning="Research-only conditional inference: genuine physical "
                        "randomization, outcome blindness, temporal registration, "
                        "complete custody and calibration remain external premises.")

if __name__ == "__main__":
    import argparse
    pa = argparse.ArgumentParser(description=__doc__)
    pa.add_argument("protocol")
    pa.add_argument("evidence")
    pa.add_argument("--protocol-pin", required=True)
    pa.add_argument("--attempts-pin", required=True)
    args = pa.parse_args()
    try:
        report = audit(load_strict(args.protocol), load_strict(args.evidence),
                       protocol_pin=args.protocol_pin, attempts_pin=args.attempts_pin)
    except (Reject, TypeError, ValueError, KeyError, OSError, OverflowError) as exc:
        pa.exit(2, "REJECTED: " + str(exc) + "\n")
    print(json.dumps(report, sort_keys=True, indent=2))
