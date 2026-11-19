"""Kernel resource feasibility run (feasibility study part C; protocol 13.7): development and synthetic data only.

    python -m research.claimcheck_v1_1.prospective.capacity_run --out DIR [--phase synthetic|development|both]
    python -m research.claimcheck_v1_1.prospective.capacity_run --out DIR --summarise

Authorised on 2026-11-19 as part C of the feasibility study, and nothing else. No prospective paper,
no model call, no recruitment, no article retrieval.

The run uses the kernel configuration of protocol step 4 (`criteria.json`, C7 `kernel_configuration`):

* two workers;
* one claim per proof file;
* 900 s per file;
* 7 GiB of resident memory per Lean process, enforced by `lean_guard.py` named in
  `PCS_CLAIMCHECK_LEAN`.

The kernel calls are the frozen v1 ones, unchanged: `lean.check_items` for the synthetic tables and
`pipeline.verify_many` (`batch_size=1`, `workers=2`, `lean_timeout=900`) for the development claims.

* **Synthetic:** the deterministic tables of `perf/benchmark.py`, on a finer size grid than `perf`
  (to locate each statistic's boundary), and the same six statistics with the same claim shapes.
* **Development:** every claim the four v1 arms proposed on the 19 development documents (8 tables),
  from cached proposals only (`allow_network=False`; model arms read their cached responses).

Every run is appended to `runs.jsonl` as it finishes, so an interrupted run resumes where it
stopped. Peak memory comes from the guard's log, joined by obligation digest. `--summarise` writes
`summary.json`: C7's metrics, a candidate supported size per statistic and kernel hours. All of it
is a development-set finding that enters no criterion; the protocol stays unapproved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

WORKERS = 2
TIMEOUT_S = 900
MEMORY_LIMIT_MB = 7 * 1024
SIZES = (50, 100, 200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1600, 2000, 2400, 2800)
STATS = ("count", "mean", "min", "sd_sample", "median", "pearson")
C7 = {"max_median_seconds_per_claim": 60, "max_p95_seconds_per_claim": 300, "max_peak_memory_gb": 8, "min_completed_share": 0.95}
_LOCK = threading.Lock()


def _append(path: Path, rec: dict) -> None:
    with _LOCK, open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.exists() else []


def _prepare(out: Path, real_lean: str) -> Path:
    from .lean_guard import make_guarded_lean
    exe = make_guarded_lean(out, real_lean, MEMORY_LIMIT_MB, out / "guard.jsonl")
    os.environ["PCS_CLAIMCHECK_LEAN"] = str(exe)
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY"):    # no model call can be made
        os.environ.pop(key, None)
    return exe


def synthetic(out: Path) -> None:
    from ...claimcheck_v1.lean import check_items
    from ...claimcheck_v1.oracle import evaluate
    from ...claimcheck_v1.spec import ClaimSpec
    from ..perf.benchmark import table
    runs = out / "runs.jsonl"
    done = {r["key"] for r in _read(runs) if r["phase"] == "synthetic"}
    todo = [(rows, stat) for rows in SIZES for stat in STATS if f"synthetic:{rows}:{stat}" not in done]

    def one(job):
        rows, stat = job
        data = table(rows)
        spec = ClaimSpec(stat, "1", None if stat == "count" else "x", "y" if stat == "pearson" else None)   # as perf/benchmark.py
        na, scale = ("", "NA"), Fraction(1)
        rec = check_items(data, [(spec, na, scale, evaluate(data, spec, na, scale))], timeout=TIMEOUT_S)[0]
        _append(runs, {"phase": "synthetic", "key": f"synthetic:{rows}:{stat}", "statistic": stat, "rows": rows, "table_bytes": len(data),
                       "seconds": rec.get("batch_seconds"), "kernel_accepted": bool(rec.get("kernel_accepted")),
                       "detail": str(rec.get("detail", ""))[:200], "obligation_sha256": rec.get("obligation_sha256")})

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(one, todo))


def development(out: Path) -> None:
    from ...claimcheck_v1.pipeline import verify_many
    from ...claimcheck_v1.tools.analyze import arm_proposals
    from ..dev.common import SPLITS, documents
    runs = out / "runs.jsonl"
    done = {r["document"] for r in _read(runs) if r["phase"] == "development"}
    for split, results in SPLITS.items():
        for doc in documents(split):
            if doc.key in done:
                continue
            arms = arm_proposals(doc, results)                      # cached proposals only; no network
            seen, props = set(), []
            for arm, proposals in arms.items():
                if arm == "union":
                    continue
                for p in proposals:
                    k = json.dumps(p, sort_keys=True)
                    if k not in seen:
                        seen.add(k)
                        props.append(p)
            triples = [(f"cap{i:04d}", p, "capacity run (development)") for i, p in enumerate(props)]
            receipts = verify_many(triples, source_text=doc.text, source_meta={}, data=doc.data, manifest=doc.manifest,
                                   run_lean=True, lean_timeout=TIMEOUT_S, workers=WORKERS, batch_size=1)
            table_sha = hashlib.sha256(doc.data).hexdigest()
            for r in receipts:
                for v in (r.get("q1_mathematics") or {}).get("variants") or []:
                    lean = v.get("lean") or {}
                    if "batch_seconds" not in lean:
                        continue                                    # not sent to the kernel
                    _append(runs, {"phase": "development", "document": doc.key, "split": split, "table_sha256": table_sha,
                                   "table_bytes": len(doc.data), "statistic": v.get("stat"), "seconds": lean.get("batch_seconds"),
                                   "kernel_accepted": bool(lean.get("kernel_accepted")), "detail": str(lean.get("detail", ""))[:200],
                                   "obligation_sha256": lean.get("obligation_sha256")})
            _append(runs, {"phase": "development-document-done", "document": doc.key, "claims": len(props)})


def rerun_killed(out: Path, real_lean: str) -> list[dict]:
    """Re-run, one at a time, every run the operating system killed (guard exit -9): two concurrent Lean
    processes near the 7 GiB limit can exceed the machine's memory, and the kernel then kills one
    before the guard does.  A single run separates "needs more than 7 GiB" from "killed by
    contention".  Same guard limit and timeout; its own guard log (`rerun/guard.jsonl`); results in
    `rerun/runs.jsonl`.  Obligations are rebuilt exactly and matched by digest."""
    from ...claimcheck_v1.lean import batch_source, check_items
    from ...claimcheck_v1.oracle import evaluate
    from ...claimcheck_v1.pipeline import DEFAULT_NA, _prepare
    from ...claimcheck_v1.spec import ClaimSpec
    from ..perf.benchmark import table
    from .lean_guard import make_guarded_lean
    killed = {g["obligation_sha256"] for g in _read(out / "guard.jsonl")
              if g.get("event") == "finished" and g.get("exit") == -9 and g.get("obligation_sha256")}
    targets = [r for r in _read(out / "runs.jsonl") if r.get("obligation_sha256") in killed]
    rdir = out / "rerun"
    rdir.mkdir(exist_ok=True)
    os.environ["PCS_CLAIMCHECK_LEAN"] = str(make_guarded_lean(rdir, real_lean, MEMORY_LIMIT_MB, rdir / "guard.jsonl"))
    done = {r["obligation_sha256"] for r in _read(rdir / "runs.jsonl")}
    docs = {}
    if any(r["phase"] == "development" for r in targets):
        from ...claimcheck_v1.tools.analyze import arm_proposals
        from ..dev.common import SPLITS, documents
        for split, results in SPLITS.items():
            for doc in documents(split):
                docs[doc.key] = (doc, results)
    results_out = []
    for r in targets:
        if r["obligation_sha256"] in done:
            continue
        if r["phase"] == "synthetic":
            data = table(r["rows"])
            stat = r["statistic"]
            spec = ClaimSpec(stat, "1", None if stat == "count" else "x", "y" if stat == "pearson" else None)
            item = (spec, ("", "NA"), Fraction(1), evaluate(data, spec, ("", "NA"), Fraction(1)))
        else:
            doc, results = docs[r["document"]]
            item = None
            for arm, proposals in arm_proposals(doc, results).items():
                for i, p in enumerate(proposals):
                    pend = _prepare(p, source_text=doc.text, source_meta={}, data=doc.data, manifest=doc.manifest, origin="rerun",
                                    claim_id=f"r{i}")
                    for concrete, _a, outcome, _ in getattr(pend, "variants", []):
                        cand = (concrete, tuple(doc.manifest.get("na_tokens") or DEFAULT_NA), pend.scale, outcome)
                        if hashlib.sha256(batch_source(doc.data, [cand]).encode("utf-8")).hexdigest() == r["obligation_sha256"]:
                            item = cand
                            break
                    if item:
                        break
                if item:
                    break
            if item is None:
                _append(rdir / "runs.jsonl", {"obligation_sha256": r["obligation_sha256"], "rebuilt": False})
                continue
            data = doc.data
        rec = check_items(data, [item], timeout=TIMEOUT_S)[0]
        row = {"phase": r["phase"], "statistic": r["statistic"], "table_bytes": r["table_bytes"], "rows": r.get("rows"),
               "document": r.get("document"), "obligation_sha256": rec.get("obligation_sha256"), "rebuilt": True,
               "same_obligation": rec.get("obligation_sha256") == r["obligation_sha256"], "single_worker": True,
               "seconds": rec.get("batch_seconds"), "kernel_accepted": bool(rec.get("kernel_accepted")), "detail": str(rec.get("detail", ""))[:200]}
        _append(rdir / "runs.jsonl", row)
        results_out.append(row)
    return results_out


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    return v[max(0, math.ceil(q * len(v)) - 1)]


def summarise(out: Path) -> dict:
    """C7's metrics, a candidate supported size per statistic, kernel hours.  Pure function of the logs."""
    runs = [r for r in _read(out / "runs.jsonl") if r["phase"] in ("synthetic", "development")]
    guard = [g for g in _read(out / "guard.jsonl") if g.get("event") == "finished" and g.get("obligation_sha256")]
    peak = {}
    for g in guard:
        peak[g["obligation_sha256"]] = max(peak.get(g["obligation_sha256"], 0.0), g["peak_rss_mb"])
    stopped = {g["obligation_sha256"] for g in guard if g.get("stopped_for_memory")}
    for r in runs:
        r["peak_gb"] = round(peak[r["obligation_sha256"]] / 1024, 2) if r.get("obligation_sha256") in peak else None
        r["stopped_for_memory"] = r.get("obligation_sha256") in stopped

    def block(rs: list[dict]) -> dict:
        secs = [r["seconds"] for r in rs if r["seconds"] is not None]
        peaks = [r["peak_gb"] for r in rs if r["peak_gb"] is not None]
        done = sum(1 for r in rs if r["kernel_accepted"])
        b = {"runs": len(rs), "completed": done, "completed_share": round(done / len(rs), 4) if rs else None,
             "median_seconds": round(statistics.median(secs), 2) if secs else None, "p95_seconds": _pct(secs, 0.95),
             "max_seconds": max(secs) if secs else None, "max_peak_gb": max(peaks) if peaks else None,
             "stopped_for_memory": sum(1 for r in rs if r["stopped_for_memory"]),
             "timed_out": sum(1 for r in rs if "timed out" in r["detail"]), "kernel_hours": round(sum(secs) / 3600, 3)}
        b["c7_limits_hold"] = bool(rs and b["median_seconds"] is not None and b["median_seconds"] <= C7["max_median_seconds_per_claim"]
                                   and b["p95_seconds"] <= C7["max_p95_seconds_per_claim"]
                                   and (b["max_peak_gb"] or 0) <= C7["max_peak_memory_gb"] and b["completed_share"] >= C7["min_completed_share"])
        return b

    syn = [r for r in runs if r["phase"] == "synthetic"]
    dev = [r for r in runs if r["phase"] == "development"]
    supported = {}
    for stat in STATS:
        ok_bytes = None
        for r in sorted((r for r in syn if r["statistic"] == stat), key=lambda r: r["rows"]):
            fine = r["kernel_accepted"] and r["seconds"] is not None and r["seconds"] <= C7["max_p95_seconds_per_claim"] \
                and (r["peak_gb"] or 0) <= C7["max_peak_memory_gb"]
            if not fine:
                break                                               # the boundary: the first size that fails, and above
            ok_bytes = r["table_bytes"]
        supported[stat] = ok_bytes
    by_stat_size = {}
    for r in syn:
        by_stat_size.setdefault(r["statistic"], []).append({k: r[k] for k in ("rows", "table_bytes", "seconds", "peak_gb", "kernel_accepted",
                                                                               "stopped_for_memory", "detail")})
    for v in by_stat_size.values():
        v.sort(key=lambda x: x["rows"])
    dev_by_stat = {}
    for r in dev:
        dev_by_stat.setdefault(r["statistic"], []).append(r)
    by_doc = {}
    for r in dev:
        by_doc.setdefault(r["document"].split(":")[0], []).append(r)
    per_paper_hours = [sum(x["seconds"] or 0 for x in rs) / 3600 for rs in by_doc.values()]
    # the prospective design has two documents per paper: the original and its planted-error copy
    pair = {}
    for r in dev:
        slug, variant = r["document"].split(":")
        if variant in ("original", "mutated"):
            pair.setdefault(slug, []).append(r)
    pair_hours = [sum(x["seconds"] or 0 for x in rs) / 3600 for rs in pair.values()]
    measured = [v for v in supported.values() if v is not None]
    smallest = min(measured) if measured else None

    def size_for(stat: str):
        if stat in supported:
            return supported[stat]
        if stat in ("sd", "sd_pop"):
            return supported.get("sd_sample")
        return smallest

    def inside(r: dict) -> bool:
        limit = size_for(r["statistic"])
        return limit is not None and r["table_bytes"] <= limit

    within = [r for r in dev if inside(r)]
    outside = [r for r in dev if not inside(r)]
    return {
        "what": "Feasibility study part C (protocol 13.7): development and synthetic data only. A development-set finding; it enters no criterion. "
                "The protocol (draft 3) stays unapproved.",
        "configuration": {"workers": WORKERS, "claims_per_proof_file": 1, "seconds_per_proof_file": TIMEOUT_S,
                          "memory_limit_mb_per_lean_process": MEMORY_LIMIT_MB, "memory_limit_enforced_by": "prospective/lean_guard.py",
                          "c7_limits": C7},
        "synthetic": {"overall": block(syn), "candidate_supported_size_bytes": supported, "runs_by_statistic": by_stat_size},
        "development": {"overall": block(dev), "by_statistic": {s: block(rs) for s, rs in sorted(dev_by_stat.items())},
                        "within_candidate_supported_size": {
                            "rule": "a run counts if its table is no larger than the candidate supported size of its statistic (sd and sd_pop take "
                                    "sd_sample's; a statistic not measured takes the smallest measured size), as C7 is defined",
                            **block(within)},
                        "outside_candidate_supported_size": block(outside),
                        "papers": len(by_doc), "kernel_hours_per_paper_with_its_copies": {
                            "mean": round(statistics.mean(per_paper_hours), 3) if per_paper_hours else None,
                            "max": round(max(per_paper_hours), 3) if per_paper_hours else None},
                        "kernel_hours_per_paper_original_plus_planted_copy": {
                            "papers": len(pair_hours),
                            "mean": round(statistics.mean(pair_hours), 3) if pair_hours else None,
                            "max": round(max(pair_hours), 3) if pair_hours else None,
                            "note": "all four v1 arms' distinct claims (rules, search, Gemini, Nemotron); one claim per proof file"}},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--phase", choices=("synthetic", "development", "both"), default="both")
    ap.add_argument("--lean", default=None, help="the real Lean 4.28.0 executable (default: lean on PATH)")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--rerun-killed", action="store_true", help="re-run, one at a time, the runs the operating system killed")
    args = ap.parse_args(argv)
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.summarise:
        s = summarise(args.out)
        (args.out / "summary.json").write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({k: s[k]["overall"] for k in ("synthetic", "development")}, indent=1))
        return 0
    import shutil
    real = args.lean or shutil.which("lean")
    if not real:
        raise SystemExit("Lean 4.28.0 not found")
    if args.rerun_killed:
        for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY"):
            os.environ.pop(key, None)
        print(json.dumps(rerun_killed(args.out, real), indent=1))
        return 0
    _prepare(args.out, real)
    meta = args.out / "host.json"
    if not meta.exists():
        from ...claimcheck_v1.lean import lean_version
        mem = next((int(x.split()[1]) for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemTotal:")), None)
        meta.write_text(json.dumps({"lean": lean_version(real), "host": platform.platform(), "cpus": os.cpu_count(),
                                    "mem_total_kb": mem, "python": sys.version.split()[0],
                                    "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=1) + "\n", encoding="utf-8")
    if args.phase in ("synthetic", "both"):
        synthetic(args.out)
    if args.phase in ("development", "both"):
        development(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
