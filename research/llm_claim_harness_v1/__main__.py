"""Run with `python -m research.llm_claim_harness_v1`."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .core import Source, canonical
from .pipeline import LeanChecker, LocalCache, get_proposals, run, run_arithmetic
from .providers import Provider, ProviderError
from .discovery import discover_standalone


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Experimental PCS source-grounded LLM+Lean harness (NOT production verifier)")
    parser.add_argument("--mode", choices=["literal", "arithmetic"], default="literal",
                        help="Experimental arithmetic mode checks rational expression ASTs in Lean")
    parser.add_argument("--source", type=Path, required=True, help="Plain UTF-8 text only; <=32KiB")
    parser.add_argument("--out", type=Path, required=True, help="Where to write an experimental JSON receipt")
    parser.add_argument("--offline-proposals", type=Path, help="JSON fixture replacing all primary network calls")
    parser.add_argument("--offline-reviewer", type=Path, help="Optional second independent JSON fixture")
    parser.add_argument("--primary", choices=["gemini", "openrouter", "deterministic"])
    parser.add_argument("--primary-model")
    parser.add_argument("--reviewer", choices=["gemini", "openrouter"])
    parser.add_argument("--reviewer-model")
    parser.add_argument("--allow-external", action="store_true", help="Explicit permission to transmit source to API providers")
    parser.add_argument("--cache-dir", type=Path, help="Opt-in local plaintext proposal caching")
    parser.add_argument("--lean", default="lean", help="Path to installed Lean 4 executable")
    parser.add_argument("--require-lean", action="store_true", help="Fail CLI if no checks passed through Lean")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        source = Source.from_bytes(args.source.read_bytes())
        network_needed = (not args.offline_proposals and args.primary != "deterministic") or (args.reviewer and not args.offline_reviewer)
        if network_needed and not args.allow_external:
            raise ValueError("network calls require --allow-external; provide offline fixtures otherwise")
        if not args.offline_proposals and not args.primary:
            raise ValueError("select --primary")
        if not args.offline_proposals and args.primary != "deterministic" and not args.primary_model:
            raise ValueError("external primary requires --primary-model")
        if args.primary == "deterministic" and args.primary_model:
            raise ValueError("deterministic extraction does not use a model")
        if args.reviewer and not args.offline_reviewer and not args.reviewer_model:
            raise ValueError("select --reviewer-model")
        if args.reviewer_model and not args.reviewer:
            raise ValueError("--reviewer-model requires --reviewer")
        if args.offline_reviewer and args.reviewer and not args.allow_external:
            # Entirely offline: allowed. Reviewer fixture wins over remote.
            pass
        cache = LocalCache(args.cache_dir) if args.cache_dir else None
        primary_meta = {"provider": "offline", "model": "local-fixture"}
        reviewer_meta = None
        if args.offline_proposals:
            primary = json.loads(args.offline_proposals.read_text(encoding="utf-8"))
        elif args.primary == "deterministic":
            primary = discover_standalone(source, args.mode)
            primary_meta = {"provider": "deterministic", "model": None, "network_calls": 0}
        else:
            provider = Provider(args.primary, args.primary_model, mode=args.mode)
            primary, hit = get_proposals(provider, source, cache)
            primary_meta = {"provider": provider.kind, "model": provider.model, "cache_hit": hit}
        reviewer = None
        if args.offline_reviewer:
            reviewer = json.loads(args.offline_reviewer.read_text(encoding="utf-8"))
            reviewer_meta = {"provider": "offline", "model": "local-fixture"}
        elif args.reviewer:
            provider = Provider(args.reviewer, args.reviewer_model, mode=args.mode)
            reviewer, hit = get_proposals(provider, source, cache)
            reviewer_meta = {"provider": provider.kind, "model": provider.model, "cache_hit": hit}
        receiver = run_arithmetic if args.mode == "arithmetic" else run
        receipt = receiver(source, primary, reviewer_proposals=reviewer, lean=LeanChecker(args.lean), primary_metadata=primary_meta, reviewer_metadata=reviewer_meta)
        # Refuse symlink targets; caller controls the output path.
        if args.out.is_symlink():
            raise ValueError("output must not be a symbolic link")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        temp = args.out.with_name(args.out.name + ".tmp")
        if temp.is_symlink():
            raise ValueError("temporary output must not be a symbolic link")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(canonical(receipt) + b"\n")
        os.replace(temp, args.out)
        print(f"Experimental PCS receipt: {args.out}")
        print(f"Grounded: {receipt['counts']['accepted_grounding']}; kernel-checked: {receipt['counts']['kernel_checked']}; rejected: {receipt['counts']['rejected_grounding']}; needs-review: {receipt['counts']['needs_review']}")
        if args.require_lean and receipt["counts"]["kernel_checked"] == 0:
            return 2
        return 0
    except (OSError, ValueError, TypeError, ProviderError, json.JSONDecodeError) as exc:
        # Never print provider error payloads or API keys.
        print(f"harness error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
