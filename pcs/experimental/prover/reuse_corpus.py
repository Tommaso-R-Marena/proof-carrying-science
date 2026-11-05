"""Frozen mathematical reuse benchmark; no validation/final proof scripts.

Partitions use distinct compositions and quantifier structures. The elementary
results are authored, public and correlated, not external or secret benchmarks.
"""
from .corpus import tasks
from .data import structural_fingerprint
from .language import formalize


def benchmark():
    foundation_ids = {"conjunction_swap", "conjunction_project", "conjunction_intro",
                      "function_injective_composition", "nat_add_comm", "modus_ponens"}
    foundations = [{**t, "role": "library_foundation"} for t in tasks() if t["id"] in foundation_ids]
    statements = [
        ("train", "nested_pair_swap", "For all propositions A, B and C, if ((A and B) and C) then (C and (A and B))."),
        ("train", "pair_of_implications", "For all propositions A, B and C, if ((A implies B) and (B implies C)) then ((B implies C) and (A implies B))."),
        ("train", "predicate_pair_swap", "For all predicates on natural numbers P and Q, if ((∀ (n : Nat), P(n)) and (∀ (m : Nat), Q(m))) then ((∀ (k : Nat), Q(k)) and (∀ (j : Nat), P(j)))."),
        ("train", "integer_equality_pair", "For all integers x, y and z, if ((x equals y) and (y equals z)) then ((y equals z) and (x equals y))."),
        ("train", "nat_witness", "For all natural numbers n, there exists a natural number m such that m equals n."),
        ("train", "pair_projection_composed", "For all propositions A, B and C, if ((A and B) and C) then (A and B)."),
        ("validation", "universal_pair_reverse", "For all predicates on natural numbers P and Q, if ((∀ (a : Nat), P(a) implies Q(a)) and (∀ (b : Nat), Q(b) implies P(b))) then ((∀ (c : Nat), Q(c) implies P(c)) and (∀ (d : Nat), P(d) implies Q(d)))."),
        ("validation", "integer_witness", "For all integers z, there exists an integer w such that w equals z."),
        ("validation", "nested_right_projection", "For all propositions A, B and C, if (A and (B and C)) then (B and C)."),
        ("final", "predicate_implication_exchange", "For all predicates on natural numbers P, Q and R, if ((∀ (a : Nat), P(a) implies Q(a)) and (∀ (b : Nat), Q(b) implies R(b))) then ((∀ (c : Nat), Q(c) implies R(c)) and (∀ (d : Nat), P(d) implies Q(d)))."),
        ("final", "arithmetic_relation_exchange", "For all natural numbers a, b and c, if ((a + b equals c) and (c * 1 equals c)) then ((c * 1 equals c) and (a + b equals c))."),
        ("final", "existential_relation_exchange", "For all natural numbers a, if ((∃ (b : Nat), a equals b) and (∀ (c : Nat), c + 0 equals c)) then ((∀ (d : Nat), d + 0 equals d) and (∃ (e : Nat), a equals e))."),
        ("final", "functional_relation_exchange", "For all functions from natural numbers to natural numbers f and g, if ((∀ (a : Nat), f(a) equals g(a)) and (∀ (b : Nat), g(b) equals f(b))) then ((∀ (c : Nat), g(c) equals f(c)) and (∀ (d : Nat), f(d) equals g(d)))."),
        ("final", "quantified_projection", "For all predicates on natural numbers P and Q, if ((∀ (a : Nat), P(a) implies Q(a)) and (∀ (b : Nat), P(b))) then (∀ (c : Nat), P(c) implies Q(c))."),
        ("final", "quantified_witness", "For all natural numbers n, there exists a natural number m such that (m equals n and m + 0 equals n)."),
        ("final", "missing_premise", "For all predicates on natural numbers P and Q, if (∀ (n : Nat), P(n)) then (∀ (m : Nat), Q(m))."),
        ("final", "wrong_quantifier", "For all natural numbers n, there exists a natural number m such that (∀ (k : Nat), k equals m)."),
    ]
    result = []
    for split, name, statement in statements:
        parsed = formalize(statement)
        if parsed["status"] != "supported":
            raise ValueError("benchmark statement does not lower: " + name + " " + str(parsed))
        result.append({"id": name, "family": name, "split": split,
                       "goal": parsed["candidates"][0]["ir"], "original_statement": statement,
                       "license": "Apache-2.0", "source": "PCS authored", "role": "transfer_problem"})
    fingerprints = [structural_fingerprint(t["goal"]) for t in foundations + result]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("alpha duplicate in benchmark partitions")
    return foundations, result
