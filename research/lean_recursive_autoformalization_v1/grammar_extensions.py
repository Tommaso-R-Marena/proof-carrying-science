"""Additive English patterns NOT present in base ``formalize``.

Each extension is gated by a discrete rule id from the PGRA catalog. Patterns
are fail-closed: unrecognized English is left unsupported. Roundtrip uses the
existing IR / ``parse_lean`` path when a Lean fragment can be produced.

General unrestricted English remains unproved; these rules only enlarge a
finite controlled grammar.
"""
from __future__ import annotations

import re
from typing import Any

from pcs.experimental.prover.ir import digest, theorem
from pcs.experimental.prover.language import formalize, parse_lean

# Catalog order is the search order used by the recursive loop.
RULE_CATALOG: tuple[tuple[str, str], ...] = (
    (
        "rule_unique_exists",
        "There exists a unique natural number n such that ... → ∃! via ∃ n, P ∧ ∀ m, P[m] → m = n",
    ),
    (
        "rule_neither_nor",
        '"neither A nor B" → ¬A ∧ ¬B',
    ),
    (
        "rule_exactly_when",
        '"exactly when" → ↔',
    ),
    (
        "rule_whenever",
        '"whenever A, B" → A → B',
    ),
    (
        "rule_plus_times_words",
        '"plus"/"times" as +/*',
    ),
    (
        "rule_distinct_forall",
        '"For all distinct natural numbers a and b, ..." → ∀ a b, ¬(a = b) → body',
    ),
    (
        "rule_zero_word",
        '"zero" as the Nat literal 0',
    ),
    (
        "rule_is_equal_to",
        '"is equal to" → =',
    ),
)

RULE_IDS: tuple[str, ...] = tuple(rule_id for rule_id, _ in RULE_CATALOG)
RULE_DESCRIPTIONS: dict[str, str] = dict(RULE_CATALOG)


def _replace_atomic_english(body: str) -> str:
    """Shared atomic English→symbol map used after structural rewrites."""
    text = body
    for english, symbol in [
        ("if and only if", "↔"),
        ("exactly when", "↔"),
        ("is less than or equal to", "≤"),
        ("equals", "="),
        ("implies", "→"),
        ("and", "∧"),
        ("or", "∨"),
        ("not", "¬"),
        ("plus", "+"),
        ("times", "*"),
    ]:
        text = re.sub(r"\b" + english + r"\b", symbol, text, flags=re.I)
    return text


def _try_unique_exists(source: str) -> dict[str, Any] | None:
    text = source.strip().rstrip(".")
    match = re.fullmatch(
        r"There exists a unique (natural number|integer) "
        r"([A-Za-z][A-Za-z0-9_]*) such that (.+)",
        text,
        re.I,
    )
    if not match:
        return None
    domain = {"natural number": "Nat", "integer": "Int"}[match[1].lower()]
    name = match[2]
    body_en = match[3].strip()
    alt = "m" if name != "m" else "k"
    body_alt = re.sub(rf"\b{re.escape(name)}\b", alt, body_en)
    body_lean = _replace_atomic_english(body_en)
    body_alt_lean = _replace_atomic_english(body_alt)
    lean = (
        f"∃ ({name} : {domain}), ({body_lean}) ∧ "
        f"(∀ ({alt} : {domain}), ({body_alt_lean}) → ({alt} = {name}))"
    )
    try:
        ir = parse_lean(lean)
        formal = theorem(ir)
        return {
            "status": "supported",
            "source": source,
            "source_sha256": digest(source),
            "candidates": [
                {
                    "ir": ir,
                    "lean": formal,
                    "interpretation_sha256": digest(ir),
                    "score": None,
                }
            ],
            "semantic_authorization": False,
            "extension_rule": "rule_unique_exists",
            "fidelity_boundary": (
                "Controlled unique-exists extension; unrestricted English unproved."
            ),
        }
    except ValueError as ex:
        return {
            "status": "unsupported",
            "source": source,
            "source_sha256": digest(source),
            "candidates": [],
            "reason": str(ex),
            "extension_rule": "rule_unique_exists",
        }


def _rewrite_neither_nor(body: str) -> str:
    def repl(match: re.Match[str]) -> str:
        left, right = match.group(1).strip(), match.group(2).strip()
        return f"(not ({left})) and (not ({right}))"

    return re.sub(
        r"\bneither\b\s+(.+?)\s+\bnor\b\s+(.+)",
        repl,
        body,
        count=1,
        flags=re.I,
    )


def _rewrite_whenever(body: str) -> str:
    match = re.fullmatch(r"whenever\s+(.+?),\s*(.+)", body.strip(), re.I)
    if not match:
        match = re.fullmatch(r"whenever\s+(.+?)\s+then\s+(.+)", body.strip(), re.I)
    if not match:
        return body
    return f"if {match.group(1).strip()} then {match.group(2).strip()}"


def _rewrite_exactly_when(body: str) -> str:
    return re.sub(r"\bexactly when\b", "if and only if", body, flags=re.I)


