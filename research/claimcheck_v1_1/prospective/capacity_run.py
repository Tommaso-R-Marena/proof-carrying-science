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
from collections import Counter
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


def development(out: Path, max_documents: int | None = None) -> None:
    from ...claimcheck_v1.pipeline import verify_many
    from ...claimcheck_v1.tools.analyze import arm_proposals
    from ..dev.common import SPLITS, documents
    runs = out / "runs.jsonl"
    done = {r["document"] for r in _read(runs) if r["phase"] == "development-document-done"}
    started = 0
    for split, results in SPLITS.items():
        for doc in documents(split):
            if doc.key in done:
                continue
            if max_documents is not None and started >= max_documents:
                return
            started += 1
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


# ---------------------------------------------------------------------------------------------------
# Outcomes.  One label per run, taken from the run's own kernel detail.  The same obligation can occur
# in several runs (an original and its planted copy share unchanged claims) with different outcomes, so
# a run is never labelled from another run's guard record: its peak comes from the guard records of its
# obligation whose exit matches its outcome.
# ---------------------------------------------------------------------------------------------------
OUTCOMES = ("accepted", "memory guard stop", "killed by the operating system", "time limit",
            "kernel rejection: Lean recursion-depth limit", "kernel rejection: other")
RESOURCE_OUTCOMES = ("memory guard stop", "killed by the operating system", "time limit")
HIGH_MEMORY_MB = 5 * 1024          # a documented peak above this: a 6 GiB limit can change the outcome
RESERVE_GB = 1.0                   # kept free for Python, the operating system and anything else in the memory domain


def _finished_by_digest(guard: list[dict]) -> dict[str, list[dict]]:
    fin: dict[str, list[dict]] = {}
    for g in guard:
        if g.get("event") == "finished" and g.get("obligation_sha256"):
            fin.setdefault(g["obligation_sha256"], []).append(g)
    return fin


def classify(r: dict, fin: dict[str, list[dict]]) -> tuple[str, float | None]:
    """The run's outcome and its peak resident memory in MB (None if the guard recorded none)."""
    d = r.get("detail") or ""
    gs = fin.get(r.get("obligation_sha256"), [])
    kills = [g for g in gs if g.get("exit") == -9 and not g.get("stopped_for_memory")]
    if r.get("kernel_accepted"):
        label, match = "accepted", [g for g in gs if g.get("exit") == 0]
    elif "lean guard: memory limit" in d:
        label, match = "memory guard stop", [g for g in gs if g.get("stopped_for_memory")]
    elif d.endswith("no output") and kills:
        label, match = "killed by the operating system", kills
    elif "timed out" in d:
        label, match = "time limit", []
    elif "maximum recursion depth" in d:
        label, match = "kernel rejection: Lean recursion-depth limit", [g for g in gs if g.get("exit") not in (0, -9, 137)]
    else:
        label, match = "kernel rejection: other", [g for g in gs if g.get("exit") != 0]
    peaks = [g["peak_rss_mb"] for g in (match or gs) if g.get("peak_rss_mb") is not None]
    return label, (max(peaks) if peaks else None)


def _annotate(runs: list[dict], guard: list[dict]) -> list[dict]:
    fin = _finished_by_digest(guard)
    for r in runs:
        label, peak = classify(r, fin)
        r["outcome"] = label
        r["peak_gb"] = round(peak / 1024, 2) if peak is not None else None
        r["stopped_for_memory"] = label == "memory guard stop"
        r["killed_by_system"] = label == "killed by the operating system"
    return runs


def outcome(r: dict) -> str:
    return r.get("outcome") or classify(r, {})[0]


def _documented(out: Path) -> list[dict]:
    runs = [r for r in _read(out / "runs.jsonl") if r["phase"] in ("synthetic", "development")]
    return _annotate(runs, _read(out / "guard.jsonl"))


# ---------------------------------------------------------------------------------------------------
# Further configurations, each evaluated separately in its own directory with its own guard log.  The
# documented-configuration results are never changed.
# ---------------------------------------------------------------------------------------------------
def _cgroup_dir() -> Path | None:
    try:
        for line in Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines():
            parts = line.split(":", 2)
            if len(parts) != 3:
                continue
            if "memory" in parts[1].split(","):
                p = Path("/sys/fs/cgroup/memory") / parts[2].lstrip("/")
                if (p / "memory.usage_in_bytes").exists():
                    return p
            if parts[0] == "0" and parts[1] == "":
                p = Path("/sys/fs/cgroup") / parts[2].lstrip("/")
                if (p / "memory.current").exists():
                    return p
    except OSError:
        pass
    return None


