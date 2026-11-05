"""Canonical, versioned, validated serialization of PRISM problems and certificates.

Schemas: `prism-problem/1`, `prism-certificate/1` (documented in
docs/TRUST_BOUNDARIES.md).  Parsing is strict: duplicate JSON keys, NaN/Infinity,
non-canonical rationals, unknown identifiers, negative costs, undeclared outcomes,
missing observations, oversize inputs and over-deep policies are all rejected
with an explicit `SchemaError`.  Certificates are bound to a problem by the
SHA-256 of the problem's canonical encoding.
"""
from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction
from math import gcd
from typing import Any, Dict, List

from .core import Problem, bits

PROBLEM_SCHEMA = "prism-problem/1"
CERT_SCHEMA = "prism-certificate/1"

MAX_BYTES = 64 * 1024 * 1024
MAX_MODELS = 1 << 20
MAX_EXPERIMENTS = 4096
MAX_OUTCOMES = 4096
MAX_POLICY_NODES = 1 << 22
MAX_RAT_DIGITS = 4096
_RAT = re.compile(r"^-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?$")
_ID = re.compile(r"^[A-Za-z0-9_.:\-+=()\[\]<>|^*/,]{1,200}$")


class SchemaError(ValueError):
    pass


# ----------------------------------------------------------------- rationals
def rat_to_str(x: Fraction) -> str:
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def str_to_rat(s: Any) -> Fraction:
    if not isinstance(s, str) or len(s) > MAX_RAT_DIGITS or not _RAT.match(s):
        raise SchemaError(f"non-canonical rational: {s!r}")
    if "/" in s:
        a, b = s.split("/")
        a, b = int(a), int(b)
        if b == 1 or gcd(abs(a), b) != 1:
            raise SchemaError(f"rational not in lowest terms: {s!r}")
        if a == 0:
            raise SchemaError("zero must be written as '0'")
        return Fraction(a, b)
    if s == "-0":
        raise SchemaError("'-0' is not canonical")
    return Fraction(int(s))


# ------------------------------------------------------------------ parsing
def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise SchemaError(f"duplicate JSON key {k!r}")
        d[k] = v
    return d


def _bad_const(c):
    raise SchemaError(f"forbidden JSON constant {c}")


def loads(data: bytes) -> Any:
    if len(data) > MAX_BYTES:
        raise SchemaError("input exceeds size limit")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as ex:
        raise SchemaError("input is not UTF-8") from ex
    try:
        return json.loads(text, object_pairs_hook=_no_dupes, parse_constant=_bad_const)
    except json.JSONDecodeError as ex:
        raise SchemaError(f"malformed JSON: {ex}") from ex


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def _req(d, key, typ):
    if not isinstance(d, dict) or key not in d:
        raise SchemaError(f"missing field {key!r}")
    v = d[key]
    if not isinstance(v, typ) or (typ is int and isinstance(v, bool)):
        raise SchemaError(f"field {key!r} has wrong type")
    return v


def _ident(s):
    if not isinstance(s, str) or not _ID.match(s):
        raise SchemaError(f"invalid identifier {s!r}")
    return s


class Spec:
    """A validated problem specification: Problem + assumptions + data + tolerance."""

    def __init__(self, raw: Dict, problem: Problem, assumptions: List[Dict], data: List,
                 eps: Fraction):
        self.raw = raw
        self.P = problem
        self.assumptions = assumptions  # [{"id","description","mask"}]
        self.data = data                # [(e, o)]
        self.eps = eps
        self.hash = sha256(raw)

    def version_space(self, extra_data=()) -> int:
        P = self.P
        K = P.full
        for a in self.assumptions:
            K &= a["mask"]
        for (e, o) in list(self.data) + list(extra_data):
            K &= P.cellmask[e][o]
        return K