def _rewrite_plus_times(body: str) -> str:
    body = re.sub(r"\bplus\b", "+", body, flags=re.I)
    body = re.sub(r"\btimes\b", "*", body, flags=re.I)
    return body


def _rewrite_zero_word(body: str) -> str:
    return re.sub(r"\bzero\b", "0", body, flags=re.I)


def _rewrite_is_equal_to(body: str) -> str:
    return re.sub(r"\bis equal to\b", "equals", body, flags=re.I)


def _try_distinct_forall(source: str) -> dict[str, Any] | None:
    text = source.strip().rstrip(".")
    match = re.fullmatch(
        r"For all distinct (natural numbers|integers) "
        r"([A-Za-z][A-Za-z0-9_]*) and ([A-Za-z][A-Za-z0-9_]*), (.+)",
        text,
        re.I,
    )
    if not match:
        return None
    domain_words = match[1].lower()
    domain = "Nat" if domain_words.startswith("natural") else "Int"
    a, b, body_en = match[2], match[3], match[4].strip()
    if a == b:
        return {
            "status": "unsupported",
            "source": source,
            "candidates": [],
            "reason": "distinct binders must differ",
            "extension_rule": "rule_distinct_forall",
        }
    body_lean = _replace_atomic_english(body_en)
    lean = (
        f"∀ ({a} : {domain}) ({b} : {domain}), "
        f"(¬ ({a} = {b})) → ({body_lean})"
    )
    try:
        ir = parse_lean(lean)
        formal = theorem(ir)
        return {
            "status": "supported",
            "source": source,
            "source_sha256": digest(source),
            "candidates": [
                {
                    "ir": ir,
                    "lean": formal,
                    "interpretation_sha256": digest(ir),
                    "score": None,
                }
            ],
            "semantic_authorization": False,
            "extension_rule": "rule_distinct_forall",
            "fidelity_boundary": (
                "Controlled distinct-forall extension; unrestricted English unproved."
            ),
        }
    except ValueError as ex:
        return {
            "status": "unsupported",
            "source": source,
            "source_sha256": digest(source),
            "candidates": [],
            "reason": str(ex),
            "extension_rule": "rule_distinct_forall",
        }


def apply_extensions(source: str, rules: frozenset[str]) -> dict[str, Any] | None:
    """Attempt rule-gated rewrites. Return a formalize-like dict or None to fall through."""
    if type(source) is not str or not source.strip():
        return None

    if "rule_unique_exists" in rules:
        hit = _try_unique_exists(source)
        if hit is not None:
            return hit

    if "rule_distinct_forall" in rules:
        hit = _try_distinct_forall(source)
        if hit is not None:
            return hit

    needs_body = bool(
        rules
        & {
            "rule_neither_nor",
            "rule_exactly_when",
            "rule_whenever",
            "rule_plus_times_words",
            "rule_zero_word",
            "rule_is_equal_to",
        }
    )
    if not needs_body:
        return None

    text = source.strip().rstrip(".")
    outer = re.fullmatch(
        r"((?:For all|For every|For any) .+?, )(.+)",
        text,
        re.I,
    )
    existence = re.fullmatch(
        r"(There exists (?:a|an) (?:natural number|integer|proposition) "
        r"[A-Za-z][A-Za-z0-9_]* such that )(.+)",
        text,
        re.I,
    )
    if outer:
        prefix, body = outer.group(1), outer.group(2)
    elif existence:
        prefix, body = existence.group(1), existence.group(2)
    else:
        return None

    rewritten = body
    used: list[str] = []
    if "rule_neither_nor" in rules and re.search(r"\bneither\b.+\bnor\b", rewritten, re.I):
        rewritten = _rewrite_neither_nor(rewritten)
        used.append("rule_neither_nor")
    if "rule_exactly_when" in rules and re.search(r"\bexactly when\b", rewritten, re.I):
        rewritten = _rewrite_exactly_when(rewritten)
        used.append("rule_exactly_when")
    if "rule_whenever" in rules and re.match(r"whenever\b", rewritten.strip(), re.I):
        rewritten = _rewrite_whenever(rewritten)
        used.append("rule_whenever")
    if "rule_plus_times_words" in rules and re.search(r"\b(plus|times)\b", rewritten, re.I):
        rewritten = _rewrite_plus_times(rewritten)
        used.append("rule_plus_times_words")
    if "rule_zero_word" in rules and re.search(r"\bzero\b", rewritten, re.I):
        rewritten = _rewrite_zero_word(rewritten)
        used.append("rule_zero_word")
    if "rule_is_equal_to" in rules and re.search(r"\bis equal to\b", rewritten, re.I):
        rewritten = _rewrite_is_equal_to(rewritten)
        used.append("rule_is_equal_to")

    if not used or rewritten == body:
        return None

    result = formalize(prefix + rewritten)
    if result.get("status") in {"supported", "ambiguous"}:
        result = dict(result)
        result["extension_rules"] = used
        result["semantic_authorization"] = False
    return result


__all__ = [
    "RULE_CATALOG",
    "RULE_IDS",
    "RULE_DESCRIPTIONS",
    "apply_extensions",
]
