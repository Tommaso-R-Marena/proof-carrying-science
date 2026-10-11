"""Prospectively frozen, public authored mathematics. No evaluation solutions.

Transfer problems reuse mathematical laws across new compositions; they are not
external or secret theorem benchmarks. Separate family probes use unseen laws.
"""
from .language import formalize
from .data import structural_fingerprint


STATEMENTS = [
    ("train", "list_length_append", "list_length", "For all lists of natural numbers xs and ys, the length of (xs appended to ys) equals (the length of xs + the length of ys)."),
    ("train", "list_append_associativity", "list_association", "For all lists of natural numbers xs, ys and zs, ((xs appended to ys) appended to zs) equals (xs appended to (ys appended to zs))."),
    ("train", "successor_congruence", "nat_congruence", "For all natural numbers a and b, if a equals b then the successor of a equals the successor of b."),
    ("train", "arithmetic_nested", "nat_identities", "For all natural numbers n, ((n + 0) * 1) equals n."),
    ("train", "logical_bridge", "logical_chain", "For all propositions A, B and C, if ((A implies B) and (B implies C)) then (A implies C)."),
    ("train", "quantified_bridge", "predicate_chain", "For all predicates on natural numbers P and Q, if ((∀ (n : Nat), P(n) implies Q(n)) and (∀ (m : Nat), P(m))) then (∀ (k : Nat), Q(k))."),
    ("validation", "length_pair", "paired_list_length", "For all lists of natural numbers xs and ys, ((the length of (xs appended to ys) equals (the length of xs + the length of ys)) and (xs appended to the empty list equals xs))."),
    ("validation", "association_pair", "paired_list_association", "For all lists of natural numbers xs, ys and zs, ((((xs appended to ys) appended to zs) equals (xs appended to (ys appended to zs))) and (ys appended to the empty list equals ys))."),
    ("validation", "successor_twice", "iterated_successor", "For all natural numbers a and b, if a equals b then the successor of (the successor of a) equals the successor of (the successor of b)."),
    ("validation", "false_length", "false_list_bound", "For all lists of natural numbers xs, the length of xs equals 0."),
    ("final", "length_under_successor", "successor_list_length", "For all lists of natural numbers xs and ys, the successor of (the length of (xs appended to ys)) equals the successor of (the length of xs + the length of ys)."),
    ("final", "two_inductions", "joint_inductive_laws", "For all lists of natural numbers xs, ys and zs, ((the length of (xs appended to ys) equals (the length of xs + the length of ys)) and (((xs appended to ys) appended to zs) equals (xs appended to (ys appended to zs))))."),
    ("final", "relation_transport", "transported_list_equality", "For all lists of natural numbers xs, ys and zs, if ((xs appended to ys) appended to zs) equals xs then (xs appended to (ys appended to zs)) equals xs."),
    ("final", "arithmetic_bundle", "mixed_nat_bundle", "For all natural numbers a and b, if a equals b then ((the successor of a equals the successor of b) and ((a + 0) * 1 equals b))."),
    ("final", "unseen_reverse", "list_reversal", "For all lists of natural numbers xs, the reversal of (the reversal of xs) equals xs."),
    ("final", "unseen_distributivity", "nat_distributivity", "For all natural numbers a, b and c, a * (b + c) equals ((a * b) + (a * c))."),
    ("final", "false_function", "false_function_equality", "For all functions from natural numbers to natural numbers f and g, (∀ (n : Nat), f(n) equals g(n))."),
    ("final", "false_successor", "false_successor_identity", "For all natural numbers n, the successor of n equals n."),
]


def tasks():
    result = []
    for split, identity, family, statement in STATEMENTS:
        parsed = formalize(statement)
        if parsed["status"] != "supported":
            raise ValueError(f"corpus failed to lower {identity}: {parsed}")
        result.append({"id": identity, "family": family, "split": split,
                       "goal": parsed["candidates"][0]["ir"], "original_statement": statement,
                       "license": "Apache-2.0", "source": "PCS authored public induction benchmark"})
    fingerprints = [structural_fingerprint(t["goal"]) for t in result]
    if len(set(fingerprints)) != len(result): raise ValueError("alpha duplicate across splits")
    families = {s: {t["family"] for t in result if t["split"] == s} for s in ["train", "validation", "final"]}
    if any(families[a] & families[b] for a, b in [("train", "validation"), ("train", "final"), ("validation", "final")]):
        raise ValueError("declared theorem family overlap")
    return result