class _CgroupSampler:
    """Samples this session's memory cgroup while a phase runs: usage, working set (usage less inactive
    file cache, which the kernel reclaims before it kills anything), the OOM-kill counter and the limit."""

    def __init__(self, interval: float = 0.2):
        self.dir, self.interval = _cgroup_dir(), interval
        self.v1 = bool(self.dir and (self.dir / "memory.usage_in_bytes").exists())
        self.max_usage = self.max_working_set = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _int(self, name: str) -> int | None:
        try:
            v = (self.dir / name).read_text(encoding="ascii").strip()
            return None if v == "max" else int(v)
        except (OSError, ValueError, TypeError):
            return None

    def _key(self, name: str, key: str) -> int | None:
        try:
            for line in (self.dir / name).read_text(encoding="ascii").splitlines():
                k, _, v = line.partition(" ")
                if k == key:
                    return int(v)
        except (OSError, ValueError, TypeError):
            pass
        return None

    def _sample(self) -> None:
        usage = self._int("memory.usage_in_bytes" if self.v1 else "memory.current")
        inactive = self._key("memory.stat", "total_inactive_file" if self.v1 else "inactive_file") or 0
        if usage is not None:
            self.max_usage = max(self.max_usage, usage)
            self.max_working_set = max(self.max_working_set, usage - inactive)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self._sample()

    def _counters(self) -> dict:
        if self.dir is None:
            return {}
        return {"oom_kill": self._key("memory.oom_control" if self.v1 else "memory.events", "oom_kill"),
                "failcnt": self._int("memory.failcnt") if self.v1 else None}

    def start(self) -> None:
        self.started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.before = self._counters()
        if self.dir is not None:
            self._sample()
            self._thread.start()

    def stop(self) -> dict:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join()
        after = self._counters()
        limit = self._int("memory.limit_in_bytes" if self.v1 else "memory.max") if self.dir else None
        return {"cgroup_found": self.dir is not None, "started_utc": self.started,
                "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "limit_bytes": limit,
                "sampled_max_usage_bytes": self.max_usage, "sampled_max_working_set_bytes": self.max_working_set,
                "sample_interval_seconds": self.interval, "counters_before": self.before, "counters_after": after}


def _synthetic_item(rows: int, stat: str):
    from ...claimcheck_v1.oracle import evaluate
    from ...claimcheck_v1.spec import ClaimSpec
    from ..perf.benchmark import table
    data = table(rows)
    spec = ClaimSpec(stat, "1", None if stat == "count" else "x", "y" if stat == "pearson" else None)   # as synthetic()
    return data, (spec, ("", "NA"), Fraction(1), evaluate(data, spec, ("", "NA"), Fraction(1)))


def _rebuild(targets: dict[str, list[dict]]) -> dict[str, tuple]:
    """Rebuild each target obligation exactly, matched by digest: synthetic ones from the generator,
    development ones from the cached proposals (this reads the model arms' cached responses, so it must
    run before any of them is withheld)."""
    from ...claimcheck_v1.lean import batch_source

    def digest(data, item) -> str:
        return hashlib.sha256(batch_source(data, [item]).encode("utf-8")).hexdigest()

    built: dict[str, tuple] = {}
    for d, rs in targets.items():
        if rs[0]["phase"] == "synthetic":
            data, item = _synthetic_item(rs[0]["rows"], rs[0]["statistic"])
            if digest(data, item) == d:
                built[d] = (data, item)
    docs = {r["document"] for rs in targets.values() for r in rs if r["phase"] == "development"}
    if docs:
        from ...claimcheck_v1.pipeline import DEFAULT_NA, _prepare
        from ...claimcheck_v1.tools.analyze import arm_proposals
        from ..dev.common import SPLITS, documents
        for split, results in SPLITS.items():
            for doc in documents(split):
                if doc.key not in docs:
                    continue
                for arm, proposals in arm_proposals(doc, results).items():           # cached proposals only; no network
                    for i, p in enumerate(proposals):
                        pend = _prepare(p, source_text=doc.text, source_meta={}, data=doc.data, manifest=doc.manifest,
                                        origin="capacity rebuild", claim_id=f"r{i}")
                        for concrete, _a, oc, _ in getattr(pend, "variants", []):
                            cand = (concrete, tuple(doc.manifest.get("na_tokens") or DEFAULT_NA), pend.scale, oc)
                            d = digest(doc.data, cand)
                            if d in targets and d not in built:
                                built[d] = (doc.data, cand)
    return built


def targets_killed(out: Path) -> dict[str, list[dict]]:
    """Every obligation the operating system killed under the documented configuration."""
    t: dict[str, list[dict]] = {}
    for r in _documented(out):
        if r["outcome"] == "killed by the operating system":
            t.setdefault(r["obligation_sha256"], []).append(r)
    return t


def targets_high_memory(out: Path) -> dict[str, list[dict]]:
    """Every obligation (synthetic and development) with a documented peak above 5 GiB, with all its runs."""
    fin = _finished_by_digest(_read(out / "guard.jsonl"))
    high = {d for d, gs in fin.items() if max(g.get("peak_rss_mb") or 0 for g in gs) > HIGH_MEMORY_MB}
    t: dict[str, list[dict]] = {}
    for r in _documented(out):
        if r.get("obligation_sha256") in high:
            t.setdefault(r["obligation_sha256"], []).append(r)
    return t


def worst_case_gb(workers: int, memory_limit_mb: int, overshoot_mb: float, other_mb: float) -> float:
    """Analytic worst case for the memory domain: every worker at its limit plus the guard's largest
    observed overshoot, plus the driver and guard processes."""
    return round((workers * (memory_limit_mb + overshoot_mb) + other_mb) / 1024, 3)


