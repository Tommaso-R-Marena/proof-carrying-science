"""Provisional PCS adapter interoperability (not a trusted acceptance pathway).

This is a *local diagnostic* for pinned cross-project inputs. No successful
result from this module may be treated as a Lean checked claim, PCS acceptance,
a digital signature, or proof of deployed-run fidelity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from .jsonio import StrictJSONError, strict_json_loads


FORMAT = "pcs-adapter-proposal-v1"
RESULT_FORMAT = "pcs-adapter-precheck-v1"
REGISTRY = frozenset({"pcs.reference.identical_bytes.v1", "pcs.reference.bounded_trace.v1"})
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
MAX_INPUT_BYTES = 65536
MAX_ARTIFACT_BYTES = 2_000_000


class AdapterProposalError(ValueError):
    """Invalid or unsupported adapter proposal; fail closed."""


def _obj(value: Any, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise AdapterProposalError(f"{label} must have exactly {sorted(keys)}")
    return value


def _identity(value: Any, label: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise AdapterProposalError(f"unsafe {label}")
    return value


def _int(value: Any, label: str, low: int = 0, high: int = 1_000_000) -> int:
    if type(value) is not int or not low <= value <= high:
        raise AdapterProposalError(f"{label} must be an integer in [{low}, {high}]")
    return value


def _bounded_text(value: Any, label: str, maximum: int = 3000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise AdapterProposalError(f"{label} must be nonempty text (max {maximum})")
    return value


def _path(root: Path, path: Any) -> Path:
    if not isinstance(path, str) or not 1 <= len(path) <= 300 or "\\" in path:
        raise AdapterProposalError("unsafe artifact path")
    parts = path.split("/")
    if not all(_SEGMENT.fullmatch(x) and x not in {".", ".."} for x in parts):
        raise AdapterProposalError("unsafe artifact path components")
    file = root.joinpath(*parts)
    if any(candidate.is_symlink() for candidate in (root, *[root.joinpath(*parts[:i]) for i in range(1, len(parts) + 1)])):
        raise AdapterProposalError("symbolic links are not admissible artifacts")
    resolved_root = root.resolve(strict=True)
    try:
        resolved = file.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AdapterProposalError("artifact is missing or inaccessible") from exc
    if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
        raise AdapterProposalError("artifact escapes the supplied root or is not a regular file")
    return resolved


def _read_pinned(root: Path, entry: dict) -> bytes:
    _obj(entry, {"id", "path", "sha256"}, "artifact")
    digest = entry["sha256"]
    if not isinstance(digest, str) or _HEX.fullmatch(digest) is None:
        raise AdapterProposalError("artifact SHA-256 must be lowercase hexadecimal")
    source = _path(root, entry["path"])
    if source.stat().st_size > MAX_ARTIFACT_BYTES:
        raise AdapterProposalError("artifact is too large")
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise AdapterProposalError("artifact SHA-256 mismatch: " + entry["id"])
    return raw


def evaluate_proposal(proposal: Any, root: Path) -> dict:
    """Check a registered finite synthetic reference contract without elevating it.

    A local PASS is only a diagnostic. Integrators must bind an independent,
    reviewed semantics checker through PCS's separate authority layer.
    """
    proposal = _obj(proposal, {"format", "source", "claim", "artifacts", "check", "assumptions"}, "proposal")
    if proposal["format"] != FORMAT:
        raise AdapterProposalError("unsupported proposal format")
    source = _obj(proposal["source"], {"project", "commit", "disclosure"}, "source")
    _identity(source["project"], "project")
    if not isinstance(source["commit"], str) or _COMMIT.fullmatch(source["commit"]) is None:
        raise AdapterProposalError("source revision must be 40 lowercase hex characters")
    if not isinstance(source["disclosure"], str) or source["disclosure"] not in {"synthetic", "private", "public"}:
        raise AdapterProposalError("source disclosure must be explicit")

    claim = _obj(proposal["claim"], {"id", "kind", "statement"}, "claim")
    _identity(claim["id"], "claim ID")
    if claim["kind"] != "computational":
        raise AdapterProposalError("only bounded computational proposals are supported")
    _bounded_text(claim["statement"], "claim statement")

    assumptions = proposal["assumptions"]
    if not isinstance(assumptions, list) or len(assumptions) > 32 or any(
        not isinstance(x, str) or not x.strip() or len(x) > 400 for x in assumptions
    ):
        raise AdapterProposalError("assumptions must be a bounded list of nonempty strings")
    if len(assumptions) != len(set(assumptions)):
        raise AdapterProposalError("duplicate assumptions")

    artifacts = proposal["artifacts"]
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 8:
        raise AdapterProposalError("require 1-8 pinned artifacts")
    files: dict[str, bytes] = {}
    names = set()
    for entry in artifacts:
        if not isinstance(entry, dict):
            raise AdapterProposalError("artifact record must be an object")
        key = _identity(entry.get("id"), "artifact ID")
        artifact_path = entry.get("path")
        if not isinstance(artifact_path, str):
            raise AdapterProposalError("artifact path must be a string")
        if key in files or artifact_path in names:
            raise AdapterProposalError("duplicate artifact ID or file path")
        files[key] = _read_pinned(root, entry)
        names.add(entry["path"])

    check = proposal["check"]
    if not isinstance(check, dict):
        raise AdapterProposalError("check must be an object")
    check_type = check.get("type")
    if not isinstance(check_type, str) or check_type not in REGISTRY:
        raise AdapterProposalError("UNREGISTERED_CHECK_TYPE: no transcript/status fallback is permitted")
    if check_type == "pcs.reference.identical_bytes.v1":
        _obj(check, {"type", "left_artifact", "right_artifact"}, "identical_bytes check")
        left = _identity(check["left_artifact"], "left artifact")
        right = _identity(check["right_artifact"], "right artifact")
        if left == right or left not in files or right not in files or set(files) != {left, right}:
            raise AdapterProposalError("identity checker requires two distinct, pinned artifacts")
        ok = files[left] == files[right]
        explanation = "Exact artifact bytes match" if ok else "Exact artifact bytes differ"
    else:
        _obj(check, {"type", "trace_artifact", "forbidden_action", "max_cumulative_risk"}, "bounded_trace check")
        trace_id = _identity(check["trace_artifact"], "trace artifact")
        if trace_id not in files or set(files) != {trace_id}:
            raise AdapterProposalError("bounded trace must name its single pinned artifact")
        forbidden = _int(check["forbidden_action"], "forbidden action")
        budget = _int(check["max_cumulative_risk"], "risk budget")
        try:
            trace = strict_json_loads(files[trace_id].decode("utf-8"))
        except (UnicodeDecodeError, StrictJSONError) as exc:
            raise AdapterProposalError("invalid strict JSON trace") from exc
        _obj(trace, {"events"}, "trace")
        events = trace["events"]
        if not isinstance(events, list) or not 1 <= len(events) <= 128:
            raise AdapterProposalError("trace must contain 1-128 events")
        risk = 0
        ok = True
        first_failure = None
        for index, event in enumerate(events, start=1):
            _obj(event, {"action", "risk"}, f"event {index}")
            action = _int(event["action"], f"event {index} action")
            risk += _int(event["risk"], f"event {index} risk")
            if action == forbidden or risk > budget:
                ok = False
                if first_failure is None:
                    first_failure = f"step {index}: forbidden action or cumulative risk budget exceeded"
        explanation = "Every recorded prefix satisfies the policy" if ok else str(first_failure)

    return {
        "format": RESULT_FORMAT,
        "kind": "UNTRUSTED_ADAPTER_DIAGNOSTIC",
        "result": "LOCAL_CHECK_PASS" if ok else "LOCAL_CHECK_FAIL",
        "check_type": check_type,
        "claim_id": claim["id"],
        "source_commit": source["commit"],
        "explanation": explanation,
        "authoritative": False,
        "pcs_acceptance": "NOT_EVALUATED",
        "claim_status": "OPEN",
        "limitations": [
            "This is an unsigned local structural/computational check, not a Lean proof.",
            "Producer claims and provenance labels do not authenticate real-world execution.",
            "No unregistered check type may inherit transcript PASS or confer PCS acceptance.",
            "Formal, semantic-preservation, or deployed-run claims require separate soundness bridges.",
        ],
    }


def evaluate_file(envelope: Path, root: Path) -> dict:
    if envelope.stat().st_size > MAX_INPUT_BYTES:
        raise AdapterProposalError("proposal file exceeds size limit")
    try:
        document = strict_json_loads(envelope.read_text(encoding="utf-8"))
    except (UnicodeError, StrictJSONError) as exc:
        raise AdapterProposalError("invalid strict JSON proposal") from exc
    return evaluate_proposal(document, root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PCS provisional adapter contract; never authoritative.")
    parser.add_argument("--envelope", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate_file(args.envelope, args.root)
    except (OSError, AdapterProposalError) as exc:
        print(json.dumps({
            "format": RESULT_FORMAT,
            "kind": "UNTRUSTED_ADAPTER_DIAGNOSTIC",
            "result": "REJECTED",
            "authoritative": False,
            "pcs_acceptance": "NOT_EVALUATED",
            "claim_status": "OPEN",
            "error": str(exc),
        }, sort_keys=True))
        return 2
    text = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["result"] == "LOCAL_CHECK_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