def parse_problem(raw: Any) -> Spec:
    if not isinstance(raw, dict):
        raise SchemaError("problem must be a JSON object")
    allowed = {"schema", "name", "description", "models", "experiments", "query",
               "assumptions", "data", "tolerance"}
    extra = set(raw) - allowed
    if extra:
        raise SchemaError(f"unknown top-level fields {sorted(extra)}")
    if raw.get("schema") != PROBLEM_SCHEMA:
        raise SchemaError("unsupported or missing schema version")
    _req(raw, "name", str)
    exps = _req(raw, "experiments", list)
    models = _req(raw, "models", list)
    if not (1 <= len(models) <= MAX_MODELS):
        raise SchemaError("model count out of range (must be nonempty and bounded)")
    if len(exps) > MAX_EXPERIMENTS:
        raise SchemaError("too many experiments")
    exp_ids, outcomes, costs = [], [], []
    for x in exps:
        eid = _ident(_req(x, "id", str))
        if eid in exp_ids:
            raise SchemaError(f"duplicate experiment id {eid!r}")
        exp_ids.append(eid)
        c = str_to_rat(_req(x, "cost", str))
        if c < 0:
            raise SchemaError(f"negative cost for experiment {eid!r}")
        costs.append(c)
        outs = _req(x, "outcomes", list)
        if not (1 <= len(outs) <= MAX_OUTCOMES):
            raise SchemaError("outcome list size out of range")
        outs = [_ident(o) for o in outs]
        if len(set(outs)) != len(outs):
            raise SchemaError(f"duplicate outcome ids in experiment {eid!r}")
        outcomes.append(outs)
    eidx = {e: i for i, e in enumerate(exp_ids)}
    model_ids, q, obs = [], [], []
    for x in models:
        mid = _ident(_req(x, "id", str))
        if mid in model_ids:
            raise SchemaError(f"duplicate model id {mid!r}")
        model_ids.append(mid)
        q.append(str_to_rat(_req(x, "q", str)))
        ob = _req(x, "obs", dict)
        if set(ob) != set(exp_ids):
            raise SchemaError(f"model {mid!r}: observations must cover exactly the declared experiments")
        row = [0] * len(exp_ids)
        for e, o in ob.items():
            i = eidx[e]
            if o not in outcomes[i]:
                raise SchemaError(f"model {mid!r}: undeclared outcome {o!r} for {e!r}")
            row[i] = outcomes[i].index(o)
        obs.append(row)
    midx = {m: i for i, m in enumerate(model_ids)}
    query = _req(raw, "query", dict)
    _ident(_req(query, "id", str))
    P = Problem(model_ids, exp_ids, outcomes, obs, q, costs,
                meta={"name": raw["name"], "query": query})
    assumptions = []
    for a in raw.get("assumptions", []):
        aid = _ident(_req(a, "id", str))
        holds = _req(a, "holds", list)
        mask = 0
        for m in holds:
            if m not in midx:
                raise SchemaError(f"assumption {aid!r} references unknown model {m!r}")
            mask |= 1 << midx[m]
        assumptions.append({"id": aid, "description": a.get("description", ""), "mask": mask})
    data = []
    for d in raw.get("data", []):
        e = _req(d, "experiment", str)
        o = _req(d, "outcome", str)
        if e not in eidx or o not in outcomes[eidx[e]]:
            raise SchemaError(f"datum references unknown experiment/outcome {e!r}/{o!r}")
        data.append((eidx[e], outcomes[eidx[e]].index(o)))
    eps = str_to_rat(raw.get("tolerance", "0"))
    if eps < 0:
        raise SchemaError("negative tolerance")
    return Spec(raw, P, assumptions, data, eps)


def load_problem(path: str) -> Spec:
    with open(path, "rb") as f:
        return parse_problem(loads(f.read()))


def problem_to_json(P: Problem, name: str, query_id: str, query_desc: str = "",
                    assumptions=(), data=(), eps=Fraction(0), description: str = "") -> Dict:
    return {
        "schema": PROBLEM_SCHEMA,
        "name": name,
        "description": description,
        "query": {"id": query_id, "description": query_desc},
        "experiments": [{"id": P.experiments[e], "cost": rat_to_str(P.cost[e]),
                         "outcomes": P.outcomes[e]} for e in range(P.k)],
        "models": [{"id": P.models[m], "q": rat_to_str(P.q[m]),
                    "obs": {P.experiments[e]: P.outcomes[e][P.obs[m][e]] for e in range(P.k)}}
                   for m in range(P.n)],
        "assumptions": [{"id": a["id"], "description": a.get("description", ""),
                         "holds": [P.models[m] for m in bits(a["mask"])]} for a in assumptions],
        "data": [{"experiment": P.experiments[e], "outcome": P.outcomes[e][o]} for (e, o) in data],
        "tolerance": rat_to_str(eps),
    }