def run_phase(out: Path, name: str, targets: dict[str, list[dict]], real_lean: str, workers: int, memory_limit_mb: int,
              purpose: str) -> dict:
    """Run `targets` once each under `workers` x `memory_limit_mb`, into `out/name/` (runs.jsonl, guard.jsonl,
    phase.jsonl).  Resumable.  Records the memory cgroup throughout."""
    from ...claimcheck_v1.lean import check_items
    from .lean_guard import make_guarded_lean
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY"):    # no model call can be made
        os.environ.pop(key, None)
    pdir = out / name
    pdir.mkdir(exist_ok=True)
    os.environ["PCS_CLAIMCHECK_LEAN"] = str(make_guarded_lean(pdir, real_lean, memory_limit_mb, pdir / "guard.jsonl"))
    done = {r.get("target_obligation_sha256") for r in _read(pdir / "runs.jsonl")}
    todo = {d: rs for d, rs in targets.items() if d not in done}
    built = _rebuild(todo)
    for d in sorted(set(todo) - set(built)):
        _append(pdir / "runs.jsonl", {"phase": name, "target_obligation_sha256": d, "rebuilt": False})
    order = sorted(built, key=lambda d: (todo[d][0]["phase"], todo[d][0]["statistic"], todo[d][0]["table_bytes"], d))

    def one(d: str) -> None:
        data, item = built[d]
        rec = check_items(data, [item], timeout=TIMEOUT_S)[0]
        rs = todo[d]
        _append(pdir / "runs.jsonl", {
            "phase": name, "workers": workers, "memory_limit_mb": memory_limit_mb, "target_obligation_sha256": d,
            "obligation_sha256": rec.get("obligation_sha256"), "same_obligation": rec.get("obligation_sha256") == d, "rebuilt": True,
            "statistic": rs[0]["statistic"], "table_bytes": rs[0]["table_bytes"], "rows": rs[0].get("rows"),
            "documented_runs": [{"phase": r["phase"], "document": r.get("document"), "outcome": r["outcome"], "seconds": r["seconds"],
                                 "peak_gb": r["peak_gb"]} for r in rs],
            "seconds": rec.get("batch_seconds"), "kernel_accepted": bool(rec.get("kernel_accepted")),
            "detail": str(rec.get("detail", ""))[:200]})

    sampler = _CgroupSampler()
    sampler.start()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, order))
    rec = {"phase": name, "purpose": purpose, "workers": workers, "memory_limit_mb": memory_limit_mb, "targets": len(targets),
           "run_now": len(order), **sampler.stop()}
    _append(pdir / "phase.jsonl", rec)
    return rec


PHASES = {
    # name: (workers, memory limit MB, targets, purpose)
    "rerun": (1, 7 * 1024, targets_killed,
              "isolated reruns: every obligation the operating system killed, one at a time, at the documented 7 GiB limit"),
    "safer_6gib": (2, 6 * 1024, targets_high_memory,
                   "the proposed safer configuration: two workers at 6 GiB, on every obligation whose documented peak exceeded 5 GiB"),
    "single_7gib": (1, 7 * 1024, targets_high_memory,
                    "reduced concurrency: one worker at the documented 7 GiB, on the same obligations"),
}


def phase_results(out: Path, name: str) -> tuple[list[dict], dict | None]:
    """A phase's runs, labelled from its own guard log, and its last phase record."""
    pdir = out / name
    runs = [r for r in _read(pdir / "runs.jsonl") if r.get("rebuilt")]
    _annotate(runs, _read(pdir / "guard.jsonl"))
    recs = _read(pdir / "phase.jsonl")
    return runs, (recs[-1] if recs else None)


def safety(out: Path, name: str) -> dict | None:
    """The rule fixed before the further configurations were run: a configuration is safe on this machine
    only if (1) its analytic worst case leaves RESERVE_GB of the memory limit free, (2) no run was killed
    by the operating system and the cgroup's OOM-kill counter did not move, and (3) the sampled working
    set stayed RESERVE_GB below the limit."""
    runs, rec = phase_results(out, name)
    if rec is None:
        return None
    fin = [g for g in _read(out / name / "guard.jsonl") if g.get("event") == "finished"]
    doc_fin = [g for g in _read(out / "guard.jsonl") if g.get("event") == "finished"]
    over = max([g["peak_rss_mb"] - g["memory_limit_mb"] for g in fin + doc_fin if g.get("stopped_for_memory")] or [0.0])
    limit_gb = (rec.get("limit_bytes") or 0) / 1024 ** 3
    other_mb = 128.0          # the driver and one guard per worker, measured at about 26 MB and 16 MB; rounded up generously
    wc = worst_case_gb(rec["workers"], rec["memory_limit_mb"], over, other_mb)
    b, a = rec.get("counters_before") or {}, rec.get("counters_after") or {}
    oom_moved = None if b.get("oom_kill") is None or a.get("oom_kill") is None else a["oom_kill"] - b["oom_kill"]
    killed = sum(1 for r in runs if r["outcome"] == "killed by the operating system")
    ws_gb = rec["sampled_max_working_set_bytes"] / 1024 ** 3
    checks = {"worst_case_leaves_reserve": bool(limit_gb) and wc <= limit_gb - RESERVE_GB,
              "no_system_kill": killed == 0 and (oom_moved in (0, None)),
              "sampled_working_set_leaves_reserve": bool(limit_gb) and ws_gb <= limit_gb - RESERVE_GB}
    return {"phase": name, "workers": rec["workers"], "memory_limit_gb": rec["memory_limit_mb"] / 1024, "limit_gb": round(limit_gb, 3),
            "reserve_gb": RESERVE_GB, "largest_guard_overshoot_mb": round(over, 1), "worst_case_gb": wc,
            "sampled_max_working_set_gb": round(ws_gb, 3), "sampled_max_usage_gb": round(rec["sampled_max_usage_bytes"] / 1024 ** 3, 3),
            "system_kills": killed, "oom_kill_counter_change": oom_moved, **checks, "safe_on_this_machine": all(checks.values())}


