"""Orchestration, deterministic receipts, independent optional reviewer, Lean check."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from . import VERSION
from .core import Source, Comparison, canonical, make_lean_source, prompt_for, PROPOSAL_SCHEMA, sha, validate_proposals
from .providers import Provider
from .arithmetic import ArithmeticClaim, make_arithmetic_lean_source, validate_arithmetic_proposals


class LocalCache:
    """Hash-keyed proposal cache. Local plaintext may include sensitive quotes.

    Cache directory is private on POSIX where supported, and writes are atomic.
    Caller is responsible for filesystem security of other users/admins.
    """
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise ValueError("cache directory must not be a symlink")

    def key(self, provider: Provider, source: Source) -> str:
        return sha(canonical({"version": VERSION, "role": "claims", "kind": provider.kind, "model": provider.model, "mode": provider.mode, "source_sha256": source.digest, "prompt_sha256": sha(provider.prompt(source).encode("utf-8")), "schema_sha256": sha(canonical(provider.schema))}))

    def get(self, key: str) -> dict | None:
        path = self.root / (key + ".json")
        if not path.exists():
            return None
        raw = path.read_bytes()
        if len(raw) > 131072:
            raise ValueError("cached response exceeds cap")
        result = json.loads(raw)
        if not isinstance(result, dict) or result.get("cache_key") != key or "proposal" not in result:
            raise ValueError("cache integrity mismatch")
        if result.get("proposal_sha256") != sha(canonical(result["proposal"])):
            raise ValueError("cache content hash mismatch")
        return result["proposal"]

    def put(self, key: str, proposal: dict) -> None:
        payload = canonical({"cache_key": key, "proposal": proposal, "proposal_sha256": sha(canonical(proposal))})
        fd, name = tempfile.mkstemp(prefix=".pcs-", suffix=".tmp", dir=self.root)
        try:
            os.chmod(name, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.root / (key + ".json"))
        finally:
            if os.path.exists(name):
                os.unlink(name)


def get_proposals(provider: Provider, source: Source, cache: LocalCache | None) -> tuple[dict, bool]:
    key = cache.key(provider, source) if cache else None
    if key is not None:
        cached = cache.get(key)
        if cached is not None:
            return cached, True
    proposal = provider.propose(source)
    if cache is not None and key is not None:
        cache.put(key, proposal)
    return proposal, False


class LeanChecker:
    def __init__(self, executable: str = "lean", timeout: int = 10):
        if timeout < 1 or timeout > 60:
            raise ValueError("Lean timeout must be 1..60 seconds")
        self.executable, self.timeout = executable, timeout

    def check(self, claim: Comparison) -> dict:
        code, truth = make_lean_source(claim)
        return self._check_generated(code, truth, "NORMALIZED")

    def check_arithmetic(self, claim: ArithmeticClaim) -> dict:
        code, truth = make_arithmetic_lean_source(claim)
        return self._check_generated(code, truth, "ARITH_EXPR")

    def _check_generated(self, code: str, truth: bool, scope: str) -> dict:
        executable = shutil.which(self.executable)
        output = {
            "normalization": ("external-exact-Fraction-cross-product" if scope == "NORMALIZED"
                              else "exact-AST-rational-expressions-rechecked-by-Lean"),
            "tested_relation": "source" if truth else "negation_of_source",
            "lean_source_sha256": sha(code.encode("utf-8")),
            "lean_source": code,
            "kernel_checked": False,
            "status": "KERNEL_UNAVAILABLE",
        }
        if executable is None:
            return output
        env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LEAN_PATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "USER", "TMPDIR"}}
        try:
            version = subprocess.run([executable, "--version"], capture_output=True, timeout=self.timeout, check=False, env=env)
        except (OSError, subprocess.TimeoutExpired):
            output["status"] = "KERNEL_INVOCATION_FAILED"
            return output
        version_string = version.stdout.decode("utf-8", errors="replace").strip()
        if version.returncode != 0 or not version_string.startswith("Lean (version 4.28.0"):
            output["status"] = "UNPINNED_LEAN_VERSION"
            return output
        output["lean_version"] = version_string[:256]
        with tempfile.TemporaryDirectory(prefix="pcs-experimental-lean-") as work:
            path = Path(work) / "Check.lean"
            path.write_text(code, encoding="utf-8")
            # Deliberately no model-generated code, shell, imports, axioms, or sorry.
            # Environment is minimized; PATH/LEAN_PATH support installed toolchains.
            try:
                result = subprocess.run([executable, str(path)], cwd=work, env=env, capture_output=True, timeout=self.timeout, check=False)
            except (OSError, subprocess.TimeoutExpired):
                output["status"] = "KERNEL_INVOCATION_FAILED"
                return output
        if result.returncode == 0:
            output["status"] = scope + ("_PROVED" if truth else "_REFUTED")
            output["kernel_checked"] = True
        else:
            output["status"] = "KERNEL_REJECTED"
            # This is generated-only arithmetic source. Diagnostic bytes contain
            # no provider prompts, API credentials, or external research text.
            output["lean_diagnostic"] = (
                (result.stderr + b"\n" + result.stdout).decode("utf-8", errors="replace")[:1800]
            )
        return output


def run(
    source: Source,
    primary_proposals: dict,
    *,
    reviewer_proposals: dict | None = None,
    lean: LeanChecker | None = None,
    primary_metadata: dict | None = None,
    reviewer_metadata: dict | None = None,
) -> dict:
    primary, rejected = validate_proposals(primary_proposals, source)
    reviewer_set = None
    if reviewer_proposals is not None:
        reviewer, reviewer_rejected = validate_proposals(reviewer_proposals, source)
        reviewer_set = {c.identity() for c in reviewer}
    else:
        reviewer_rejected = []
    claims = []
    for claim in primary:
        row = claim.to_dict()
        if reviewer_set is not None and claim.identity() not in reviewer_set:
            row["status"] = "NEEDS_REVIEW"
            row["kernel_checked"] = False
        else:
            check = lean.check(claim) if lean is not None else LeanChecker(executable="__pcs_missing_lean_executable__").check(claim)
            row.update(check)
            row["status"] = check["status"]
        claims.append(row)
    return {
        "schema_version": VERSION,
        "authority": "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY",
        "source_sha256": source.digest,
        "source_encoding": "UTF-8 raw bytes; offsets index Unicode codepoints",
        "primary_proposal_sha256": sha(canonical(primary_proposals)),
        "reviewer_proposal_sha256": sha(canonical(reviewer_proposals)) if reviewer_proposals is not None else None,
        "primary": primary_metadata or {"provider": "offline", "model": "local-fixture"},
        "reviewer": reviewer_metadata,
        "scope": "literal scalar comparisons only; no semantic/scientific validity",
        "claims": claims,
        "rejected": rejected,
        "reviewer_rejected": reviewer_rejected,
        "counts": {
            "primary_proposed": len(primary_proposals.get("claims", [])) if isinstance(primary_proposals.get("claims"), list) else 0,
            "accepted_grounding": len(primary),
            "rejected_grounding": len(rejected),
            "kernel_checked": sum(row.get("kernel_checked", False) for row in claims),
            "needs_review": sum(row["status"] == "NEEDS_REVIEW" for row in claims),
        },
    }


def run_arithmetic(
    source: Source, primary_proposals: dict, *, reviewer_proposals: dict | None = None,
    lean: LeanChecker | None = None, primary_metadata: dict | None = None,
    reviewer_metadata: dict | None = None,
) -> dict:
    """Research-only expression-claim receiver. Never promotes to PCS authority."""
    primary, rejected = validate_arithmetic_proposals(primary_proposals, source)
    reviewer_set = None
    reviewer_rejected = []
    if reviewer_proposals is not None:
        reviewers, reviewer_rejected = validate_arithmetic_proposals(reviewer_proposals, source)
        reviewer_set = {c.identity() for c in reviewers}
    rows = []
    for claim in primary:
        row = claim.to_dict()
        if reviewer_set is not None and claim.identity() not in reviewer_set:
            row.update({"status": "NEEDS_REVIEW", "kernel_checked": False})
        else:
            checker = lean or LeanChecker(executable="__pcs_missing_lean_executable__")
            row.update(checker.check_arithmetic(claim))
        rows.append(row)
    return {
        "schema_version": "llm-claim-arithmetic-v2-research",
        "authority": "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY",
        "source_sha256": source.digest,
        "source_encoding": "UTF-8 raw bytes; offsets index Unicode codepoints",
        "primary_proposal_sha256": sha(canonical(primary_proposals)),
        "reviewer_proposal_sha256": sha(canonical(reviewer_proposals)) if reviewer_proposals is not None else None,
        "primary": primary_metadata or {"provider": "offline", "model": "local-fixture"},
        "reviewer": reviewer_metadata,
        "scope": ("bounded literal rational expressions only; AST parser and source semantics "
                  "are not Lean-verified; no scientific validity"),
        "claims": rows, "rejected": rejected, "reviewer_rejected": reviewer_rejected,
        "counts": {
            "primary_proposed": len(primary_proposals["claims"]),
            "accepted_grounding": len(primary), "rejected_grounding": len(rejected),
            "kernel_checked": sum(row.get("kernel_checked", False) for row in rows),
            "needs_review": sum(row["status"] == "NEEDS_REVIEW" for row in rows),
        },
    }
