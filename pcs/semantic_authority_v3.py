"""Host-pinned, stateful semantic authority; never a scientific truth certificate.

The caller supplies independently approved configuration/binary commitments and a
ClaimIR binding. Only the actual Lean v3 decision followed by the SQLite commit
can certify a translation. Signer honesty, compiler/runtime correspondence,
durable storage and the host clock remain explicit trusted assumptions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import sqlite3
import subprocess
from typing import Any, Callable, Mapping

from pcs_semantic.receipt_store import ReceiptStore, StoreError
from pcs_semantic import receipts_v3 as receipts
from .semantic_claim_binding_v1 import verify_binding
from .semantic_kernel_bridge_v1 import canonical_bytes, digest, strict_decode, _pin

FORMAT = "pcs-semantic-authority-result-v3"
TOOLCHAIN = "leanprover/lean4:v4.28.0"


def regular_file(path: str | Path, limit: int) -> Path:
    path = Path(path).absolute()
    if ".." in path.parts or any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError("SYMLINK_OR_ALIAS_PATH")
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("MISSING_OR_OVERSIZED_FILE")
    return path


def fixture_public_keys() -> set[str]:
    # These eight keys are intentionally public in the supplied fixture writer.
    return {receipts.test_key("pcs-v3-test-" + name + "-seed").public for name in (
        "confirmation", "confirmation2", "elaboration", "proof", "proof2",
        "attacker", "proof-retired", "proof-future")}


class _PinnedStore(ReceiptStore):
    def __init__(self, *args, binary_sha256: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.binary_sha256 = binary_sha256

    def _run_binary(self, *args, **kwargs):
        path = regular_file(self.binary, 64 * 1024 * 1024)
        _pin(path.read_bytes(), self.binary_sha256, "BINARY")
        decision = super()._run_binary(*args, **kwargs)
        # This check runs inside the transaction, before any COMMIT or result.
        _pin(regular_file(path, 64 * 1024 * 1024).read_bytes(), self.binary_sha256, "BINARY")
        canonical_bytes(decision)
        return decision


class SemanticAuthority:
    def __init__(self, *, binary: str | Path, binary_sha256: str,
                 authority_bytes: bytes, authority_sha256: str, store: str | Path,
                 allow_public_fixtures: bool = False,
                 clock: Callable[[], float] = time.time):
        authority = strict_decode(authority_bytes)
        if canonical_bytes(authority) != authority_bytes:
            raise ValueError("NONCANONICAL_AUTHORITY")
        _pin(authority_bytes, authority_sha256, "AUTHORITY")
        if authority.get("schema") != receipts.AUTHORITY_V3_SCHEMA:
            raise ValueError("AUTHORITY_SCHEMA")
        context = authority.get("context")
        if type(context) is not dict or context.get("toolchain") != TOOLCHAIN:
            raise ValueError("AUTHORITY_CONTEXT")
        scope = context.get("scope")
        if type(scope) is not str or not 1 <= len(scope) <= 256:
            raise ValueError("AUTHORITY_SCOPE")
        keys = authority.get("keys")
        if type(keys) is not list or any(type(key) is not dict or type(key.get("key")) is not str for key in keys):
            raise ValueError("AUTHORITY_KEYS")
        if authority.get("require_elaboration") is not True or authority.get("require_proof") is not True:
            raise ValueError("ELABORATION_AND_PROOF_REQUIRED")
        axioms = authority.get("allowed_axioms")
        if type(axioms) is not list or any(type(a) is not str or a not in
                {"propext", "Classical.choice", "Quot.sound"} for a in axioms):
            raise ValueError("UNAPPROVED_AXIOM_POLICY")
        if not allow_public_fixtures and (
            scope.startswith("pcs-fixture-") or
            any(key.get("key") in fixture_public_keys() for key in keys)
        ):
            raise ValueError("PUBLIC_FIXTURE_KEYS_NOT_PRODUCTION")
        path = regular_file(binary, 64 * 1024 * 1024)
        _pin(path.read_bytes(), binary_sha256, "BINARY")
        database = regular_file(store, 64 * 1024 * 1024)
        self.store = _PinnedStore.open(str(database), scope, binary=str(path),
                                      binary_sha256=binary_sha256, timeout=180)
        self.authority_bytes = authority_bytes
        self.authority_sha256 = authority_sha256
        self.binary_sha256 = binary_sha256
        self.scope = scope
        self.clock = clock
        self.fixture_mode = allow_public_fixtures

    def evaluate(self, request_bytes: bytes, *, claim_ir: Mapping[str, Any],
                 binding: Mapping[str, Any], approved_binding_sha256: str,
                 mode: str = "translation") -> dict[str, Any]:
        request_sha = digest(request_bytes)
        try:
            if mode not in ("translation", "strengthening"):
                raise ValueError("UNKNOWN_MODE")
            request = strict_decode(request_bytes)
            if request.get("schema") != receipts.REQUEST_V3_SCHEMA:
                raise ValueError("STATEFUL_V3_REQUEST_REQUIRED")
            if canonical_bytes(request) != request_bytes:
                raise ValueError("NONCANONICAL_REQUEST")
            semantic_request = request["request"]["request"]
            checked_binding = verify_binding(
                claim_ir, semantic_request, authority_sha256=self.authority_sha256,
                request_sha256=request_sha, binding=binding,
                approved_binding_sha256=approved_binding_sha256)
            clock_value = self.clock()
            if type(clock_value) not in (int, float) or not 0 <= clock_value <= 2**53:
                raise ValueError("INVALID_HOST_CLOCK")
            # Never accept a proposer-supplied ledger, time or configuration.
            outcome = self.store.certify(self.authority_bytes, request_bytes,
                                         now=int(clock_value), mode=mode)
            return {"format": FORMAT, "mode": mode, "outcome": outcome.outcome,
                    "semantic_contract_satisfied": outcome.certified,
                    "store_commit_completed": outcome.certified,
                    "production_configuration": not self.fixture_mode,
                    "fixture_keys_have_authority": False,
                    "pcs_scientific_authority": False,
                    "binary_sha256": self.binary_sha256,
                    "authority_sha256": self.authority_sha256,
                    "request_sha256": request_sha, "scope": self.scope,
                    "claim_ir_binding": checked_binding,
                    "consumed_nonces": outcome.consumed,
                    "decision": outcome.decision, "store_error": outcome.store_error,
                    "trust_assumptions": ["honest quorum of separately authorized receipt issuers",
                        "Lean frontend/kernel and compiler/runtime correspondence",
                        "approved interpretation and registry meaning",
                        "SQLite durability, filesystem and trusted host clock"],
                    "limitations": ["Meaning relative to the approved structured interpretation",
                        "Not a proof of human intent, empirical truth or native agent behavior",
                        "Strengthening is a separate result, never translation equivalence"]}
        except (ValueError, KeyError, TypeError, OSError, RuntimeError, StoreError,
                sqlite3.Error, subprocess.SubprocessError, UnicodeError,
                OverflowError, RecursionError) as error:
            return {"format": FORMAT, "mode": mode, "outcome": "REJECTED",
                    "semantic_contract_satisfied": False, "store_commit_completed": False,
                    "pcs_scientific_authority": False, "request_sha256": request_sha,
                    "diagnostics": [type(error).__name__ + ": " + str(error)]}


def add_arguments(parser: argparse.ArgumentParser) -> None:
    for name in ("binary", "approved-binary-sha256", "authority", "approved-authority-sha256",
                 "request", "store", "claim-ir", "binding", "approved-binding-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--mode", choices=["translation", "strengthening"], default="translation")
    parser.add_argument("--allow-public-fixtures", action="store_true")
    parser.add_argument("--fixture-clock", type=int)
    parser.add_argument("-o", "--output")


def run_cli(args) -> int:
    try:
        if args.fixture_clock is not None and not args.allow_public_fixtures:
            raise ValueError("FIXTURE_CLOCK_REQUIRES_FIXTURE_MODE")
        authority = SemanticAuthority(
            binary=args.binary, binary_sha256=args.approved_binary_sha256,
            authority_bytes=regular_file(args.authority, 1_000_000).read_bytes(),
            authority_sha256=args.approved_authority_sha256, store=args.store,
            allow_public_fixtures=args.allow_public_fixtures,
            clock=(lambda: args.fixture_clock) if args.fixture_clock is not None else time.time)
        result = authority.evaluate(
            regular_file(args.request, 1_000_000).read_bytes(),
            claim_ir=strict_decode(regular_file(args.claim_ir, 1_000_000).read_bytes()),
            binding=strict_decode(regular_file(args.binding, 1_000_000).read_bytes()),
            approved_binding_sha256=args.approved_binding_sha256, mode=args.mode)
    except (ValueError, TypeError, OSError, RuntimeError, StoreError, sqlite3.Error,
            subprocess.SubprocessError, UnicodeError) as error:
        result = {"format": FORMAT, "outcome": "REJECTED", "semantic_contract_satisfied": False,
                  "store_commit_completed": False, "pcs_scientific_authority": False,
                  "diagnostics": [type(error).__name__ + ": " + str(error)]}
    raw = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")
    if result.get("semantic_contract_satisfied"):
        return 4 if result["mode"] == "strengthening" else 0
    return 1