def _boundary(rows_sorted: list[dict]) -> int | None:
    ok = None
    for r in rows_sorted:
        if not (r["kernel_accepted"] and r["seconds"] is not None and r["seconds"] <= C7["max_p95_seconds_per_claim"]
                and (r["peak_gb"] or 0) <= C7["max_peak_memory_gb"]):
            break                                                   # the boundary: the first size that fails, and above
        ok = r["table_bytes"]
    return ok


def supported_sizes(out: Path, name: str | None = None) -> dict[str, int | None]:
    """Candidate supported size per statistic under the documented configuration, or under phase `name`:
    a synthetic case the phase re-ran takes the phase's result; every other case (documented peak at most
    5 GiB, which a 6 GiB limit cannot change) keeps its documented result."""
    syn = [r for r in _documented(out) if r["phase"] == "synthetic"]
    if name is not None:
        redo = {r["target_obligation_sha256"]: r for r in phase_results(out, name)[0]}
        syn = [{**r, **{k: redo[r["obligation_sha256"]][k] for k in ("kernel_accepted", "seconds", "peak_gb", "outcome")}}
               if r["obligation_sha256"] in redo else r for r in syn]
    return {stat: _boundary(sorted((r for r in syn if r["statistic"] == stat), key=lambda r: r["rows"])) for stat in STATS}


def repeat_variation(out: Path) -> dict:
    """How far one obligation's peak memory and time vary between runs that completed both times: the same
    obligation run twice in the documented configuration (an original and its planted copy), and once more
    in the single-worker phase at the same limit."""
    fin = _finished_by_digest(_read(out / "guard.jsonl"))
    pairs = []
    for gs in fin.values():
        ok = [g for g in gs if g.get("exit") == 0]
        if len(ok) >= 2:
            pairs.append((ok[0], ok[1]))
    single = _finished_by_digest(_read(out / "single_7gib" / "guard.jsonl"))
    cross = [(fin[d][0], g[0]) for d, g in single.items() if d in fin and g and g[0].get("exit") == 0 and fin[d][0].get("exit") == 0]

    def stats(ps):
        if not ps:
            return None
        dm = sorted(abs(a["peak_rss_mb"] - b["peak_rss_mb"]) for a, b in ps)
        rel = sorted(abs(a["seconds"] - b["seconds"]) / max(a["seconds"], b["seconds"]) for a, b in ps)
        return {"pairs": len(ps), "peak_difference_mb_median": round(statistics.median(dm), 1), "peak_difference_mb_max": round(dm[-1], 1),
                "time_difference_relative_median": round(statistics.median(rel), 3), "time_difference_relative_max": round(rel[-1], 3)}
    return {"documented_twice": stats(pairs), "documented_vs_single_worker": stats(cross)}


def projection(out: Path) -> dict:
    """Kernel time per paper observed on the development set, and the wall time it would imply for 60 and
    120 papers.  The per-paper figures are observations; the totals are projections (perfect packing, papers
    like the development papers), not measurements."""
    dev = [r for r in _documented(out) if r["phase"] == "development"]
    pair: dict[str, list[dict]] = {}
    for r in dev:
        slug, variant = r["document"].split(":")
        if variant in ("original", "mutated"):
            pair.setdefault(slug, []).append(r)
    hours = sorted(sum(x["seconds"] or 0 for x in rs) / 3600 for rs in pair.values())
    claims = sorted(len(rs) for rs in pair.values())
    if not hours:
        return {"observed": None, "projected_wall_hours": {}}
    p = {"observed": {"papers": len(hours), "kernel_hours_per_paper_mean": round(statistics.mean(hours), 3),
                      "kernel_hours_per_paper_median": round(statistics.median(hours), 3), "kernel_hours_per_paper_max": round(hours[-1], 3),
                      "kernel_runs_per_paper_mean": round(statistics.mean(claims), 1), "kernel_runs_per_paper_max": claims[-1]},
         "projected_wall_hours": {}}
    for n in (60, 120):
        for w in (1, 2):
            p["projected_wall_hours"][f"{n}_papers_{w}_worker{'s' if w > 1 else ''}"] = {
                "at_mean": round(n * statistics.mean(hours) / w, 1), "if_every_paper_were_the_slowest": round(n * hours[-1] / w, 1)}
    return p


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    return v[max(0, math.ceil(q * len(v)) - 1)]


