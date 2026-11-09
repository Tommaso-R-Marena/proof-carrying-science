"""Zero-API deterministic discovery of standalone numeric claims.

Low-cost first pass. Deliberately does not guess spans within prose, draw
scientific inferences, or accept ambiguous equations. The LLM can separately
propose additional spans through the existing explicit external mode.
"""
from __future__ import annotations

from .arithmetic import validate_arithmetic_claim
from .typed import parse_bindings, parse_typed_claim
from .core import COMPARISON, MAX_CLAIMS, Source, validate_claim


def discover_standalone(source: Source, mode: str) -> dict:
    """Return the same strict proposal schema as the remote provider adapters.

    A line counts only if every non-whitespace character is a parseable claim.
    Offsets are source Unicode codepoints, not bytes. Invalid lines are skipped,
    not 'refuted'. Too many valid lines fail instead of silently truncating.
    """
    if mode not in {"literal", "arithmetic", "typed"}:
        raise ValueError("unsupported deterministic extraction mode")
    bindings = parse_bindings(source) if mode == "typed" else None
    proposals = []
    cursor = 0
    for raw_line in source.text.splitlines(keepends=True):
        # Allow CRLF and LF, but reject all other control characters in quotes.
        line = raw_line.rstrip("\r\n")
        quote = line.strip(" \t")
        if not quote:
            cursor += len(raw_line)
            continue
        start = cursor + len(line) - len(line.lstrip(" \t"))
        end = start + len(quote)
        record = {
            "id": f"local_{len(proposals) + 1}",
            "source_span": {"start": start, "end": end},
            "source_quote": quote,
            "assumptions": [],
        }
        if mode == "typed" and not quote.startswith("assert "):
            cursor += len(raw_line)
            continue
        if mode == "literal":
            match = COMPARISON.fullmatch(quote)
            if match is None:
                cursor += len(raw_line)
                continue
            record["relation"] = {"lhs": match.group("lhs"), "op": match.group("op"), "rhs": match.group("rhs")}
        try:
            if mode == "arithmetic":
                validate_arithmetic_claim(record, source)
            elif mode == "typed":
                parse_typed_claim(record, source, bindings)
            else:
                validate_claim(record, source)
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            cursor += len(raw_line)
            continue
        if len(proposals) >= MAX_CLAIMS:
            raise ValueError("deterministic discovery exceeds claim budget")
        proposals.append(record)
        cursor += len(raw_line)
    return {"claims": proposals}
