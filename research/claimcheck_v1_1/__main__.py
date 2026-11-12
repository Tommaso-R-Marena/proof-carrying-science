"""ClaimCheck v1.1 command line (research sidecar; no production authority).

Check one number, with a fresh Lean kernel run:

    python -m research.claimcheck_v1_1 verify --data soil.csv \
        --sentence "Soils had a somewhat acidic average pH of 6.07 ± 0.05 SE (range = 5.01–8.03)." \
        --number 6.07 --stat mean --column pH --out bundle/

Check several readings of a paper (a proposals file, as in v1):

    python -m research.claimcheck_v1_1 verify --data d.csv --source paper.txt --manifest manifest.json \
        --proposals proposals.json --out bundle/

Replay a bundle with a program that shares no code with the one that made it:

    python -m research.claimcheck_v1_1 replay bundle/
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ..claimcheck_v1.lean import checker_sha256
from ..claimcheck_v1.spec import sha256_hex
from .verify import _LABEL, verify, write_bundle_v11

HERE = Path(__file__).resolve().parent


def _where(items: list[str]) -> list[dict]:
    out = []
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"--where expects column=label, got {item!r}")
        column, value = item.split("=", 1)
        out.append({"kind": "text_eq", "column": column.strip(), "value": value.strip()})
    return out


def cmd_verify(args) -> int:
    data = Path(args.data).read_bytes()
    if args.source:
        source_text = Path(args.source).read_bytes().decode("utf-8")
        source_name = Path(args.source).name
    elif args.sentence:
        source_text, source_name = args.sentence, "sentence typed on the command line"
    else:
        raise SystemExit("give --source FILE or --sentence TEXT")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8")) if args.manifest else {}
    manifest.setdefault("data_name", Path(args.data).name)
    if args.proposals:
        raw = json.loads(Path(args.proposals).read_text(encoding="utf-8"))
        items = raw["proposals"] if isinstance(raw, dict) else raw
        origin = (raw.get("origin") if isinstance(raw, dict) else None) or "proposals file"
        triples = [(f"c{i + 1:03d}", p, origin) for i, p in enumerate(items)]
    else:
        if not (args.number and args.stat):
            raise SystemExit("give --proposals FILE, or --number and --stat (and --column) for one claim")
        spec = {"stat": args.stat, "reported": args.number}
        if args.column:
            spec["column"] = args.column
        if args.x_column:
            spec["x_column"] = args.x_column
        if args.unit:
            spec["reported_unit"] = args.unit
        if args.stat == "share":
            spec["sub_filter"] = _where(args.where)
        else:
            spec["filter"] = _where(args.where)
        quote = args.quote or (args.sentence if args.sentence else None)
        if not quote:
            raise SystemExit("with --source, give --quote: the sentence copied exactly from the paper")
        triples = [("c001", {"quote": quote, "spec": spec}, args.selected_by or "the person running the command")]
    selection = {"proposed_by": args.selected_by or triples[0][2], "saw_the_data": args.saw_data}
    review = None
    if args.reviewer:
        review = {"reviewer": args.reviewer, "statement": args.review_statement or "I read the sentence and it reports this statistic of this column.",
                  "reviewer_saw_the_data": args.reviewer_saw_data, "identity_verified_by_pcs": False}
    out = Path(args.out)
    result = verify(triples, source_text=source_text, source_meta={"name": source_name}, data=data, manifest=manifest, selection=selection,
                    human_review=review, run_lean=not args.no_lean, lean_timeout=args.timeout, keep_dir=out / "v1" / "obligations",
                    workers=args.workers, batch_size=args.batch_size)
    index = write_bundle_v11(out, result, source_text=source_text, data=data, manifest=manifest, source_name=source_name, data_name=Path(args.data).name)
    for r in result["records"]:
        m, s = r["mathematical"], r["source_reading"]
        tag = " (found automatically as supporting evidence)" if r["auxiliary"] else ""
        print(f"\n[{r['claim_id']}]{tag}  {_LABEL[r['outward']['verdict']].upper()}  ({r['outward']['verdict']})")
        print(f"  statement    {m['statement']}")
        print(f"  mathematics  {m['status']}" + ("  — kernel-checked in this run" if m["kernel_run"] else "  — NOT kernel-checked"))
        print(f"  reading      {s['status']}")
        for reason in r["outward"]["reasons"]:
            print(f"               · {reason}")
        print("  science      NOT_ASSESSED")
    if args.no_lean or not any(r["mathematical"]["kernel_run"] for r in result["records"]):
        print("\nNo Lean kernel result was obtained, so nothing is established. Install Lean 4.28.0 "
              "(from the repository root: source scripts/activate_lean_428.sh) and run again.")
    print(f"\ndata SHA-256  {sha256_hex(data)}")
    print(f"report        {out / 'report.html'}")
    print(f"replay        python {HERE / 'replay_independent_v1_1.py'} {out} --checker-sha256 {checker_sha256()}")
    print(json.dumps({"bundle": str(out), "counts": index["counts"]}))
    return 0


def cmd_replay(args) -> int:
    cmd = [sys.executable, str(HERE / "replay_independent_v1_1.py"), args.bundle, "--checker-sha256", args.checker_sha256 or checker_sha256()]
    if args.skip_lean:
        cmd.append("--skip-lean")
    return subprocess.run(cmd).returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m research.claimcheck_v1_1", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="gates, Lean kernel and the v1.1 reading policy; writes a replayable bundle")
    v.add_argument("--data", required=True, help="CSV data file (at most 64 KB)")
    v.add_argument("--source", help="paper text (UTF-8)")
    v.add_argument("--sentence", help="one sentence, when you have no file with the paper's text")
    v.add_argument("--manifest", help="dataset manifest JSON (digest pin, units, aliases, row_unit, missing-value tokens)")
    v.add_argument("--proposals", help="JSON file of proposed readings")
    v.add_argument("--quote", help="the sentence, copied exactly from the paper")
    v.add_argument("--number", help="the number exactly as printed")
    v.add_argument("--stat", help="count, share, sum, mean, median, min, max, sd, sem, var_sample, pearson, ols_slope, ols_intercept")
    v.add_argument("--column")
    v.add_argument("--x-column", dest="x_column")
    v.add_argument("--unit", help="unit printed after the number, if it differs from the data unit")
    v.add_argument("--where", action="append", help="row selection column=label (repeat for a second one)")
    v.add_argument("--selected-by", dest="selected_by", help="who or what chose this reading")
    v.add_argument("--saw-data", dest="saw_data", choices=("yes", "no", "unknown"), default="unknown",
                   help="did whoever chose the reading see the data first? (recorded; the policy assumes yes either way)")
    v.add_argument("--reviewer", help="name of a person who read the paper and confirms the reading (recorded, not verified)")
    v.add_argument("--review-statement", dest="review_statement")
    v.add_argument("--reviewer-saw-data", dest="reviewer_saw_data", choices=("yes", "no", "unknown"), default="unknown")
    v.add_argument("--out", required=True)
    v.add_argument("--no-lean", action="store_true", help="skip the kernel: every result then stays UNKNOWN")
    v.add_argument("--timeout", type=int, default=900)
    v.add_argument("--workers", type=int, default=2)
    v.add_argument("--batch-size", dest="batch_size", type=int, default=4)
    v.set_defaults(func=cmd_verify)
    r = sub.add_parser("replay", help="independent replay of a bundle")
    r.add_argument("bundle")
    r.add_argument("--checker-sha256", dest="checker_sha256")
    r.add_argument("--skip-lean", action="store_true")
    r.set_defaults(func=cmd_replay)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