def _block(rs: list[dict]) -> dict:
    secs = [r["seconds"] for r in rs if r["seconds"] is not None]
    peaks = [r["peak_gb"] for r in rs if r["peak_gb"] is not None]
    done = sum(1 for r in rs if r["kernel_accepted"])
    c = Counter(r["outcome"] for r in rs)
    b = {"runs": len(rs), "completed": done, "completed_share": round(done / len(rs), 4) if rs else None,
         "outcomes": {k: c.get(k, 0) for k in OUTCOMES}, "resource_unknown": sum(c.get(k, 0) for k in RESOURCE_OUTCOMES),
         "median_seconds": round(statistics.median(secs), 2) if secs else None, "p95_seconds": _pct(secs, 0.95),
         "max_seconds": max(secs) if secs else None, "max_peak_gb": max(peaks) if peaks else None,
         "stopped_for_memory": c.get("memory guard stop", 0), "killed_by_system": c.get("killed by the operating system", 0),
         "timed_out": c.get("time limit", 0), "kernel_hours": round(sum(secs) / 3600, 3)}
    b["c7_limits_hold"] = bool(rs and b["median_seconds"] is not None and b["median_seconds"] <= C7["max_median_seconds_per_claim"]
                               and b["p95_seconds"] <= C7["max_p95_seconds_per_claim"]
                               and (b["max_peak_gb"] or 0) <= C7["max_peak_memory_gb"] and b["completed_share"] >= C7["min_completed_share"])
    return b


def summarise(out: Path) -> dict:
    """C7's metrics, candidate supported sizes, kernel hours, the further configurations.  Pure function of the logs."""
    runs = _documented(out)
    syn = [r for r in runs if r["phase"] == "synthetic"]
    dev = [r for r in runs if r["phase"] == "development"]
    supported = supported_sizes(out)
    by_stat_size: dict[str, list[dict]] = {}
    for r in syn:
        by_stat_size.setdefault(r["statistic"], []).append({k: r[k] for k in ("rows", "table_bytes", "seconds", "peak_gb", "kernel_accepted",
                                                                               "outcome", "detail")})
    for v in by_stat_size.values():
        v.sort(key=lambda x: x["rows"])
    dev_by_stat: dict[str, list[dict]] = {}
    for r in dev:
        dev_by_stat.setdefault(r["statistic"], []).append(r)
    by_doc: dict[str, list[dict]] = {}
    for r in dev:
        by_doc.setdefault(r["document"].split(":")[0], []).append(r)
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
    phases = {}
    for name in PHASES:
        prs, rec = phase_results(out, name)
        if rec is not None:
            phases[name] = {"runs": _block(prs), "safety": safety(out, name),
                            "candidate_supported_size_bytes": supported_sizes(out, name) if name != "rerun" else None}
    return {
        "what": "Feasibility study part C (protocol 13.7): development and synthetic data only. A development-set finding; it enters no criterion. "
                "The protocol (draft 3) stays unapproved.",
        "configuration": {"workers": WORKERS, "claims_per_proof_file": 1, "seconds_per_proof_file": TIMEOUT_S,
                          "memory_limit_mb_per_lean_process": MEMORY_LIMIT_MB, "memory_limit_enforced_by": "prospective/lean_guard.py",
                          "c7_limits": C7},
        "synthetic": {"overall": _block(syn), "by_statistic": {s: _block([r for r in syn if r["statistic"] == s]) for s in STATS},
                      "candidate_supported_size_bytes": supported, "runs_by_statistic": by_stat_size},
        "development": {"overall": _block(dev), "by_statistic": {s: _block(rs) for s, rs in sorted(dev_by_stat.items())},
                        "by_paper": {p: _block(rs) for p, rs in sorted(by_doc.items())},
                        "within_candidate_supported_size": {
                            "rule": "a run counts if its table is no larger than the candidate supported size of its statistic (sd and sd_pop take "
                                    "sd_sample's; a statistic not measured takes the smallest measured size), as C7 is defined",
                            **_block(within)},
                        "outside_candidate_supported_size": _block(outside),
                        "papers": len(by_doc)},
        "record_validation": validate(out),
        "infrastructure": infrastructure(out),
        "further_configurations": phases,
        "repeat_variation": repeat_variation(out),
        "projection": projection(out),
    }


def validate(out: Path) -> dict:
    """Checks of the result records themselves, before anything is reported from them."""
    rows = _read(out / "runs.jsonl")
    runs = [r for r in rows if r.get("phase") in ("synthetic", "development")]
    need = ("phase", "statistic", "table_bytes", "seconds", "kernel_accepted", "detail", "obligation_sha256")
    malformed = [i for i, r in enumerate(runs) if any(k not in r for k in need) or not isinstance(r.get("obligation_sha256"), str)
                 or len(r["obligation_sha256"]) != 64]
    syn_keys = Counter(r["key"] for r in runs if r["phase"] == "synthetic")
    done = Counter(r["document"] for r in rows if r.get("phase") == "development-document-done")
    from ..dev.common import SPLITS, documents
    expected_docs = {d.key for s in SPLITS for d in documents(s)}
    fin = _finished_by_digest(_read(out / "guard.jsonl"))
    unguarded = sorted({r["obligation_sha256"] for r in runs} - set(fin))
    phases = {}
    for name, (_w, _l, targets, _p) in PHASES.items():
        pr = _read(out / name / "runs.jsonl")
        if not pr:
            continue
        want = set(targets(out))
        got = [r for r in pr if r.get("rebuilt")]
        phases[name] = {"targets": len(want), "run": len(got), "not_rebuilt": sum(1 for r in pr if not r.get("rebuilt")),
                        "every_target_run_once": sorted(r["target_obligation_sha256"] for r in got) == sorted(want),
                        "every_rebuild_is_the_same_obligation": all(r.get("same_obligation") for r in got),
                        "phase_records": len(_read(out / name / "phase.jsonl"))}
    checks = {"no_malformed_run_record": not malformed,
              "every_synthetic_case_once": len(syn_keys) == len(SIZES) * len(STATS) and set(syn_keys.values()) == {1},
              "every_development_document_done_once": set(done) == expected_docs and set(done.values()) == {1},
              "every_run_has_a_guard_record": not unguarded,
              "further_configurations_complete": all(v["every_target_run_once"] and v["every_rebuild_is_the_same_obligation"]
                                                     and v["not_rebuilt"] == 0 and v["phase_records"] >= 1 for v in phases.values())}
    return {**checks, "valid": all(checks.values()), "development_documents": len(done), "runs": len(runs),
            "malformed": malformed[:10], "runs_without_a_guard_record": unguarded[:10], "phases": phases}