# ------------------------------------------------------------- certificates
def policy_to_json(P: Problem, pol):
    if pol == "stop":
        return "stop"
    return {"experiment": P.experiments[pol["e"]],
            "next": {P.outcomes[pol["e"]][o]: policy_to_json(P, c) for o, c in sorted(pol["next"].items())}}


def policy_from_json(P: Problem, j, counter=None):
    counter = counter if counter is not None else [0]
    counter[0] += 1
    if counter[0] > MAX_POLICY_NODES:
        raise SchemaError("policy too large")
    if j == "stop":
        return "stop"
    if not isinstance(j, dict) or set(j) != {"experiment", "next"}:
        raise SchemaError("malformed policy node")
    e = j["experiment"]
    if e not in P.experiments:
        raise SchemaError(f"policy references unknown experiment {e!r}")
    ei = P.experiments.index(e)
    if not isinstance(j["next"], dict):
        raise SchemaError("malformed policy continuation")
    nxt = {}
    for o, sub in j["next"].items():
        if o not in P.outcomes[ei]:
            raise SchemaError(f"policy references undeclared outcome {o!r}")
        nxt[P.outcomes[ei].index(o)] = policy_from_json(P, sub, counter)
    return {"e": ei, "next": nxt}


def mask_to_ids(P, mask):
    return [P.models[m] for m in bits(mask)]


def ids_to_mask(P, ids):
    if not isinstance(ids, list):
        raise SchemaError("model set must be a list")
    idx = {m: i for i, m in enumerate(P.models)}
    mask = 0
    for m in ids:
        if m not in idx:
            raise SchemaError(f"unknown model id {m!r}")
        if (mask >> idx[m]) & 1:
            raise SchemaError(f"duplicate model id {m!r} in set")
        mask |= 1 << idx[m]
    return mask


def optimal_cert_to_json(spec: Spec, res: Dict) -> Dict:
    P = spec.P
    return {
        "schema": CERT_SCHEMA, "problem_sha256": spec.hash, "kind": "optimal",
        "bound": rat_to_str(res["value"]),
        "core": mask_to_ids(P, res["core"]),
        "policy": policy_to_json(P, res["policy"]),
        "adversary": [{"models": mask_to_ids(P, S), "lb": rat_to_str(b)}
                      for S, b in sorted(res["adversary"].items(), key=lambda t: (bin(t[0]).count("1"), t[0]))],
    }


def parse_optimal_cert(spec: Spec, j: Dict) -> Dict:
    if not isinstance(j, dict) or j.get("schema") != CERT_SCHEMA:
        raise SchemaError("unsupported certificate schema")
    if j.get("problem_sha256") != spec.hash:
        raise SchemaError("certificate is bound to a different problem")
    if j.get("kind") != "optimal":
        raise SchemaError("not an optimality certificate")
    if set(j) != {"schema", "problem_sha256", "kind", "bound", "core", "policy", "adversary"}:
        raise SchemaError("unexpected or missing certificate fields")
    P = spec.P
    adv = []
    for ent in _req(j, "adversary", list):
        if not isinstance(ent, dict) or set(ent) != {"models", "lb"}:
            raise SchemaError("malformed adversary entry")
        b = str_to_rat(ent["lb"])
        if b < 0:
            raise SchemaError("negative adversary value")
        adv.append((ids_to_mask(P, ent["models"]), b))
    bound = str_to_rat(_req(j, "bound", str))
    if bound < 0:
        raise SchemaError("negative bound")
    return {"bound": bound, "core": ids_to_mask(P, j["core"]),
            "policy": policy_from_json(P, j["policy"]), "adversary": adv}
