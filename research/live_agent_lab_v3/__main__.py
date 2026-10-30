"""Usable local lab; no production registrations, web server or arbitrary tools."""
import argparse
from contextlib import contextmanager
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

from .protocol import HERE,standard_plan,check_plan,FORMAT


def require_tokenizer():
    try:ok=importlib.metadata.version("tokenizers")=="0.22.2"
    except importlib.metadata.PackageNotFoundError:ok=False
    if not ok:raise ModuleNotFoundError("Install the pinned standalone token checker")


@contextmanager
def decoder(path):
    require_tokenizer()
    from research.real_model_execution_v2.artifacts import fetch
    from research.real_model_execution_v2.oracle import Oracle
    if path is not None:yield Oracle(path);return
    print("Preparing pinned decoder files (~11 MB; no neural weights).",file=sys.stderr,flush=True)
    with tempfile.TemporaryDirectory(prefix="pcs-lab-decoder-") as tmp:
        root=Path(tmp)/"files";fetch(root);yield Oracle(root)


def main():
    p=argparse.ArgumentParser(description="See and replay real-model proposals through the fixed PCS workflow.")
    sub=p.add_subparsers(dest="command",required=True)
    d=sub.add_parser("doctor",help="Explain setup without running inference or proofs")
    for flag in ("tokenizer","bundle","dependencies"):d.add_argument("--"+flag,type=Path)
    d.add_argument("--json",action="store_true");d.add_argument("--require",choices=("replay","live"))
    r=sub.add_parser("run",help="Run the real local model against current broker observations")
    r.add_argument("output",type=Path);r.add_argument("--bundle",type=Path);r.add_argument("--dependencies",type=Path)
    r.add_argument("--plan",type=Path);r.add_argument("--case",action="append")
    for name in ("demo","replay"):
        a=sub.add_parser(name,help="Fresh native Lean/SQL replay; recorded model responses")
        if name=="replay":a.add_argument("input",type=Path)
        a.add_argument("output",type=Path);a.add_argument("--tokenizer",type=Path)
    v=sub.add_parser("view",help="Check and render loaded evidence; no kernel-verification claim")
    v.add_argument("input",type=Path);v.add_argument("output",type=Path);v.add_argument("--tokenizer",type=Path)
    args=p.parse_args()
    if args.command=="doctor":
        from .doctor import inspect,human
        result=inspect(args.tokenizer,args.bundle,args.dependencies)
        print(json.dumps(result) if args.json else human(result))
        key="recorded_replay" if args.require=="replay" else "live_model"
        return 3 if args.require and not result["ready_for"][key] else 0
    if args.output.exists():raise FileExistsError("Choose a fresh output path")
    from .intake import read_once,parse,prepare
    from .report import write_report,summary
    if args.command=="run":
        require_tokenizer()
        from .live import run
        plan=check_plan(parse(read_once(args.plan,128*1024))) if args.plan else standard_plan()
        if args.case:
            if args.plan:p.error("Choose --plan or --case, not both")
            if len(args.case)!=len(set(args.case)) or not set(args.case)<={c['id'] for c in plan['cases']}:
                p.error("Use unique case IDs from the standard plan")
            plan["cases"]=[c for c in plan["cases"] if c["id"] in args.case]
        if any(case["id"]=="authority" for case in plan["cases"]):
            p.error("Case ID 'authority' is reserved for the native verifier workspace")
        frozen=run(args.bundle,args.dependencies,args.output,plan,progress=lambda text:print(text,file=sys.stderr,flush=True))
        write_report(frozen,args.output/"report.html","live");mode="live"
    else:
        source=HERE/"demo" if args.command=="demo" else args.input
        with decoder(args.tokenizer) as oracle:
            if args.command=="view":
                frozen=prepare(source,oracle);write_report(frozen,args.output,"loaded");mode="loaded"
            else:
                from .live import replay
                print("Checking recorded responses, rebuilding the pinned Lean authority and replaying SQL. Cold builds can take several minutes.",file=sys.stderr,flush=True)
                frozen=replay(source,oracle,args.output)
                write_report(frozen,args.output/"report.html","replay");mode="replay"
    counts=summary(frozen);report_path=args.output if mode=="loaded" else args.output/"report.html"
    print(f"Open {report_path} in your browser. {'Loaded evidence only; not replayed here.' if mode=='loaded' else 'Local execution checks completed.'}",file=sys.stderr,flush=True)
    print(json.dumps(dict(format=FORMAT,status="COMPLETE",mode=mode,output=str(args.output),report=str(report_path),summary=counts,
                          inference_performed=mode=="live" and counts["model_proposals"]>0,native_execution_checked=mode!="loaded",
                          kernel_replayed=mode=="replay",pcs_authority=False)))
    return 0


if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,ValueError,EOFError,RuntimeError,KeyError,ImportError,sqlite3.Error,subprocess.SubprocessError) as error:
        if isinstance(error,ModuleNotFoundError):next_step="Install: python -m pip install --no-deps --require-hashes -r research/real_model_execution_v2/requirements-tokenizer.lock"
        elif isinstance(error,FileExistsError):next_step="Choose a new output path; existing evidence is never replaced."
        else:next_step="Run doctor, inspect logs, and use a fresh output directory. No success verdict was issued."
        print(json.dumps(dict(format=FORMAT,status="REFUSED_OR_UNAVAILABLE",reason=type(error).__name__,
                              next_step=next_step,completed=False,pcs_authority=False)),file=sys.stderr)
        raise SystemExit(20)
