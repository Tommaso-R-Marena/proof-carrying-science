"""Typed scientific Claim IR with scope-preserving constructors."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

from ..core.canonical import canonical_hash
from ..core.errors import ErrorCode, PcsNextError
from ..core.schemas import CLAIM_IR_FORMAT

Sort = str


@dataclass(frozen=True)
class Var:
    name: str
    sort: Sort
    unit: str | None = None


@dataclass(frozen=True)
class Expr:
    kind: str
    data: dict[str, Any] = field(default_factory=dict)


def var_ref(v: Var) -> Expr:
    return Expr("var", {"name": v.name, "sort": v.sort, "unit": v.unit})


def const(value: Any, sort: Sort, unit: str | None = None) -> Expr:
    return Expr("const", {"value": value, "sort": sort, "unit": unit})


def app(fn: str, args: list[Expr], sort: Sort) -> Expr:
    return Expr("app", {"fn": fn, "args": [asdict(a) for a in args], "sort": sort})


def eq(a: Expr, b: Expr) -> Expr:
    return Expr("eq", {"left": asdict(a), "right": asdict(b)})


def ineq(op: Literal["lt", "le", "gt", "ge"], a: Expr, b: Expr) -> Expr:
    return Expr(op, {"left": asdict(a), "right": asdict(b)})


def neg(phi: Expr) -> Expr:
    return Expr("not", {"of": asdict(phi)})


def and_(*phis: Expr) -> Expr:
    return Expr("and", {"args": [asdict(p) for p in phis]})


def or_(*phis: Expr) -> Expr:
    return Expr("or", {"args": [asdict(p) for p in phis]})


def implies(a: Expr, b: Expr) -> Expr:
    return Expr("implies", {"antecedent": asdict(a), "consequent": asdict(b)})


def forall(v: Var, body: Expr, *, domain: Expr | None = None) -> Expr:
    return Expr(
        "forall",
        {
            "var": asdict(v),
            "domain": asdict(domain) if domain else None,
            "body": asdict(body),
        },
    )


def exists(v: Var, body: Expr, *, domain: Expr | None = None) -> Expr:
    return Expr(
        "exists",
        {
            "var": asdict(v),
            "domain": asdict(domain) if domain else None,
            "body": asdict(body),
        },
    )


def approx(a: Expr, b: Expr, bound: Expr) -> Expr:
    """Numerical approximation |a-b| <= bound — never silently becomes equality."""
    return Expr("approx", {"left": asdict(a), "right": asdict(b), "bound": asdict(bound)})


def probabilistic(event: Expr, op: str, p: Expr) -> Expr:
    return Expr("prob", {"event": asdict(event), "op": op, "probability": asdict(p)})


def association(a: Expr, b: Expr, measure: str) -> Expr:
    """Statistical association — must not be read as causation."""
    return Expr(
        "association",
        {
            "a": asdict(a),
            "b": asdict(b),
            "measure": measure,
            "not_causation": True,
        },
    )


def validate_expr(node: dict[str, Any], *, bound: set[str] | None = None) -> None:
    bound = set(bound or [])
    kind = node.get("kind")
    data = node.get("data", node)  # tolerate flat
    if "kind" in node and "data" in node:
        kind = node["kind"]
        data = node["data"]
    elif "kind" in node:
        kind = node["kind"]
        data = {k: v for k, v in node.items() if k != "kind"}

    if kind in {"forall", "exists"}:
        v = data["var"]
        name = v["name"]
        if name in bound:
            # shadowing allowed but recorded
            pass
        body = data["body"]
        validate_expr(body if "kind" in body else body, bound=bound | {name})
        return
    if kind == "var":
        # free var ok; binder discipline checked at claim level optionally
        return
    if kind == "not":
        validate_expr(data["of"])
        return
    if kind in {"and", "or"}:
        for a in data.get("args", []):
            validate_expr(a)
        return
    if kind == "implies":
        validate_expr(data["antecedent"])
        validate_expr(data["consequent"])
        return
    # recursive generic walk
    for v in data.values():
        if isinstance(v, dict) and ("kind" in v or "data" in v):
            validate_expr(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    validate_expr(item)


def expr_to_dict(e: Expr) -> dict[str, Any]:
    return {"kind": e.kind, "data": e.data}


def alpha_eq(a: dict[str, Any], b: dict[str, Any], env_a: dict[str, str] | None = None, env_b: dict[str, str] | None = None) -> bool:
    """Alpha-equivalence for forall/exists binders."""
    env_a = dict(env_a or {})
    env_b = dict(env_b or {})

    def norm(node):
        if "kind" in node and "data" in node:
            return node["kind"], node["data"]
        kind = node.get("kind")
        data = {k: v for k, v in node.items() if k != "kind"}
        return kind, data

    ka, da = norm(a)
    kb, db = norm(b)
    if ka != kb:
        return False
    if ka in {"forall", "exists"}:
        va, vb = da["var"]["name"], db["var"]["name"]
        # map both to fresh
        fresh = f"#{len(env_a)}"
        return alpha_eq(da["body"], db["body"], {**env_a, va: fresh}, {**env_b, vb: fresh})
    if ka == "var":
        na = env_a.get(da["name"], da["name"])
        nb = env_b.get(db["name"], db["name"])
        return na == nb and da.get("sort") == db.get("sort")
    if ka == "not":
        return alpha_eq(da["of"], db["of"], env_a, env_b)
    # structural compare with recursive dicts
    if sorted(da.keys()) != sorted(db.keys()):
        return False
    for k in da:
        va, vb = da[k], db[k]
        if isinstance(va, dict) and isinstance(vb, dict) and ("kind" in va or "kind" in vb):
            if not alpha_eq(va, vb, env_a, env_b):
                return False
        elif isinstance(va, list) and isinstance(vb, list):
            if len(va) != len(vb):
                return False
            for xa, xb in zip(va, vb):
                if isinstance(xa, dict) and isinstance(xb, dict):
                    if not alpha_eq(xa, xb, env_a, env_b):
                        return False
                elif xa != xb:
                    return False
        elif va != vb:
            return False
    return True


def negate_preserves(phi: dict[str, Any]) -> dict[str, Any]:
    """Double-negation introduction helper — does not flip quantifiers."""
    return {"kind": "not", "data": {"of": {"kind": "not", "data": {"of": phi}}}}


def claim_document(
    claim_id: str,
    text: str,
    expr: Expr,
    *,
    assumptions: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
    obligations: list[str] | None = None,
) -> dict[str, Any]:
    body = expr_to_dict(expr)
    validate_expr(body)
    doc = {
        "format": CLAIM_IR_FORMAT,
        "claim_id": claim_id,
        "text": text,
        "expr": body,
        "assumptions": list(assumptions or []),
        "provenance": provenance or {"source": "manual"},
        "undischarged_obligations": list(obligations or []),
    }
    doc["content_hash"] = canonical_hash({k: v for k, v in doc.items() if k != "content_hash"})
    return doc


def refuse_ambiguous(alternatives: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    if not alternatives:
        raise PcsNextError(ErrorCode.AMBIGUOUS_CLAIM, reason)
    return {
        "status": "OPEN",
        "error_code": ErrorCode.AMBIGUOUS_CLAIM.value,
        "reason": reason,
        "alternatives": alternatives,
    }
