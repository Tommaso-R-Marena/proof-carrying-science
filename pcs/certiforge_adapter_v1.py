"""Pinned, bounded CertiForge subprocess protocol; no imported optimizer internals.

An accepted result is exhaustive computational replay by a trusted Rust checker.
It is never a Lean proof or a PCS authoritative scientific certificate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

from .jsonio import strict_json_loads
from .provisional_adapter_v1 import _read_pinned

FORMAT = "pcs-certiforge-proposal-v1"
RESULT_FORMAT = "pcs-certiforge-result-v1"
MEMBERS = frozenset({"manifest.json", "program.certir", "optimized.certir", "spec.json",
                     "effects.json", "certificates/functional.lean", "certificates/equivalence.lean"})
HEX = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _object(value: Any, fields: set[str]) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("unexpected protocol fields")
    return value


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject(code: str) -> dict:
    return {"format": RESULT_FORMAT, "state": "REJECTED", "pcs_authority": False,
            "lean_kernel_checked": False, "diagnostics": [code]}


def evaluate(proposal: Any, root: Path, *, checker: Path, checker_sha256: str,
             checker_source_commit: str, timeout_seconds: int = 120) -> dict:
    """Caller pins the trusted checker separately from producer-controlled data.

    Snapshot exact pinned members into a fresh directory before invoking the
    checker. Optimizer assertions, producer provenance, benchmark JSON and LRAT
    placeholder files cannot grant authority through this interface.
    """
    try:
        _object(proposal, {"format", "claim_id", "source", "artifacts", "cost_objective"})
        if proposal["format"] != FORMAT:
            raise ValueError("unsupported adapter protocol")
        claim = proposal["claim_id"]
        if type(claim) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", claim):
            raise ValueError("invalid claim identity")
        source = _object(proposal["source"], {"repository", "commit", "disclosure"})
        if (source["repository"] != "Tommaso-R-Marena/certiforge" or
            type(source["commit"]) is not str or not COMMIT.fullmatch(source["commit"]) or
            source["disclosure"] not in ("private", "public", "synthetic")):
            raise ValueError("invalid source provenance")
        objective = _object(proposal["cost_objective"], {"metric", "require_improvement"})
        if objective["metric"] != "CERTIR_AST_NODE_COUNT" or type(objective["require_improvement"]) is not bool:
            raise ValueError("unsupported cost objective")
        if (type(checker_sha256) is not str or not HEX.fullmatch(checker_sha256) or
            type(checker_source_commit) is not str or not COMMIT.fullmatch(checker_source_commit)):
            raise ValueError("reviewer checker pins required")
        if checker.is_symlink() or not checker.is_file() or checker.resolve().is_relative_to(root.resolve()):
            raise ValueError("checker must be a separate trusted regular executable")
        if checker.stat().st_size > 64_000_000 or _hash(checker.read_bytes()) != checker_sha256:
            raise ValueError("checker byte pin mismatch")
        entries = proposal["artifacts"]
        if type(entries) is not list or len(entries) != len(MEMBERS):
            raise ValueError("complete semantic package inventory required")
        snapshots = {}
        identities = set()
        for entry in entries:
            if type(entry) is not dict or type(entry.get("id")) is not str:
                raise ValueError("invalid artifact identity")
            path = entry.get("path")
            if path not in MEMBERS or path in snapshots or entry["id"] in identities:
                raise ValueError("duplicate or unregistered package member")
            snapshots[path] = _read_pinned(root, entry)
            identities.add(entry["id"])
        if set(snapshots) != MEMBERS:
            raise ValueError("incomplete package inventory")
        expected_hashes = {name: _hash(raw) for name, raw in snapshots.items()}
        with tempfile.TemporaryDirectory(prefix="pcs-certiforge-") as temp:
            package = Path(temp)
            for name, raw in snapshots.items():
                file = package / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(raw)
            process = subprocess.run([str(checker.resolve()), "package", "verify", str(package), "--json"],
                                     capture_output=True, timeout=timeout_seconds, check=False)
            if len(process.stdout) > 200_000 or process.returncode not in (0, 2):
                raise ValueError("checker process failed")
            if any(_hash((package / name).read_bytes()) != expected_hashes[name] for name in MEMBERS):
                raise ValueError("checker modified supplied evidence")
        if _hash(checker.read_bytes()) != checker_sha256:
            raise ValueError("checker changed during execution")
        evidence = strict_json_loads(process.stdout.decode("utf-8"))
        _object(evidence, {"format", "checker_version", "result", "method", "domain_size",
                           "artifact_sha256", "cost", "lean_kernel_checked",
                           "rust_lean_refinement_proved", "unsolved_obligations"})
        if (evidence["format"] != "certiforge-verification-v1" or evidence["checker_version"] != "0.1.0" or
            evidence["method"] != "EXHAUSTIVE_RUST_REPLAY" or
            evidence["lean_kernel_checked"] is not False or evidence["rust_lean_refinement_proved"] is not False or
            evidence["artifact_sha256"] != expected_hashes):
            raise ValueError("checker contract mismatch")
        if type(evidence["domain_size"]) is not int or not 1 <= evidence["domain_size"] <= 65536:
            raise ValueError("unverified or oversized semantic domain")
        verdict = evidence["result"]
        if type(verdict) is not dict or verdict.get("result") not in ("accept", "reject"):
            raise ValueError("invalid checker verdict")
        if verdict["result"] == "reject":
            if process.returncode != 2 or set(verdict) != {"result", "reasons"}:
                raise ValueError("checker exit/verdict mismatch")
            return _reject("SEMANTIC_CHECK_REJECTED")
        if process.returncode != 0 or set(verdict) != {"result"}:
            raise ValueError("checker exit/verdict mismatch")
        costs = _object(evidence["cost"], {"objective", "original", "optimized"})
        if costs["objective"] != objective["metric"] or any(type(costs[x]) is not int or not 1 <= costs[x] <= 100000 for x in ("original", "optimized")):
            raise ValueError("invalid cost evidence")
        if objective["require_improvement"] and costs["optimized"] >= costs["original"]:
            return _reject("COST_OBJECTIVE_NOT_MET")
        obligations = evidence["unsolved_obligations"]
        if type(obligations) is not list or not obligations or any(type(x) is not str or not x for x in obligations):
            raise ValueError("residual obligations missing")
        return {"format": RESULT_FORMAT, "state": "CHECKED_EXHAUSTIVE",
                "claim_id": claim, "source": source, "source_provenance_verified": False,
                "checker": {"sha256": checker_sha256, "source_commit": checker_source_commit,
                            "version": evidence["checker_version"], "build_correspondence": "EXTERNALLY_TRUSTED"},
                "artifact_sha256": expected_hashes, "domain_size": evidence["domain_size"], "cost": costs,
                "proof_status": "COMPUTATIONALLY_REPLAYED_NOT_FORMALLY_PROVED",
                "pcs_authority": False, "lean_kernel_checked": False,
                "unsolved_obligations": obligations, "diagnostics": [],
                "trusted_computing_base": ["pinned Rust checker, parser and interpreter", "SHA-256", "OS/process isolation", "reviewer checker/build provenance"]}
    except (ValueError, OSError, TypeError, KeyError, RecursionError, subprocess.TimeoutExpired):
        return _reject("FAIL_CLOSED_PROTOCOL_OR_INPUT")


def research_claim_graph(proposal: dict, result: dict, root: Path) -> dict:
    """Bind computational evidence into the existing v1 IR, leaving authority BLOCKED.

    Call only after evaluate. This function is a research/reporting API, not a
    verifier registration. The graph can never close the residual obligations.
    """
    from .proof_translation_v06 import _claim_ir_v06, _proof_obligation_graph, _obligation
    if (result.get("state") != "CHECKED_EXHAUSTIVE" or result.get("pcs_authority") is not False or
            result.get("lean_kernel_checked") is not False or result.get("claim_id") != proposal.get("claim_id")):
        raise ValueError("a scoped computational receipt is required")
    inventory = {}
    for entry in proposal["artifacts"]:
        raw = _read_pinned(root, entry)
        if _hash(raw) != result["artifact_sha256"].get(entry["path"]):
            raise ValueError("artifacts changed before claim binding")
        inventory[entry["id"]] = {"id": entry["id"], "path": entry["path"],
                                   "sha256": entry["sha256"], "size": len(raw)}
    claim_id = result["claim_id"]
    candidate = {"id": claim_id, "source": proposal["source"], "selected": False,
                 "formalizable": False, "status": "COMPUTATIONALLY_REPLAYED_NOT_FORMALLY_PROVED",
                 "artifact_ids": list(inventory),
                 "typed_claim": {"id": claim_id, "kind": "computational",
                   "statement": "The optimized pure CertIR program preserves the original program over the complete admitted input domain and satisfies the stated AST-node cost objective.",
                   "predicate": {"format": FORMAT, "domain_size": result["domain_size"],
                      "artifact_sha256": result["artifact_sha256"], "checker": result["checker"],
                      "cost": result["cost"], "scope": "Bool/u8/u16 Cartesian domains of at most 65536 inputs; Rust semantics"}},
                 "obligations": [_obligation(claim_id, "CERTIFORGE_RESIDUAL_OBLIGATION", item,
                     blocking=True) for item in result["unsolved_obligations"]]}
    claim_ir = _claim_ir_v06([candidate])
    graph = _proof_obligation_graph([candidate], inventory=inventory, claim_ir=claim_ir)
    assert graph["summary"]["blocking_obligations"] > 0
    return {"format": "pcs-certiforge-research-claim-graph-v1", "claim_ir": claim_ir,
            "obligation_graph": graph, "pcs_authority": False, "verifier_registered": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--checker", required=True, type=Path)
    parser.add_argument("--checker-sha256", required=True)
    parser.add_argument("--checker-source-commit", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.proposal.stat().st_size > 65536:
            raise ValueError("proposal too large")
        proposal = strict_json_loads(args.proposal.read_text(encoding="utf-8"))
        result = evaluate(proposal, args.package, checker=args.checker,
                          checker_sha256=args.checker_sha256, checker_source_commit=args.checker_source_commit)
    except (ValueError, OSError):
        result = _reject("INVALID_PROPOSAL")
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as file:
            file.write(payload)
    else:
        print(payload, end="")
    return 0 if result["state"] == "CHECKED_EXHAUSTIVE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
