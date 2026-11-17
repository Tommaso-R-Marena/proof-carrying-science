"""Expensive local-check benchmarks: isolate validation / recheck / recompute costs.

Synthetic Int ops are too cheap to show incremental benefit. This suite wraps the
registry with a configurable per-check delay representing expensive proof checking.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from model.graph import Graph, Node
from model.ops import DEFAULT_POLICY, OP_INT_ADD, OP_INT_CONST, OpRegistry, default_registry
from reference.fresh import fresh_verify
from verifier.incremental import IncrementalVerifier


@dataclass
class CostRow:
    name: str
    nodes: int
    changes: int
    delay_ms: float
    fresh_ms: float
    incr_trusted_ms: float  # recheck_on_reuse=False (ValidState trust)
    incr_defend_ms: float  # recheck_on_reuse=True
    reused: int
    rechecked: int
    agree: bool

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "nodes": self.nodes,
            "changes": self.changes,
            "delay_ms_per_check": self.delay_ms,
            "fresh_full_recompute_ms": self.fresh_ms,
            "incremental_trusted_reuse_ms": self.incr_trusted_ms,
            "incremental_defense_recheck_ms": self.incr_defend_ms,
            "reused": self.reused,
            "rechecked": self.rechecked,
            "agree": self.agree,
            "speedup_trusted_vs_fresh": (
                self.fresh_ms / self.incr_trusted_ms if self.incr_trusted_ms else None
            ),
            "speedup_defend_vs_fresh": (
                self.fresh_ms / self.incr_defend_ms if self.incr_defend_ms else None
            ),
        }


class DelayedRegistry(OpRegistry):
    """Wraps an OpRegistry, sleeping `delay_ms` on every local_check_node."""

    def __init__(self, inner: OpRegistry, delay_ms: float):
        super().__init__(
            versions=dict(inner.versions),
            allowed_policies=set(inner.allowed_policies),
            rat_table=dict(inner.rat_table),
        )
        self._inner = inner
        self.delay_ms = delay_ms
        self.check_calls = 0

    def local_check_node(self, *args, **kwargs) -> bool:  # type: ignore[override]
        self.check_calls += 1
        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000.0)
        return self._inner.local_check_node(*args, **kwargs)

    def make_cert(self, op, deps, evidence):  # type: ignore[override]
        return self._inner.make_cert(op, deps, evidence)

    def compute(self, op, deps, evidence):  # type: ignore[override]
        return self._inner.compute(op, deps, evidence)


def chain_graph(n: int) -> Graph:
    nodes = [Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 1)]
    for i in range(1, n):
        nodes.append(Node(i, OP_INT_ADD, (i - 1, 0), DEFAULT_POLICY, 1, 0))
    return Graph(nodes=nodes)


def _run(name: str, g: Graph, change_ids: List[int], delay_ms: float) -> CostRow:
    base = default_registry()
    # Initial verify without delay (setup).
    v = IncrementalVerifier(base)
    assert v.initial_verify(g).accepted
    new_g = g.replace_nodes(
        [
            Node(cid, g.by_id()[cid].op, g.by_id()[cid].deps, DEFAULT_POLICY, 1, g.by_id()[cid].evidence + 1)
            if g.by_id()[cid].op == OP_INT_CONST
            else Node(
                cid,
                g.by_id()[cid].op,
                g.by_id()[cid].deps,
                DEFAULT_POLICY,
                1,
                g.by_id()[cid].evidence + 1,
            )
            for cid in change_ids
        ]
    )

    # Fresh with delay
    delayed_fresh = DelayedRegistry(base, delay_ms)
    t0 = time.perf_counter()
    fresh = fresh_verify(new_g, delayed_fresh)
    t1 = time.perf_counter()

    # Incremental trusted reuse
    delayed_inc = DelayedRegistry(base, delay_ms)
    v_trust = IncrementalVerifier(delayed_inc)
    assert v_trust.initial_verify(g).accepted
    # Re-bind registry for revalidate checks
    v_trust.registry = delayed_inc
    delayed_inc.check_calls = 0
    t2 = time.perf_counter()
    incr_t = v_trust.revalidate(
        new_g,
        change_ids,
        compare_fresh=False,
        recheck_on_reuse=False,
        record_trace=False,
    )
    t3 = time.perf_counter()

    # Incremental defense-in-depth
    delayed_def = DelayedRegistry(base, delay_ms)
    v_def = IncrementalVerifier(delayed_def)
    assert v_def.initial_verify(g).accepted
    v_def.registry = delayed_def
    delayed_def.check_calls = 0
    t4 = time.perf_counter()
    incr_d = v_def.revalidate(
        new_g,
        change_ids,
        compare_fresh=False,
        recheck_on_reuse=True,
        record_trace=False,
    )
    t5 = time.perf_counter()

    agree = (
        incr_t.accepted == fresh.accepted
        and (not incr_t.accepted or incr_t.outputs == fresh.outputs)
        and incr_d.accepted == fresh.accepted
        and (not incr_d.accepted or incr_d.outputs == fresh.outputs)
    )
    return CostRow(
        name=name,
        nodes=len(g.nodes),
        changes=len(change_ids),
        delay_ms=delay_ms,
        fresh_ms=(t1 - t0) * 1000,
        incr_trusted_ms=(t3 - t2) * 1000,
        incr_defend_ms=(t5 - t4) * 1000,
        reused=len(incr_t.reused),
        rechecked=len(incr_t.rechecked),
        agree=agree,
    )


def run_expensive_benchmarks(delay_ms: float = 2.0) -> List[CostRow]:
    rows = [
        _run("chain_80_leaf", chain_graph(80), [79], delay_ms),
        _run("chain_80_root", chain_graph(80), [0], delay_ms),
        _run("chain_200_leaf", chain_graph(200), [199], delay_ms),
        _run("chain_200_mid", chain_graph(200), [100], delay_ms),
    ]
    return rows


def main() -> int:
    rows = run_expensive_benchmarks(delay_ms=2.0)
    payload = {
        "assumption": (
            "Each local_check_node sleeps delay_ms to model expensive proof checking. "
            "Trusted reuse skips local_check on reuse; defense mode rechecks every reuse."
        ),
        "not_a_refinement_claim": True,
        "rows": [r.to_json() for r in rows],
        "all_agree": all(r.agree for r in rows),
        "any_trusted_speedup": any(
            r.incr_trusted_ms < r.fresh_ms for r in rows if r.reused > 0
        ),
    }
    out = Path(__file__).resolve().parents[1] / "results" / "expensive_benchmark_report.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for r in rows:
        st = r.fresh_ms / r.incr_trusted_ms if r.incr_trusted_ms else None
        sd = r.fresh_ms / r.incr_defend_ms if r.incr_defend_ms else None
        print(
            f"{r.name}: fresh={r.fresh_ms:.1f}ms trusted={r.incr_trusted_ms:.1f}ms "
            f"defend={r.incr_defend_ms:.1f}ms reused={r.reused} rechecked={r.rechecked} "
            f"speedup_trusted={st:.2f}x speedup_defend={sd:.2f}x agree={r.agree}"
        )
    print("wrote", out)
    return 0 if payload["all_agree"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
