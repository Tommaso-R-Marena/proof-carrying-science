"""Command line for ClaimCheck v1 (research sidecar; no production authority).

    python -m research.claimcheck_v1 propose --source paper.txt --data data.csv --manifest manifest.json \
        --proposer baseline --out proposals.json
    python -m research.claimcheck_v1 check --source paper.txt --data data.csv --manifest manifest.json \
        --proposals proposals.json --out bundle/
    python research/claimcheck_v1/replay_independent.py bundle/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .bundle import write_bundle
from .pipeline import verify_many


def _load_inputs(args):
    source_text = Path(args.source).read_bytes().decode("utf-8")
    data = Path(args.data).read_bytes()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8")) if args.manifest else {}
    manifest.setdefault("data_name", Path(args.data).name)
    return source_text, data, manifest


def cmd_check(args) -> int:
    source_text, data, manifest = _load_inputs(args)
    raw = json.loads(Path(args.proposals).read_text(encoding="utf-8"))
    items = raw["proposals"] if isinstance(raw, dict) else raw
    origin = (raw.get("origin") if isinstance(raw, dict) else None) or "file"
    out = Path(args.out)
    triples = [(f"c{i + 1:03d}", p, p.pop("origin", origin) if isinstance(p, dict) else origin) for i, p in enumerate(items)]
    receipts = verify_many(
        triples, workers=args.workers, source_text=source_text, source_meta={"name": Path(args.source).name},
        data=data, manifest=manifest, run_lean=not args.no_lean, lean_timeout=args.timeout, keep_dir=out / "obligations",
    )
    index = write_bundle(out, source_text=source_text, data=data, manifest=manifest, receipts=receipts,
                         source_name=Path(args.source).name, data_name=Path(args.data).name)
    print(json.dumps({"bundle": str(out), "counts": index["counts"], "report": str(out / "report.html")}, indent=1))
    return 0


def cmd_propose(args) -> int:
    source_text, data, manifest = _load_inputs(args)
    if args.proposer == "baseline":
        from .baseline import propose_rules
        proposals, meta = propose_rules(source_text, data, manifest), {"origin": "deterministic-rules"}
    elif args.proposer == "search":
        from .baseline import propose_search
        proposals, meta = propose_search(source_text, data, manifest), {"origin": "deterministic-search"}
    else:
        from .propose import propose_with_model
        proposals, meta = propose_with_model(args.proposer, args.model, source_text, data, manifest, allow_network=args.allow_network)
    Path(args.out).write_text(json.dumps({**meta, "proposals": proposals}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"proposals": len(proposals), "out": args.out, **{k: v for k, v in meta.items() if k != "raw"}}, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m research.claimcheck_v1", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "propose"):
        p = sub.add_parser(name)
        p.add_argument("--source", required=True, help="paper text (UTF-8)")
        p.add_argument("--data", required=True, help="CSV data file")
        p.add_argument("--manifest", help="dataset manifest JSON (digest pin, units, aliases, NA tokens)")
        p.add_argument("--out", required=True)
    c = sub.choices["check"]
    c.add_argument("--proposals", required=True)
    c.add_argument("--workers", type=int, default=3)
    c.add_argument("--timeout", type=int, default=600)
    c.add_argument("--no-lean", action="store_true", help="skip the kernel (every verdict then stays UNKNOWN)")
    c.set_defaults(func=cmd_check)
    p = sub.choices["propose"]
    p.add_argument("--proposer", choices=("baseline", "search", "gemini", "openrouter"), default="baseline")
    p.add_argument("--model")
    p.add_argument("--allow-network", action="store_true", help="required before any text is sent to a model provider")
    p.set_defaults(func=cmd_propose)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
