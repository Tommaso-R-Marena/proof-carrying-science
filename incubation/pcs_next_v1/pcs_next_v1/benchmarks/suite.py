"""Independent evaluation benchmark suite."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..adapters.pkpd import predict_concentration, verify_predictions
from ..core.canonical import canonicalize
from ..falsification.challenges import challenge_data_leakage, challenge_unit_error
from ..translation.formalize import formalize_text


def run_benchmarks() -> dict[str, Any]:
    t0 = time.perf_counter()
    results = []

    # Honest PK
    model = {"dose": 100.0, "volume": 10.0, "clearance": 1.0, "clearance_unit": "L/h", "evidence_kind": "simulation"}
    rows = [(t, predict_concentration(100.0, 10.0, 1.0, t)) for t in [0.0, 1.0, 2.0, 5.0]]
    r = verify_predictions(model, rows)
    results.append({"case": "pk_honest", "result": r, "expect_status": "COMPUTATIONALLY_TESTED"})

    # Wrong predictions
    bad_rows = [(t, c * 1.5) for t, c in rows]
    r2 = verify_predictions(model, bad_rows)
    results.append({"case": "pk_wrong", "result": r2, "expect_status": "REFUTED"})

    # Unit error
    bad_model = {**model, "clearance_unit": "furlongs/fortnight"}
    results.append({"case": "unit_error", "result": challenge_unit_error(bad_model).to_status(), "expect_status": "REFUTED"})

    # Leakage
    results.append(
        {
            "case": "leakage",
            "result": challenge_data_leakage(["a", "b"], ["b", "c"]).to_status(),
            "expect_status": "REFUTED",
        }
    )

    # Claim translation: existential must not become forall
    ex = formalize_text("e1", "there exists x such that x > 0")
    results.append(
        {
            "case": "exists_not_forall",
            "result": ex,
            "expect_kind": "exists",
        }
    )

    # Baseline: conventional unit test equivalent — recompute one point
    baseline = abs(predict_concentration(100, 10, 1, 1.0) - 10.0 * __import__("math").exp(-0.1)) < 1e-9
    results.append({"case": "baseline_numeric_recompute", "pass": baseline, "baseline": "independent_numeric_recompute"})

    scored = []
    for item in results:
        if "expect_status" in item:
            ok = item["result"].get("status") == item["expect_status"]
        elif "expect_kind" in item:
            ok = item["result"].get("expr", {}).get("kind") == item["expect_kind"]
        else:
            ok = bool(item.get("pass"))
        scored.append({**item, "correct": ok})

    false_accept = sum(1 for s in scored if s.get("expect_status") == "REFUTED" and s["result"].get("status") != "REFUTED")
    false_reject = sum(
        1 for s in scored if s.get("expect_status") == "COMPUTATIONALLY_TESTED" and s["result"].get("status") == "REFUTED"
    )
    elapsed = time.perf_counter() - t0
    return {
        "format": "pcs-next-benchmark-report-v1",
        "cases": scored,
        "metrics": {
            "n": len(scored),
            "correct": sum(1 for s in scored if s["correct"]),
            "false_acceptances": false_accept,
            "false_rejections": false_reject,
            "latency_s": elapsed,
        },
        "baselines_executed": ["independent_numeric_recompute", "unit_challenge", "pk_model_check"],
        "unfavorable_findings_policy": "preserved",
    }


def write_report(path: str | Path) -> dict[str, Any]:
    report = run_benchmarks()
    Path(path).write_bytes(canonicalize(report) + b"\n")
    return report
