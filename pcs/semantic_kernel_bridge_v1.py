"""Fail-closed adapter from PCS translation data to the actual Lean semantic executable.

This adapter checks authentic *binary bytes* and a pinned authority configuration.
It does not claim that a binary hash proves kernel correctness or that human intent
was established. The existing Lean authority's canonical JSON decoder is decisive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Mapping

DECISION_SCHEMA = "pcs-semantic-decision-v1"
REQUEST_SCHEMA = "pcs-semantic-translation-v1"
AUTHORITY_SCHEMA = "pcs-semantic-authority-v1"
MAX_INPUT = 1_000_000
MAX_OUTPUT = 200_000
_HEX = re.compile(r"^[0-9a-f]{64}$")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON key")
        result[name] = value
    return result


def strict_decode(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_INPUT:
        raise ValueError("JSON request exceeds limit")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON")))
    if type(value) is not dict:
        raise ValueError("JSON root is not an object")
    return value


def canonical_bytes(value: Any) -> bytes:
    def check(node: Any) -> None:
        if node is None or type(node) in (str, bool):
            return
        if type(node) is int and abs(node) <= 2**53:
            return
        if type(node) is list:
            for entry in node:
                check(entry)
            return
        if type(node) is dict and all(type(k) is str for k in node):
            for entry in node.values():
                check(entry)
            return
        raise ValueError("unsupported JSON value or number")
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rejected(reason: str, *, request_sha: str | None = None) -> dict[str, Any]:
    return {"format": "pcs-semantic-kernel-bridge-result-v1",
            "state": "REJECTED", "checker_verdict": None,
            "pcs_scientific_authority": False, "independent_kernel_receipt": False,
            "request_sha256": request_sha,
            "diagnostics": [{"code": reason, "component": "kernel-bridge"}]}


def _pin(raw: bytes, expected: str, role: str) -> None:
    if type(expected) is not str or not _HEX.fullmatch(expected):
        raise ValueError("INVALID_" + role + "_PIN")
    if digest(raw) != expected:
        raise ValueError(role + "_PIN_MISMATCH")


def evaluate(binary: str | Path, *, binary_sha256: str,
             authority_bytes: bytes, authority_sha256: str,
             request_bytes: bytes, claim_ir: Mapping[str, Any] | None = None,
             binding: Mapping[str, Any] | None = None,
             approved_binding_sha256: str | None = None,
             timeout_seconds: int = 120) -> dict[str, Any]:
    """Exact binary/authority commitments and subprocess verdict, never trust JSON alone."""
    request_sha = digest(request_bytes)
    try:
        if timeout_seconds < 1 or timeout_seconds > 180:
            raise ValueError("INVALID_TIMEOUT")
        req, authority = strict_decode(request_bytes), strict_decode(authority_bytes)
        if req.get("schema") != REQUEST_SCHEMA or authority.get("schema") != AUTHORITY_SCHEMA:
            raise ValueError("SCHEMA_MISMATCH")
        # The checker, not Python, validates each decoded meaning and receipt.
        if canonical_bytes(req) != request_bytes or canonical_bytes(authority) != authority_bytes:
            raise ValueError("NONCANONICAL_REQUEST")
        _pin(authority_bytes, authority_sha256, "AUTHORITY")
        path = Path(binary)
        if not path.is_file() or path.is_symlink():
            raise ValueError("CHECKER_BINARY_MISSING")
        b = path.read_bytes()
        _pin(b, binary_sha256, "BINARY")
        claim_binding = None
        if claim_ir is not None:
            if binding is None or approved_binding_sha256 is None:
                raise ValueError("CLAIM_BINDING_APPROVAL_REQUIRED")
            from .semantic_claim_binding_v1 import verify_binding
            claim_binding = verify_binding(
                claim_ir, req, authority_sha256=authority_sha256,
                request_sha256=request_sha, binding=binding,
                approved_binding_sha256=approved_binding_sha256)
        elif binding is not None or approved_binding_sha256 is not None:
            raise ValueError("CLAIM_BINDING_WITHOUT_IR")
        with tempfile.TemporaryDirectory(prefix="pcs-semantic-") as work:
            a, r = Path(work) / "authority.json", Path(work) / "request.json"
            a.write_bytes(authority_bytes)
            r.write_bytes(request_bytes)
            proc = subprocess.run([str(path.resolve()), str(a), str(r)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=timeout_seconds, check=False)
        if proc.returncode not in (0, 1) or len(proc.stdout) > MAX_OUTPUT:
            raise ValueError("CHECKER_PROCESS_FAILURE")
        decision = strict_decode(proc.stdout)
        if decision.get("schema") != DECISION_SCHEMA:
            raise ValueError("DECISION_SCHEMA_MISMATCH")
        verdict = decision.get("verdict")
        if verdict not in ("ACCEPTED", "REJECTED", "NEEDS_CLARIFICATION"):
            raise ValueError("UNKNOWN_VERDICT")
        if (verdict == "ACCEPTED") != (proc.returncode == 0):
            raise ValueError("VERDICT_EXIT_MISMATCH")
        diagnostics = decision.get("diagnostics")
        if type(diagnostics) is not list or (verdict == "ACCEPTED" and diagnostics):
            raise ValueError("DIAGNOSTICS_INVALID")
        for item in diagnostics:
            if type(item) is not dict or type(item.get("code")) is not str:
                raise ValueError("DIAGNOSTICS_INVALID")
        return {"format": "pcs-semantic-kernel-bridge-result-v1",
                "state": "CHECKER_ACCEPTED_BOUNDED" if verdict == "ACCEPTED" else verdict,
                "checker_verdict": verdict,
                "authority_mode": "STATELESS_NONPRODUCTION",
                "production_authority": False,
                "pcs_scientific_authority": False,
                "independent_kernel_receipt": False,
                "binary_sha256": binary_sha256,
                "authority_sha256": authority_sha256,
                "request_sha256": request_sha,
                "claim_ir_binding": claim_binding,
                "diagnostics": diagnostics,
                "explanation_ir": decision.get("explanation") if verdict == "ACCEPTED" else None,
                "limitations": ["Compiled checker integrity pinned, but kernel/source/compiler correspondence externally trusted",
                                "Interpretation meaning and signer identity are not independently established by this adapter",
                                "This is not a PCS scientific certificate or external-world guarantee"]}
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired,
            UnicodeError, json.JSONDecodeError, OverflowError, RecursionError):
        return rejected("FAIL_CLOSED_VALIDATION", request_sha=request_sha)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pinned actual Lean semantic checker bridge")
    for field in ("binary", "binary-sha256", "authority", "authority-sha256", "request"):
        p.add_argument("--" + field, required=True)
    p.add_argument("--output")
    p.add_argument("--claim-ir")
    p.add_argument("--binding")
    p.add_argument("--approved-binding-sha256")
    a = p.parse_args(argv)
    try:
        result = evaluate(a.binary, binary_sha256=a.binary_sha256,
                          authority_bytes=Path(a.authority).read_bytes(),
                          authority_sha256=a.authority_sha256,
                          request_bytes=Path(a.request).read_bytes(),
                          claim_ir=strict_decode(Path(a.claim_ir).read_bytes()) if a.claim_ir else None,
                          binding=strict_decode(Path(a.binding).read_bytes()) if a.binding else None,
                          approved_binding_sha256=a.approved_binding_sha256)
    except OSError:
        result = rejected("INPUT_IO_FAILED")
    output = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if a.output:
        Path(a.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if result["state"] == "CHECKER_ACCEPTED_BOUNDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
