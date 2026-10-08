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
        if claim_ir is not None:
            if claim_ir.get("format") != "pcs-claim-ir-v1":
                raise ValueError("CLAIM_IR_SCHEMA_MISMATCH")
            from .canonical_json import canonicalize_jcs_bytes
            core = {k: v for k, v in claim_ir.items() if k != "claim_ir_sha256"}
            actual = digest(canonicalize_jcs_bytes(core))
            if claim_ir.get("claim_ir_sha256") != actual:
                raise ValueError("CLAIM_IR_SHA_MISMATCH")
            # Never infer the model's semantics from a mere claim statement.
            raise ValueError("CLAIM_IR_INTERPRETATION_MAPPING_NOT_CERTIFIED")
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
                "pcs_scientific_authority": False,
                "independent_kernel_receipt": False,
                "binary_sha256": binary_sha256,
                "authority_sha256": authority_sha256,
                "request_sha256": request_sha,
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
    a = p.parse_args(argv)
    try:
        result = evaluate(a.binary, binary_sha256=a.binary_sha256,
                          authority_bytes=Path(a.authority).read_bytes(),
                          authority_sha256=a.authority_sha256,
                          request_bytes=Path(a.request).read_bytes())
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