def infrastructure(out: Path) -> dict:
    """Guard records that belong to no driver record: the development invocation the session's background
    limit stopped.  Its document was re-run from the start; the earlier records are kept and counted here."""
    guard = _read(out / "guard.jsonl")
    runs = [r for r in _read(out / "runs.jsonl") if r["phase"] in ("synthetic", "development")]
    per_run = Counter(r.get("obligation_sha256") for r in runs)
    finished = Counter(g["obligation_sha256"] for g in guard if g.get("event") == "finished" and g.get("obligation_sha256"))
    started = Counter(g["obligation_sha256"] for g in guard if g.get("event") == "started" and g.get("obligation_sha256"))
    return {"guard_finished_records_without_a_driver_record": sum(max(0, n - per_run.get(k, 0)) for k, n in finished.items()),
            "guard_runs_started_and_never_finished": sum(max(0, n - finished.get(k, 0)) for k, n in started.items()),
            "note": "not kernel results: the session's 2-hour background limit stopped the first development invocation"}


def _rows_by_document() -> dict[str, int]:
    from ..dev.common import SPLITS, documents
    rows = {}
    for split in SPLITS:
        for doc in documents(split):
            rows[doc.key.split(":")[0]] = max(0, len([x for x in doc.data.decode("utf-8", "replace").splitlines() if x.strip()]) - 1)
    return rows


