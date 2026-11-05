"""PCS Semantic Translation Contract v1 — Python client for the Lean authority.

This module is the *untrusted-side* bridge between a Python translation pipeline and the
certified Lean checker ``pcs-semantic-check``.  It deliberately contains **no semantic
checking logic**: every authority decision is computed by the Lean binary, whose decision
function is proved (in ``PCS.V2.TranslationJson``) to equal the certified checker
``PCS.V2.Semantic.checkTranslation``.  Python only

* serializes requests as canonical JSON (RFC 8785 fragment: sorted keys, no whitespace,
  integers only) — the exact bytes the Lean decoder accepts;
* invokes the binary and parses its canonical-JSON decision;
* fails closed: any error (missing binary, crash, timeout, non-zero exit without a parsable
  decision, schema mismatch, verdict/exit-code disagreement) is reported as a rejection;
* exposes the structured diagnostics as model feedback.

Integration with the full PCS repository's ``proof_translation_v06.py`` pipeline is an
explicit OPEN item (that file is not part of the standalone ``formal/`` package); see
``PCS_SEMANTIC_TRANSLATION_V1_REPORT.md``.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

REQUEST_SCHEMA = "pcs-semantic-translation-v1"
AUTHORITY_SCHEMA = "pcs-semantic-authority-v1"
DECISION_SCHEMA = "pcs-semantic-decision-v1"

VERDICTS = ("ACCEPTED", "NEEDS_CLARIFICATION", "REJECTED")

_DEFAULT_BINARY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".lake", "build", "bin", "pcs-semantic-check")


def canonical_json(obj: Any) -> bytes:
    """Canonical JSON bytes accepted by the Lean decoder (ints only, sorted keys)."""
    def check(v: Any) -> None:
        if isinstance(v, bool) or v is None or isinstance(v, str):
            return
        if isinstance(v, int):
            if abs(v) > 2 ** 53:
                raise ValueError("integer outside the canonical safe range")
            return
        if isinstance(v, float):
            raise ValueError("non-integral numbers are outside the canonical fragment")
        if isinstance(v, list):
            for x in v:
                check(x)
            return
        if isinstance(v, dict):
            for k, x in v.items():
                if not isinstance(k, str):
                    raise ValueError("object keys must be strings")
                check(x)
            return
        raise ValueError(f"unsupported JSON value {type(v)!r}")
    check(obj)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------------------
# Structured-claim builders (convenience only; the Lean decoder is the authority)
# ---------------------------------------------------------------------------------------

def var(x: str) -> Dict[str, Any]:
    return {"var": x}


def app(f: str, *args: Dict[str, Any]) -> Dict[str, Any]:
    return {"args": list(args), "fn": f}


def pred(p: str, *args: Dict[str, Any]) -> Dict[str, Any]:
    return {"args": list(args), "op": "pred", "symbol": p}


def eq(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {"lhs": a, "op": "eq", "rhs": b}


def ne(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {"lhs": a, "op": "ne", "rhs": b}


def not_(a: Dict[str, Any]) -> Dict[str, Any]:
    return {"arg": a, "op": "not"}


def and_(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {"lhs": a, "op": "and", "rhs": b}


def or_(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {"lhs": a, "op": "or", "rhs": b}


def implies(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {"lhs": a, "op": "implies", "rhs": b}


def forall(x: str, sort: str, body: Dict[str, Any]) -> Dict[str, Any]:
    return {"body": body, "op": "forall", "sort": sort, "var": x}


def exists(x: str, sort: str, body: Dict[str, Any]) -> Dict[str, Any]:
    return {"body": body, "op": "exists", "sort": sort, "var": x}


def unsupported(construct: str) -> Dict[str, Any]:
    """Mark a construct outside the fragment explicitly (always rejected by PCS)."""
    return {"construct": construct, "op": "unsupported"}


def claim(params: List[Dict[str, str]], assumptions: List[Dict[str, Any]],
          conclusion: Dict[str, Any]) -> Dict[str, Any]:
    return {"assumptions": assumptions, "conclusion": conclusion, "params": params}


# ---------------------------------------------------------------------------------------
# Decisions and model feedback
# ---------------------------------------------------------------------------------------

@dataclass
class Decision:
    verdict: str
    diagnostics: List[Dict[str, str]] = field(default_factory=list)
    expected_lean_source: str = ""
    explanation: Optional[Dict[str, Any]] = None
    explanation_literal: Optional[str] = None
    exit_code: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None

    @property
    def authoritative(self) -> bool:
        """True only for a well-formed ACCEPTED decision with exit code 0."""
        return (self.verdict == "ACCEPTED" and self.exit_code == 0 and not self.diagnostics
                and self.raw is not None and self.raw.get("schema") == DECISION_SCHEMA)

    @property
    def codes(self) -> List[str]:
        return [d.get("code", "") for d in self.diagnostics]

    def feedback(self) -> Dict[str, Any]:
        """Deterministic, machine-readable feedback for a (future) proposer model.

        The labels come exclusively from the PCS checker's diagnostics."""
        return {
            "accepted": self.authoritative,
            "verdict": self.verdict,
            "failure_codes": sorted(set(self.codes)),
            "failing_components": sorted({d.get("component", "") for d in self.diagnostics}),
            "diagnostics": self.diagnostics,
            "expected_lean_source": self.expected_lean_source,
            "needs_clarification": self.verdict == "NEEDS_CLARIFICATION",
        }


