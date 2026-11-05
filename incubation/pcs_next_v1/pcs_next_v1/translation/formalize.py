"""Natural-language candidate → Claim IR pipeline (deterministic fragment)."""

from __future__ import annotations

import re
from typing import Any

from ..core.statuses import AssuranceStatus
from .claim_ir import (
    Var,
    approx,
    association,
    claim_document,
    const,
    eq,
    exists,
    forall,
    implies,
    ineq,
    refuse_ambiguous,
    var_ref,
)

# Extremely small deterministic extractor for supported patterns only.
_FORALL_INEQ = re.compile(
    r"^for all (?P<var>[A-Za-z_][A-Za-z0-9_]*) in (?P<domain>\w+),\s*"
    r"(?P<lhs>.+?)\s*(?P<op><=|>=|<|>|=)\s*(?P<rhs>.+)$",
    re.I,
)
_EXISTS = re.compile(
    r"^there exists (?P<var>[A-Za-z_][A-Za-z0-9_]*) such that (?P<body>.+)$",
    re.I,
)
_APPROX = re.compile(
    r"^(?P<a>.+?)\s*(?:≈|approx(?:imately)?)\s*(?P<b>.+?)\s*within\s*(?P<bound>.+)$",
    re.I,
)
_ASSOC = re.compile(
    r"^(?P<a>.+?)\s+is associated with\s+(?P<b>.+)$",
    re.I,
)


def analyze_ambiguity(text: str) -> list[str]:
    notes = []
    if "may" in text.lower() or "might" in text.lower():
        notes.append("modal language without quantified probability")
    if "causes" in text.lower() and "associated" in text.lower():
        notes.append("mixed causal and associational language")
    if text.count(" or ") and "either" not in text.lower():
        notes.append("inclusive/exclusive or unclear")
    return notes


def formalize_text(claim_id: str, text: str) -> dict[str, Any]:
    """Return claim document or OPEN ambiguity record.

    Distinguishes extracted vs inferred content in provenance.
    """
    text = text.strip()
    amb = analyze_ambiguity(text)

    m = _FORALL_INEQ.match(text)
    if m:
        opmap = {"<": "lt", "<=": "le", ">": "gt", ">=": "ge", "=": "eq"}
        v = Var(m.group("var"), "Real")
        lhs = const(m.group("lhs").strip(), "Real")
        rhs = const(m.group("rhs").strip(), "Real")
        op = m.group("op")
        body = eq(lhs, rhs) if op == "=" else ineq(opmap[op], lhs, rhs)  # type: ignore[arg-type]
        expr = forall(v, body)
        return claim_document(
            claim_id,
            text,
            expr,
            provenance={"source": "deterministic_extractor", "extracted": True, "inferred": False, "ambiguity": amb},
        )

    m = _EXISTS.match(text)
    if m:
        v = Var(m.group("var"), "Real")
        # body left as opaque const to avoid silent universalization
        body = eq(var_ref(v), const(m.group("body").strip(), "Prop"))
        expr = exists(v, body)
        return claim_document(
            claim_id,
            text,
            expr,
            provenance={"source": "deterministic_extractor", "extracted": True, "inferred": False, "ambiguity": amb},
            obligations=["ground existential body predicate"],
        )

    m = _APPROX.match(text)
    if m:
        expr = approx(
            const(m.group("a").strip(), "Real"),
            const(m.group("b").strip(), "Real"),
            const(m.group("bound").strip(), "Real"),
        )
        return claim_document(
            claim_id,
            text,
            expr,
            provenance={"source": "deterministic_extractor", "extracted": True, "inferred": False},
        )

    m = _ASSOC.match(text)
    if m:
        expr = association(const(m.group("a").strip(), "Obs"), const(m.group("b").strip(), "Obs"), "unspecified")
        return claim_document(
            claim_id,
            text,
            expr,
            provenance={"source": "deterministic_extractor", "extracted": True, "inferred": False},
            obligations=["association is not causation"],
        )

    if amb:
        return refuse_ambiguous(
            [
                {"interpretation": "literal_unsupported", "text": text},
                {"interpretation": "needs_human_grounding", "text": text},
            ],
            "ambiguous or unsupported natural-language claim",
        )

    return {
        "status": AssuranceStatus.UNSUPPORTED.value,
        "reason": "no deterministic pattern matched; refusing arbitrary authoritative selection",
        "text": text,
        "claim_id": claim_id,
    }


def to_lean_sketch(claim: dict[str, Any]) -> str:
    """Untrusted sketch only — never authority."""
    if claim.get("format") != "pcs-next-claim-ir-v1":
        return "-- UNSUPPORTED\n"
    expr = claim["expr"]
    return (
        "-- UNTRUSTED AI/tool sketch; requires actual Lean checking\n"
        f"-- claim_id: {claim['claim_id']}\n"
        f"-- expr_kind: {expr.get('kind')}\n"
        "theorem claim_sketch : True := trivial\n"
    )
