"""Hardened independent certificate checker (schema v1).

Does not import scientific_reasoning.evaluator.
Reconstructs every judgment from rules + citations; does not trust claimed outputs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Set

SCHEMA_VERSION = 1
MAX_PREMISES = 256
MAX_STEPS = 1024
MAX_DEPTH = 64
MAX_PROPID = 2_147_483_647
MAX_JSON_BYTES = 1_000_000

RANK = {
    "disputed": 0,
    "hypothesis": 1,
    "empiricalAsserted": 2,
    "assumption": 2,
    "derived": 3,
    "mathVerified": 4,
}

TIE_ORDER = {
    "disputed": 0,
    "hypothesis": 1,
    "assumption": 2,
    "empiricalAsserted": 3,
    "derived": 4,
    "mathVerified": 5,
}

ALLOWED_TOP = {
    "schema_version",
    "premises",
    "steps",
    "conclusion_step",
    "conclusion",
    "final_support",
    "final_authority",
}

ALLOWED_PREMISE = {"id", "formula", "declared_authority", "authority"}
ALLOWED_STEP_COMMON = {
    "id",
    "rule",
    "formula",
    "support",
    "declared_authority",
    "authority",
    "math_established",
}
ALLOWED_STEP_BY_RULE = {
    "hyp": ALLOWED_STEP_COMMON | {"premise_id"},
    "andI": ALLOWED_STEP_COMMON | {"left", "right"},
    "andE1": ALLOWED_STEP_COMMON | {"from"},
    "andE2": ALLOWED_STEP_COMMON | {"from"},
}


class CheckError(Exception):
    pass


def meet(a: str, b: str) -> str:
    if a not in RANK or b not in RANK:
        raise CheckError("bad authority in meet")
    if RANK[a] < RANK[b]:
        return a
    if RANK[b] < RANK[a]:
        return b
    return a if TIE_ORDER[a] <= TIE_ORDER[b] else b


@dataclass
class Judgment:
    formula: Any
    support: List[int]
    declared_authority: str
    math_established: bool


def _require_int(x: Any, what: str) -> int:
    if isinstance(x, bool) or not isinstance(x, int):
        raise CheckError(f"{what} must be JSON integer, got {type(x).__name__}")
    if x < 0 or x > MAX_PROPID:
        raise CheckError(f"{what} out of range")
    return x


def _formula_depth(φ: Any, d: int = 0) -> int:
    if d > MAX_DEPTH:
        raise CheckError("formula depth exceeded")
    if not isinstance(φ, list) or len(φ) < 2:
        raise CheckError("malformed formula")
    tag = φ[0]
    if not isinstance(tag, str):
        raise CheckError("formula tag must be string")
    if tag == "atom":
        if len(φ) != 2:
            raise CheckError("atom arity")
        _require_int(φ[1], "atom id")
        return d
    if tag == "not":
        if len(φ) != 2:
            raise CheckError("not arity")
        return _formula_depth(φ[1], d + 1)
    if tag == "and":
        if len(φ) != 3:
            raise CheckError("and arity")
        return max(_formula_depth(φ[1], d + 1), _formula_depth(φ[2], d + 1))
    raise CheckError(f"unknown formula tag {tag}")


def _eq_formula(a: Any, b: Any) -> bool:
    return a == b


def _reject_unknown(obj: dict, allowed: Set[str], what: str) -> None:
    extra = set(obj.keys()) - allowed
    if extra:
        raise CheckError(f"unknown fields in {what}: {sorted(extra)}")


def _object_pairs_hook(pairs: list) -> dict:
    out: dict = {}
    for k, v in pairs:
        if k in out:
            raise CheckError(f"duplicate JSON key {k!r}")
        out[k] = v
    return out


def parse_certificate_json(text: str) -> dict:
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise CheckError("JSON too large")
    try:
        data = json.loads(text, object_pairs_hook=_object_pairs_hook)
    except json.JSONDecodeError as e:
        raise CheckError(f"malformed JSON: {e}") from e
    if not isinstance(data, dict):
        raise CheckError("certificate must be object")
    return data


def check(cert: dict) -> Judgment:
    if not isinstance(cert, dict):
        raise CheckError("certificate must be object")
    _reject_unknown(cert, ALLOWED_TOP, "certificate")

    # Boolean True must not masquerade as schema version 1
    sv = cert.get("schema_version")
    if isinstance(sv, bool) or not isinstance(sv, int) or sv != SCHEMA_VERSION:
        raise CheckError("unsupported schema_version")

    premises = cert.get("premises")
    steps = cert.get("steps")
    if not isinstance(premises, list) or not isinstance(steps, list):
        raise CheckError("premises/steps must be arrays")
    if len(premises) > MAX_PREMISES or len(steps) > MAX_STEPS:
        raise CheckError("size limit")
    if not steps:
        raise CheckError("empty steps")

    pm: Dict[int, dict] = {}
    for p in premises:
        if not isinstance(p, dict):
            raise CheckError("premise must be object")
        _reject_unknown(p, ALLOWED_PREMISE, "premise")
        i = _require_int(p.get("id"), "premise id")
        if i in pm:
            raise CheckError(f"duplicate premise id {i}")
        φ = p.get("formula")
        _formula_depth(φ)
        auth = p.get("declared_authority")
        if auth not in RANK:
            auth = p.get("authority")
        if auth not in RANK:
            raise CheckError("bad declared_authority")
        pm[i] = {"id": i, "formula": φ, "declared_authority": auth}

    judgments: Dict[int, Judgment] = {}
    for idx, s in enumerate(steps):
        if not isinstance(s, dict):
            raise CheckError("step must be object")
        rule = s.get("rule")
        if rule not in ALLOWED_STEP_BY_RULE:
            raise CheckError(f"unknown rule {rule}")
        _reject_unknown(s, ALLOWED_STEP_BY_RULE[rule], f"step/{rule}")
        sid = _require_int(s.get("id"), "step id")
        if sid != idx:
            raise CheckError(f"step id {sid} != index {idx}")
        if sid in judgments:
            raise CheckError("duplicate step id")

        if rule == "hyp":
            pid = _require_int(s.get("premise_id"), "premise_id")
            if pid not in pm:
                raise CheckError("unknown premise")
            p = pm[pid]
            j = Judgment(
                formula=p["formula"],
                support=[pid],
                declared_authority=p["declared_authority"],
                math_established=False,
            )
        elif rule == "andI":
            left = _require_int(s.get("left"), "left")
            right = _require_int(s.get("right"), "right")
            if left >= idx or right >= idx:
                raise CheckError("forward reference")
            if left not in judgments or right not in judgments:
                raise CheckError("missing citation")
            jl, jr = judgments[left], judgments[right]
            j = Judgment(
                formula=["and", jl.formula, jr.formula],
                support=list(jl.support) + list(jr.support),
                declared_authority=meet(jl.declared_authority, jr.declared_authority),
                math_established=jl.math_established and jr.math_established,
            )
        else:  # andE1 / andE2
            fr = _require_int(s.get("from"), "from")
            if fr >= idx:
                raise CheckError("forward reference")
            if fr not in judgments:
                raise CheckError("missing citation")
            jf = judgments[fr]
            φ = jf.formula
            if not (isinstance(φ, list) and len(φ) == 3 and φ[0] == "and"):
                raise CheckError("andE requires conjunction")
            out = φ[1] if rule == "andE1" else φ[2]
            j = Judgment(
                formula=out,
                support=list(jf.support),
                declared_authority=jf.declared_authority,
                math_established=jf.math_established,
            )

        if "formula" in s and not _eq_formula(s["formula"], j.formula):
            raise CheckError("claimed formula mismatch")
        if "support" in s:
            if not isinstance(s["support"], list):
                raise CheckError("claimed support must be array")
            # reject bools in support
            for x in s["support"]:
                _require_int(x, "claimed support id")
            if list(s["support"]) != j.support:
                raise CheckError("claimed support mismatch")
        claimed_auth = s.get("declared_authority", s.get("authority"))
        if claimed_auth is not None and claimed_auth != j.declared_authority:
            raise CheckError("claimed authority mismatch")
        if s.get("math_established") is True:
            raise CheckError("cannot claim math_established without attestation")

        judgments[sid] = j

    cstep = _require_int(cert.get("conclusion_step"), "conclusion_step")
    if cstep not in judgments:
        raise CheckError("conclusion_step missing")
    final = judgments[cstep]

    if "conclusion" in cert and not _eq_formula(cert["conclusion"], final.formula):
        raise CheckError("top-level conclusion mismatch")
    if "final_support" in cert:
        if not isinstance(cert["final_support"], list):
            raise CheckError("final_support must be array")
        for x in cert["final_support"]:
            _require_int(x, "final_support id")
        if list(cert["final_support"]) != final.support:
            raise CheckError("final_support mismatch")
    if "final_authority" in cert and cert["final_authority"] != final.declared_authority:
        raise CheckError("final_authority mismatch")

    if final.math_established:
        raise CheckError("math_established must be false without attestation")

    return final


def check_path(path: str) -> Judgment:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return check(parse_certificate_json(text))


if __name__ == "__main__":
    import sys

    j = check_path(sys.argv[1])
    print(
        "OK",
        json.dumps(
            {
                "formula": j.formula,
                "support": j.support,
                "declared_authority": j.declared_authority,
                "math_established": j.math_established,
            }
        ),
    )