def _reject(reason: str, exit_code: Optional[int] = None) -> Decision:
    return Decision(verdict="REJECTED",
                    diagnostics=[{"code": "MALFORMED_INPUT", "component": "python-bridge",
                                  "detail": reason}],
                    exit_code=exit_code)


def parse_decision(stdout: bytes, exit_code: int) -> Decision:
    """Parse the binary's output, failing closed on any inconsistency."""
    try:
        raw = json.loads(stdout.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - fail closed on anything
        return _reject(f"unparsable checker output: {exc}", exit_code)
    if not isinstance(raw, dict) or raw.get("schema") != DECISION_SCHEMA:
        return _reject("checker output has the wrong schema", exit_code)
    verdict = raw.get("verdict")
    if verdict not in VERDICTS:
        return _reject("checker output has an unknown verdict", exit_code)
    if (verdict == "ACCEPTED") != (exit_code == 0):
        return _reject("checker verdict and exit code disagree", exit_code)
    diags = raw.get("diagnostics")
    if not isinstance(diags, list) or (verdict == "ACCEPTED" and diags):
        return _reject("checker diagnostics inconsistent with verdict", exit_code)
    return Decision(verdict=verdict, diagnostics=diags,
                    expected_lean_source=raw.get("expected_lean_source", ""),
                    explanation=raw.get("explanation"),
                    explanation_literal=raw.get("explanation_literal"),
                    exit_code=exit_code, raw=raw)


def check_bytes(authority_bytes: bytes, request_bytes: bytes,
                binary: str = _DEFAULT_BINARY, timeout: float = 120.0) -> Decision:
    """Run the Lean authority on raw bytes (no re-serialization)."""
    if not os.path.isfile(binary):
        return _reject(f"checker binary not found: {binary}")
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "authority.json")
        r = os.path.join(d, "request.json")
        with open(a, "wb") as f:
            f.write(authority_bytes)
        with open(r, "wb") as f:
            f.write(request_bytes)
        try:
            proc = subprocess.run([binary, a, r], capture_output=True, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            return _reject(f"checker invocation failed: {exc}")
    if proc.returncode not in (0, 1):
        return _reject(f"checker exited with status {proc.returncode}", proc.returncode)
    return parse_decision(proc.stdout, proc.returncode)


def check(authority: Dict[str, Any], request: Dict[str, Any],
          binary: str = _DEFAULT_BINARY, timeout: float = 120.0) -> Decision:
    """Serialize canonically and run the Lean authority."""
    try:
        a = canonical_json(authority)
        r = canonical_json(request)
    except Exception as exc:  # noqa: BLE001
        return _reject(f"request is outside the canonical JSON fragment: {exc}")
    return check_bytes(a, r, binary=binary, timeout=timeout)


def explain(authority: Dict[str, Any], structured_claim: Dict[str, Any],
            binary: str = _DEFAULT_BINARY, timeout: float = 120.0) -> Optional[Dict[str, Any]]:
    """Lean → human: Explanation IR of a structured claim (None on any failure)."""
    if not os.path.isfile(binary):
        return None
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "authority.json")
        c = os.path.join(d, "claim.json")
        with open(a, "wb") as f:
            f.write(canonical_json(authority))
        with open(c, "wb") as f:
            f.write(canonical_json(structured_claim))
        try:
            proc = subprocess.run([binary, "--explain", a, c], capture_output=True, timeout=timeout)
        except Exception:  # noqa: BLE001
            return None
    if proc.returncode != 0:
        return None
    try:
        out = json.loads(proc.stdout.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return out if out.get("schema") == "pcs-semantic-explanation-v1" else None


def propose_check_repair(authority: Dict[str, Any], proposer, max_rounds: int = 5,
                         binary: str = _DEFAULT_BINARY) -> Optional[Dict[str, Any]]:
    """Untrusted propose → check → repair loop (mirrors ``PCS.V2.Proposer.runLoop``).

    ``proposer(history)`` returns the next request given the list of
    ``(request, feedback)`` pairs so far.  Only a request that the Lean authority accepts
    is ever returned; the proposer's own confidence is never consulted."""
    history: List[Any] = []
    for _ in range(max_rounds):
        req = proposer(history)
        dec = check(authority, req, binary=binary)
        if dec.authoritative:
            return req
        history.append((req, dec.feedback()))
    return None
