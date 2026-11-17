#!/usr/bin/env python3
"""End-to-end demo: initial check, change, reuse, recheck, agree with fresh, reject forgery."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cache.store import CacheEntry
from model.graph import Certificate, Graph, Node
from model.ops import DEFAULT_POLICY, OP_INT_ADD, OP_INT_CONST, OP_INT_MUL, default_registry
from reference.fresh import fresh_verify
from verifier.incremental import IncrementalVerifier


def tiny() -> Graph:
    return Graph(
        nodes=[
            Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 2),
            Node(1, OP_INT_CONST, (), DEFAULT_POLICY, 1, 3),
            Node(2, OP_INT_ADD, (0, 1), DEFAULT_POLICY, 1, 0),
            Node(3, OP_INT_MUL, (2, 1), DEFAULT_POLICY, 1, 0),
        ]
    )


def main() -> int:
    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    g = tiny()
    v = IncrementalVerifier(default_registry())

    print("== initial verify ==")
    init = v.initial_verify(g)
    print(f"accepted={init.accepted} outputs={init.outputs}")
    assert init.accepted and init.outputs[3] == 15

    print("== change node 0 evidence 2→5; reuse unaffected node 1 ==")
    incr = v.apply_node_changes([Node(0, OP_INT_CONST, (), DEFAULT_POLICY, 1, 5)])
    print(
        f"accepted={incr.accepted} outputs={incr.outputs} "
        f"reused={incr.reused} rechecked={incr.rechecked} agree={incr.agrees_with_fresh}"
    )
    assert incr.accepted and incr.outputs[3] == 24 and 1 in incr.reused
    assert incr.agrees_with_fresh
    fresh = fresh_verify(v.graph, v.registry)
    assert fresh.accepted and fresh.outputs == incr.outputs

    print("== forgery A: prior_accepted=False (no authority) ==")
    v_a = IncrementalVerifier(default_registry())
    v_a.initial_verify(g)
    key = [e for e in v_a.cache.entries if e.key.id == 3][0].key
    v_a.cache.put(
        CacheEntry(
            key=key,
            cert=Certificate(payload=("ok", OP_INT_MUL, ("int", 0)), output=0),
            prior_accepted=False,
        )
    )
    r_a = v_a.revalidate(g.copy(), changes=[], compare_fresh=True)
    print(
        f"accepted={r_a.accepted} out3={r_a.outputs.get(3)} "
        f"reused={r_a.reused} rechecked={r_a.rechecked}"
    )
    # Must not reuse forged entry; recheck yields correct 15
    assert r_a.accepted and r_a.outputs[3] == 15 and 3 in r_a.rechecked

    print("== forgery B: forged prior_accepted=True + wrong cert (defense-in-depth) ==")
    v_b = IncrementalVerifier(default_registry())
    v_b.initial_verify(g)
    key = [e for e in v_b.cache.entries if e.key.id == 3][0].key
    v_b.cache.put(
        CacheEntry(
            key=key,
            cert=Certificate(payload=("ok", OP_INT_MUL, ("int", 0)), output=0),
            prior_accepted=True,
        )
    )
    r_b = v_b.revalidate(g.copy(), changes=[], compare_fresh=True)
    print(f"accepted={r_b.accepted} out3={r_b.outputs.get(3)} err={r_b.error}")
    # Fail-closed: inconsistent "authoritative" entry fails local check on reuse
    forgery_b_rejected = not (r_b.accepted and r_b.outputs.get(3) == 0)
    assert forgery_b_rejected

    report = {
        "initial_outputs": {str(k): v for k, v in init.outputs.items()},
        "after_change": incr.to_json(),
        "agree_with_fresh": bool(incr.agrees_with_fresh),
        "forgery_no_authority": r_a.to_json(),
        "forgery_forged_authority": r_b.to_json(),
        "summary": {
            "initial_accepted": init.accepted,
            "reuse_observed": 1 in incr.reused,
            "recheck_observed": 0 in incr.rechecked,
            "agrees_with_fresh": bool(incr.agrees_with_fresh),
            "forgery_no_authority_rechecked": 3 in r_a.rechecked and r_a.outputs.get(3) == 15,
            "forgery_forged_authority_rejected": forgery_b_rejected,
        },
    }
    out = results_dir / "demo_report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
