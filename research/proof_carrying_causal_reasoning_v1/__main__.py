"""CLI: python -m research.proof_carrying_causal_reasoning_v1 <command>"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pccr")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-tasks", help="List research tasks")
    c = sub.add_parser("controls", help="Run authored control suite")
    c.add_argument("--out", type=Path, default=None)
    o = sub.add_parser("oracle", help="Backdoor↔intervention oracle sanity")
    o.add_argument("--out", type=Path, default=None)
    a = sub.add_parser("all", help="Run controls + oracle and write results")
    a.add_argument(
        "--out",
        type=Path,
        default=Path("research/proof_carrying_causal_reasoning_v1/results/local-run"),
    )
    m = sub.add_parser("model", help="Live local model evaluation")
    m.add_argument("--weights", type=Path, required=True)
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("--model", default="Qwen/Qwen3-0.6B-GGUF")
    m.add_argument("--tasks", nargs="*", default=None)
    d = sub.add_parser("download-weights", help="Download pinned GGUF + llama.cpp")
    d.add_argument("--weights", type=Path, required=True)
    g = sub.add_parser(
        "gemini",
        help="Rate-limited Gemini API evaluation (requires GEMINI_API_KEY env)",
    )
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--model", default="gemini-3.5-flash-lite")
    g.add_argument("--tasks", nargs="*", default=None)
    g.add_argument("--min-interval", type=float, default=8.0)
    g.add_argument("--max-requests", type=int, default=12)

    args = p.parse_args(argv)

    from research.proof_carrying_causal_reasoning_v1.experiment import (
        all_research_tasks,
        run_controls,
        run_oracle_sanity,
        write_results,
    )

    if args.cmd == "list-tasks":
        for t in all_research_tasks():
            print(f"{t.task_id}\t{t.domain}\t{t.title}")
        return 0

    if args.cmd == "controls":
        payload = run_controls()
        print(json.dumps({"ok": payload["ok"], "n_controls": payload["n_controls"],
                          "n_mismatches": payload["n_mismatches"]}, indent=2))
        if args.out:
            write_results(args.out, payload)
        return 0 if payload["ok"] else 1

    if args.cmd == "oracle":
        payload = run_oracle_sanity()
        print(json.dumps({"ok": payload["ok"], "n": len(payload["rows"])}, indent=2))
        if args.out:
            write_results(args.out, payload)
        return 0 if payload["ok"] else 1

    if args.cmd == "all":
        controls = run_controls()
        oracle = run_oracle_sanity()
        tasks = [t.to_dict() for t in all_research_tasks()]
        payload = {
            "package": "proof_carrying_causal_reasoning_v1",
            "controls": controls,
            "oracle": oracle,
            "tasks": tasks,
            "ok": controls["ok"] and oracle["ok"],
            "claims": {
                "production_authority": False,
                "empirical_causation_established": False,
                "general_backdoor_soundness_proved_in_lean": False,
                "local_exact_finite_evidence": True,
            },
        }
        path = write_results(args.out, payload)
        print(json.dumps({"ok": payload["ok"], "wrote": str(path)}, indent=2))
        return 0 if payload["ok"] else 1

    if args.cmd == "download-weights":
        from research.proof_carrying_causal_reasoning_v1.model_eval import download_weights

        info = download_weights(args.weights)
        print(json.dumps(info, indent=2))
        return 0

    if args.cmd == "model":
        from research.proof_carrying_causal_reasoning_v1.model_eval import run_live

        payload = run_live(args.weights, args.out, model=args.model, task_ids=args.tasks)
        print(
            json.dumps(
                {
                    "accuracy": payload["evaluation"]["accuracy"],
                    "n_accepted": payload["evaluation"]["n_accepted"],
                    "n_tasks": payload["evaluation"]["n_tasks"],
                    "out": str(args.out),
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "gemini":
        from research.proof_carrying_causal_reasoning_v1.gemini_eval import run_gemini

        payload = run_gemini(
            args.out,
            model=args.model,
            task_ids=args.tasks,
            min_interval_sec=args.min_interval,
            max_requests=args.max_requests,
        )
        print(
            json.dumps(
                {
                    "model": payload["model"],
                    "accuracy": payload["evaluation"]["accuracy"],
                    "n_accepted": payload["evaluation"]["n_accepted"],
                    "n_tasks": payload["evaluation"]["n_tasks"],
                    "n_calls": payload["n_calls"],
                    "out": str(args.out),
                },
                indent=2,
            )
        )
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
