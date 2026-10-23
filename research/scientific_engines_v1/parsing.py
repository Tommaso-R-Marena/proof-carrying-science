"""Bounded strict input contract. No coercion, executable metadata or fuzzy numbers."""

import itertools, json, math, re
from fractions import Fraction
from pcs.jsonio import strict_json_loads
from .vendor.prism.python.prism import serialize as ps

MAX_BYTES = 8 * 1024 * 1024
MAX_EVIDENCE_BYTES = 4 * MAX_BYTES + 1024 * 1024


def load(raw, *, evidence=False):
    if type(raw) is not bytes or len(raw) > (
        MAX_EVIDENCE_BYTES if evidence else MAX_BYTES
    ):
        raise ValueError("Bounded immutable input bytes required")
    try:
        d = strict_json_loads(raw.decode("utf-8"))
    except RecursionError as e:
        raise ValueError("Input nesting budget") from e
    # Bound nesting before invoking recursive upstream schema code.
    stack = [(d, 0, None)]
    nodes = 0
    while stack:
        v, depth, field = stack.pop()
        nodes += 1
        if depth > 64 or nodes > 150000:
            raise ValueError("Input structure budget")
        if type(v) is dict:
            if any(len(k) > 4096 for k in v):
                raise ValueError("Key budget")
            stack.extend(
                (x, depth + 1, k if depth == 0 else None) for k, x in v.items()
            )
        elif type(v) is list:
            stack.extend((x, depth + 1, None) for x in v)
        elif type(v) not in {str, int, bool, type(None)}:
            raise ValueError("No floating point numbers")
        limit = (
            2 * MAX_BYTES
            if evidence and field in {"input_hex", "certificate_hex"}
            else 4096
        )
        if type(v) is str and len(v) > limit:
            raise ValueError("String budget")
        if type(v) is int and v.bit_length() > 4096:
            raise ValueError("Integer budget")
    return d


def exact(d, required, optional=()):
    if (
        type(d) is not dict
        or not set(required) <= set(d)
        or not set(d) <= set(required) | set(optional)
    ):
        raise ValueError("Exact schema fields required")


def nat(x, limit):
    if type(x) is not int or not 0 <= x <= limit:
        raise ValueError("Exact bounded natural required")
    return x


def text(x):
    if type(x) is not str:
        raise ValueError("Text required")
    return x


def rational(x):
    if (
        type(x) is not str
        or len(x) > 4096
        or re.fullmatch(r"-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?", x) is None
    ):
        raise ValueError("Canonical rational string required")
    q = Fraction(x)
    if str(q) != x:
        raise ValueError("Canonical reduced rational required")
    return q


def prism(raw):
    d = load(raw)
    exact(
        d,
        {"schema", "name", "models", "experiments", "query"},
        {"description", "assumptions", "data", "tolerance"},
    )
    text(d["name"])
    text(d.get("description", ""))
    for key in ["models", "experiments", "assumptions", "data"]:
        if type(d.get(key, [])) is not list:
            raise ValueError("Exact list required: " + key)
    rational(d.get("tolerance", "0"))
    for e in d["experiments"]:
        exact(e, {"id", "cost", "outcomes"})
        rational(e["cost"])
    for m in d["models"]:
        exact(m, {"id", "obs", "q"})
        rational(m["q"])
    exact(d["query"], {"id"}, {"description"})
    text(d["query"].get("description", ""))
    seen = set()
    for a in d.get("assumptions", []):
        exact(a, {"id", "holds"}, {"description"})
        text(a.get("description", ""))
        text(a["id"])
        if type(a["holds"]) is not list or any(type(m) is not str for m in a["holds"]):
            raise ValueError("Model reference list required")
        if a["id"] in seen or len(a["holds"]) != len(set(a["holds"])):
            raise ValueError("Duplicate assumption or model reference")
        seen.add(a["id"])
    for v in d.get("data", []):
        exact(v, {"experiment", "outcome"})
    spec = ps.parse_problem(d)
    if spec.P.n > 4096 or spec.P.k > 32:
        raise ValueError("PCS finite-engine resource budget")
    return spec


def prism_certificate(raw):
    d = load(raw)
    exact(
        d, {"schema", "problem_sha256", "kind", "bound", "core", "policy", "adversary"}
    )
    rational(d["bound"])
    if type(d["adversary"]) is not list:
        raise ValueError("Adversary list required")
    for row in d["adversary"]:
        exact(row, {"models", "lb"})
        rational(row["lb"])
    return d


def aion(raw):
    d = load(raw)
    exact(
        d, {"format", "model", "target", "taboo_zero", "x0", "upper", "lower", "claim"}
    )
    if d["format"] != "AION-sandwich-1":
        raise ValueError("Unsupported certificate version")
    model = d["model"]
    exact(model, {"species", "reactions"})
    if (
        type(model["species"]) is not list
        or not 1 <= len(model["species"]) <= 4
        or any(type(s) is not str for s in model["species"])
        or len(set(model["species"])) != len(model["species"])
    ):
        raise ValueError("Unique species required")
    dim = len(model["species"])
    rx = model["reactions"]
    if type(rx) is not list or not 1 <= len(rx) <= 32:
        raise ValueError("Reaction budget")

    def vector(v, limit):
        if type(v) is not list or len(v) != dim:
            raise ValueError("Exact vector dimension")
        return [nat(x, limit) for x in v]

    for r in rx:
        exact(r, {"inp", "out", "k"}, {"name"})
        text(r.get("name", ""))
        vector(r["inp"], 8)
        vector(r["out"], 8)
        if rational(r["k"]) < 0:
            raise ValueError("Negative rate")
    target = d["target"]
    exact(target, {"species", "level"})
    j = nat(target["species"], dim - 1)
    level = nat(target["level"], 10000)
    if level == 0:
        raise ValueError("Positive target level required")
    vector(d["x0"], 10000)
    if (
        type(d["taboo_zero"]) is not list
        or len(d["taboo_zero"]) != dim
        or any(type(v) is not bool for v in d["taboo_zero"])
    ):
        raise ValueError("Exact Boolean taboo vector")

    def table(t, box):
        if type(t) is not dict:
            raise ValueError("Exact table object required")
        keys = {
            ",".join(map(str, x)) for x in itertools.product(*(range(b) for b in box))
        }
        if set(t) != keys:
            raise ValueError("Exactly one canonical entry per core state required")
        for v in t.values():
            q = rational(v)
            if q.denominator & (q.denominator - 1):
                raise ValueError("Dyadic table required by proved emitter")

    for side in ["upper", "lower"]:
        c = d[side]
        exact(c, {"box", "C", "rho", "table"} if side == "upper" else {"box", "F", "V"})
        box = vector(c["box"], 10000)
        if any(b == 0 for b in box) or math.prod(box) > 10000 or box[j] < level:
            raise ValueError("Finite core budget and target coverage required")
        if side == "upper":
            if rational(c["C"]) <= 0:
                raise ValueError("Positive tail coefficient")
            if (
                type(c["rho"]) is not list
                or len(c["rho"]) != dim
                or any(rational(v) < 1 for v in c["rho"])
            ):
                raise ValueError("Tail ratio contract")
            table(c["table"], box)
        else:
            table(c["F"], box)
            table(c["V"], box)
    exact(d["claim"], {"lower", "upper"})
    lo = rational(d["claim"]["lower"])
    hi = rational(d["claim"]["upper"])
    if not 0 <= lo <= hi <= 1:
        raise ValueError("Probability interval must lie in [0,1]")
    return d


def encode(d):
    return json.dumps(
        d, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