def report(out: Path) -> str:
    """The consolidated report, generated from the logs alone (no number is typed by hand)."""
    s = summarise(out)
    runs = _documented(out)
    host = json.loads((out / "host.json").read_text(encoding="utf-8")) if (out / "host.json").exists() else {}
    try:
        doc_rows = _rows_by_document()
    except Exception:                       # the report must not depend on the development documents being readable
        doc_rows = {}
    L: list[str] = []
    w = L.append

    def outcome_cells(c) -> str:
        return " | ".join(str(c.get(k, 0)) for k in OUTCOMES)

    head = "| Accepted | Memory stop | System kill | Time limit | Rejected (depth) | Rejected (other) |"
    rule = "| ---: | ---: | ---: | ---: | ---: | ---: |"
    w("# Kernel resource feasibility study (feasibility study part C): consolidated report\n")
    w("Generated from the logs in this directory by `capacity_run.py --report`; every number below is computed from them, none typed. "
      "Development and synthetic data only: no prospective paper, no model call. A development-set finding: it enters no criterion, "
      "and protocol draft 3 stays unapproved.\n")
    w(f"Machine: {host.get('cpus')} CPUs, {round((host.get('mem_total_kb') or 0) / 1024 / 1024, 1)} GiB physical memory; {host.get('lean')}. "
      "Every process started from this session's shell shares one memory cgroup limit of 13.35 GiB (14,338,756,608 bytes); "
      "the machine has no swap in that domain.\n")
    w("Outcomes. Every run has exactly one label, taken from its own kernel record: *accepted*; *memory guard stop* (the guard stopped "
      "Lean at its limit); *system kill* (the operating system killed Lean: the memory domain was exhausted, a property of the "
      "configuration and machine, not of the claim); *time limit* (900 s); *rejected (depth)* (Lean stopped at its maximum recursion "
      "depth, a limit of the checker); *rejected (other)*. Only *accepted* establishes anything; every other label leaves the claim "
      "UNKNOWN. Memory stops, system kills and time limits are the resource-related UNKNOWNs.\n")
    v = s["record_validation"]
    w(f"Record validation: **{'valid' if v['valid'] else 'NOT VALID'}** ({v['runs']} documented runs; {v['development_documents']} development "
      f"documents, each completed once; every synthetic case once; every run has its guard record; every further configuration ran each of "
      f"its targets once, each rebuilt to the same obligation). Checks: " + ", ".join(f"{k} {val}" for k, val in v.items()
                                                                                    if isinstance(val, bool)) + ".\n")
    w("## A. Documented configuration (2 workers, 7 GiB per Lean process, 900 s, one claim per file)\n")
    for title, phase in (("Synthetic tables", "synthetic"), ("Development claims", "development")):
        rs = [r for r in runs if r["phase"] == phase]
        b = _block(rs)
        w(f"### {title}\n")
        w(f"{b['runs']} runs: " + "; ".join(f"{k} {v}" for k, v in b["outcomes"].items() if v) +
          f". Completed share {b['completed_share']}; resource-related UNKNOWN {b['resource_unknown']}.\n")
        w(f"Seconds per claim over all runs, failures included: median {b['median_seconds']}, 95th percentile {b['p95_seconds']}, "
          f"maximum {b['max_seconds']}; kernel time {b['kernel_hours']} h. Largest peak: {b['max_peak_gb']} GiB.\n")
        w("| Statistic | Runs " + head + " Median s | 95th pct s | Max s | Max peak GiB |")
        w("| --- | ---: " + rule + " ---: | ---: | ---: | ---: |")
        by: dict[str, list[dict]] = {}
        for r in rs:
            by.setdefault(r["statistic"], []).append(r)
        for stat in sorted(by):
            x = _block(by[stat])
            w(f"| {stat} | {x['runs']} | {outcome_cells(x['outcomes'])} | {x['median_seconds']} | {x['p95_seconds']} | {x['max_seconds']} | {x['max_peak_gb']} |")
        w("")
        bad = [r for r in rs if r["outcome"] != "accepted"]
        if bad:
            w(f"Every run that did not complete ({len(bad)}):\n")
            w("| Statistic | Table bytes | Rows / document | Outcome | Seconds | Peak GiB |")
            w("| --- | ---: | --- | --- | ---: | ---: |")
            for r in sorted(bad, key=lambda r: (r["statistic"], r["table_bytes"], r.get("document") or "")):
                w(f"| {r['statistic']} | {r['table_bytes']} | {r.get('rows') or r.get('document')} | {r['outcome']} | {r['seconds']} | {r['peak_gb']} |")
            w("")
    w("### Development claims by paper (original and planted copy together)\n")
    w("| Paper | Table rows | Runs " + head + " Median s | Max s | Max peak GiB |")
    w("| --- | ---: | ---: " + rule + " ---: | ---: | ---: |")
    for p, x in s["development"]["by_paper"].items():
        w(f"| {p} | {doc_rows.get(p, '')} | {x['runs']} | {outcome_cells(x['outcomes'])} | {x['median_seconds']} | {x['max_seconds']} | {x['max_peak_gb']} |")
    w("")
    inf = s["infrastructure"]
    w("### Interrupted by the infrastructure (not a kernel result)\n")
    w(f"The session's 2-hour background limit stopped the first development invocation. The document in progress was re-run from the "
      f"start; the driver records above are the complete re-run. The interrupted attempt's guard records are kept: "
      f"{inf['guard_finished_records_without_a_driver_record']} finished runs with no driver record and "
      f"{inf['guard_runs_started_and_never_finished']} run(s) started and never finished. They are excluded from the tables above "
      f"because the same claims were re-run to completion, and listed here so that nothing is dropped silently.\n")
    d = s["development"]
    w("### C7 on the development claims (documented configuration)\n")
    for key, label in (("within_candidate_supported_size", "Within the candidate supported size"), ("outside_candidate_supported_size", "Outside it"),
                       ("overall", "All development runs")):
        b = d[key]
        w(f"* {label}: {b['runs']} runs, completed share {b['completed_share']}, median {b['median_seconds']} s, 95th percentile "
          f"{b['p95_seconds']} s, largest peak {b['max_peak_gb']} GiB, memory stops {b['stopped_for_memory']}, system kills "
          f"{b['killed_by_system']}, depth rejections {b['outcomes']['kernel rejection: Lean recursion-depth limit']}; C7's limits hold: {b['c7_limits_hold']}.")
    w("")
    rr, rrec = phase_results(out, "rerun")
    w("## B. Isolated reruns (1 worker, 7 GiB): every obligation the operating system killed\n")
    if rrec:
        w("| Statistic | Table bytes | Documented runs (outcome) | Same obligation | Rerun outcome | Seconds | Peak GiB |")
        w("| --- | ---: | --- | --- | --- | ---: | ---: |")
        for r in rr:
            docs = "; ".join(f"{x.get('document') or 'synthetic'}: {x['outcome']}" for x in r["documented_runs"])
            w(f"| {r['statistic']} | {r['table_bytes']} | {docs} | {r['same_obligation']} | {r['outcome']} | {r['seconds']} | {r['peak_gb']} |")
        w("")
    else:
        w("Not run.\n")
    for name, title in (("safer_6gib", "C. Safer configuration (2 workers, 6 GiB per Lean process)"),
                        ("single_7gib", "D. Reduced concurrency (1 worker, 7 GiB per Lean process)")):
        prs, prec = phase_results(out, name)
        w(f"## {title}\n")
        if not prec:
            w("Not run.\n")
            continue
        w(f"{PHASES[name][3][0].upper() + PHASES[name][3][1:]}. Evaluated separately, with its own guard log; the documented results are unchanged.\n")
        b = _block(prs)
        w(f"{b['runs']} obligations: " + "; ".join(f"{k} {v}" for k, v in b["outcomes"].items() if v) +
          f". Median {b['median_seconds']} s, maximum {b['max_seconds']} s, largest peak {b['max_peak_gb']} GiB.\n")
        w("| Statistic | Table bytes | Rows / document | Documented outcome(s) | Documented s | Documented peak GiB | Outcome here | Seconds | Peak GiB |")
        w("| --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: |")
        for r in sorted(prs, key=lambda r: (r["documented_runs"][0]["phase"], r["statistic"], r["table_bytes"])):
            dr = r["documented_runs"]
            where = r.get("rows") or "; ".join(sorted({x.get("document") or "" for x in dr}))
            w(f"| {r['statistic']} | {r['table_bytes']} | {where} | {', '.join(sorted({x['outcome'] for x in dr}))} | "
              f"{max((x['seconds'] or 0) for x in dr)} | {max((x['peak_gb'] or 0) for x in dr)} | {r['outcome']} | {r['seconds']} | {r['peak_gb']} |")
        w("")
        sf = safety(out, name)
        w(f"Memory domain (rule fixed before these runs: analytic worst case and sampled working set both at least {RESERVE_GB} GiB below the "
          f"limit, and no system kill): worst case {sf['worst_case_gb']} GiB (workers x (limit + largest guard overshoot "
          f"{sf['largest_guard_overshoot_mb']} MB) + 128 MB for the driver and guards) against a limit of {sf['limit_gb']} GiB; sampled "
          f"working set at most {sf['sampled_max_working_set_gb']} GiB (usage including reclaimable cache {sf['sampled_max_usage_gb']} GiB); "
          f"system kills {sf['system_kills']}; OOM-kill counter change {sf['oom_kill_counter_change']}. "
          f"Safe on this machine: **{sf['safe_on_this_machine']}**.\n")
    w("## Candidate supported size by statistic\n")
    w("Largest synthetic table accepted with every smaller size accepted, within C7's per-run limits. Measured sizes only: no size "
      "beyond the largest table tested (2,800 rows) is claimed. Under C and D, the cases those phases re-ran take their result there; "
      "the others (documented peak at most 5 GiB) keep their documented result.\n")
    fc = s["further_configurations"]
    w("| Statistic | A: 2 x 7 GiB (bytes) | C: 2 x 6 GiB (bytes) | D: 1 x 7 GiB (bytes) | Provisional in draft 3 (bytes) |")
    w("| --- | ---: | ---: | ---: | ---: |")
    prov = {"count": 51209, "mean": 33760, "sd_sample": 33760, "pearson": 33760, "min": 8219, "median": 8219}
    for stat, v in s["synthetic"]["candidate_supported_size_bytes"].items():
        cs = (fc.get("safer_6gib") or {}).get("candidate_supported_size_bytes") or {}
        ds = (fc.get("single_7gib") or {}).get("candidate_supported_size_bytes") or {}
        w(f"| {stat} | {v} | {cs.get(stat, '')} | {ds.get(stat, '')} | {prov.get(stat)} |")
    w("")
    rv = s["repeat_variation"]
    w("## Repeatability\n")
    for key, label in (("documented_twice", "Same obligation run twice in A (an original and its planted copy)"),
                       ("documented_vs_single_worker", "Same obligation in A and in D")):
        v = rv.get(key)
        if v:
            w(f"* {label}, both completed: {v['pairs']} pairs; peak memory differs by median {v['peak_difference_mb_median']} MB, at most "
              f"{v['peak_difference_mb_max']} MB; time differs by median {v['time_difference_relative_median']:.1%}, at most {v['time_difference_relative_max']:.1%}.")
    w("")
    pj = s["projection"]
    o = pj["observed"]
    if not o:
        return "\n".join(L) + "\n"
    w("## Kernel time for 60 and 120 papers\n")
    w(f"Observed on {o['papers']} development papers (original and planted copy, every distinct claim of the four v1 arms, one claim per "
      f"file, documented configuration): kernel time per paper mean {o['kernel_hours_per_paper_mean']} h, median "
      f"{o['kernel_hours_per_paper_median']} h, maximum {o['kernel_hours_per_paper_max']} h; kernel runs per paper mean "
      f"{o['kernel_runs_per_paper_mean']}, maximum {o['kernel_runs_per_paper_max']}.\n")
    w("Projected wall time (a projection, not a measurement: perfect packing, papers like the development papers):\n")
    w("| Design | Workers | At the observed mean (h) | If every paper were the slowest observed (h) |")
    w("| --- | ---: | ---: | ---: |")
    for k, v in pj["projected_wall_hours"].items():
        n, _, wk, _ = k.split("_")
        w(f"| {n} papers | {wk} | {v['at_mean']} | {v['if_every_paper_were_the_slowest']} |")
    w("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--phase", choices=("synthetic", "development", "both", *PHASES), default="both",
                    help="the documented configuration (synthetic, development, both), or one further configuration: "
                         + "; ".join(f"{k}: {v[3]}" for k, v in PHASES.items()))
    ap.add_argument("--lean", default=None, help="the real Lean 4.28.0 executable (default: lean on PATH)")
    ap.add_argument("--summarise", action="store_true", help="write summary.json from the logs")
    ap.add_argument("--report", action="store_true", help="write REPORT.md and summary.json from the logs")
    ap.add_argument("--max-documents", type=int, default=None, help="development phase: at most this many documents in this invocation (resumable)")
    args = ap.parse_args(argv)
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.report or args.summarise:
        s = summarise(args.out)
        (args.out / "summary.json").write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
        if args.report:
            (args.out / "REPORT.md").write_text(report(args.out), encoding="utf-8")
        print(json.dumps({k: s[k]["overall"] for k in ("synthetic", "development")}, indent=1))
        return 0
    import shutil
    real = args.lean or shutil.which("lean")
    if not real:
        raise SystemExit("Lean 4.28.0 not found")
    if args.phase in PHASES:
        workers, limit, targets, purpose = PHASES[args.phase]
        print(json.dumps(run_phase(args.out, args.phase, targets(args.out), real, workers, limit, purpose), indent=1))
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
        development(args.out, args.max_documents)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
