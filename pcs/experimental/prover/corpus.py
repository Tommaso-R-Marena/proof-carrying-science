"""Public, authored Apache-2.0 tasks; family partitions frozen before training.

No solutions are attached to validation/final tasks. This is a public research
benchmark, not a secret holdout, an external project or novel mathematics.
"""
from .ir import declaration, var, binary, digest


def tasks():
    p, q, r, s = [var(n) for n in "PQRS"]
    b = binary
    entries = [
        ("train", "identity", ["P"], b("implies", p, p)),
        ("train", "conjunction_swap", ["P", "Q"], b("implies", b("and", p, q), b("and", q, p))),
        ("train", "conjunction_project", ["P", "Q"], b("implies", b("and", p, q), p)),
        ("train", "conjunction_intro", ["P", "Q"], b("implies", p, b("implies", q, b("and", p, q)))),
        ("train", "disjunction_left", ["P", "Q"], b("implies", p, b("or", p, q))),
        ("train", "disjunction_right", ["P", "Q"], b("implies", q, b("or", p, q))),
        ("train", "modus_ponens", ["P", "Q"], b("implies", b("implies", p, q), b("implies", p, q))),
        ("validation", "duplicate", ["P"], b("implies", p, b("and", p, p))),
        ("validation", "weaken", ["P", "Q"], b("implies", p, b("implies", q, p))),
        ("final", "nested_reorder", ["P", "Q", "R"], b("implies", b("and", p, b("and", q, r)), b("and", r, b("and", p, q)))),
        ("final", "compose_implications", ["P", "Q", "R"], b("implies", b("implies", p, q), b("implies", b("implies", q, r), b("implies", p, r)))),
        ("final", "four_assumptions", ["P", "Q", "R", "S"], b("implies", p, b("implies", q, b("implies", r, b("implies", s, b("and", q, s)))))),
        ("final", "missing_assumption", ["P", "Q"], b("implies", p, q)),
    ]
    result = [{"id": name, "family": name, "split": split,
               "goal": declaration(names, body), "license": "Apache-2.0", "source": "PCS authored"}
              for split, name, names, body in entries]
    n, m = var("n"), var("m")
    zero, one = [{"op": "number", "value": i, "type": "Nat"} for i in [0, 1]]
    for split, name, names, body in [
        ("train", "nat_add_zero", ["n"], b("eq", b("add", n, zero), n)),
        ("train", "nat_mul_one", ["n"], b("eq", b("mul", n, one), n)),
        ("train", "nat_add_comm", ["n", "m"], b("eq", b("add", n, m), b("add", m, n))),
        ("validation", "nat_zero_add", ["n"], b("eq", b("add", zero, n), n)),
        ("final", "nat_nested_identity", ["n"], b("eq", b("add", b("mul", n, one), zero), n)),
    ]:
        result.append({"id": name, "family": name, "split": split, "goal": declaration(names, body, "Nat"),
                       "license": "Apache-2.0", "source": "PCS authored"})
    if len({digest(t["goal"]) for t in result}) != len(result):
        raise ValueError("duplicate theorem across partitions")
    return result
