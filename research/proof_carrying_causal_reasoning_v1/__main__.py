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
    cl = sub.add_parser(
        "cladder",
        help="External CLadder (NeurIPS 2023) oracle match for ATE/ETT/etc.",
    )
    cl.add_argument("--zip", type=Path, default=None)
    cl.add_argument("--data-dir", type=Path, default=None)
    cl.add_argument("--out", type=Path, required=True)
    cl.add_argument("--atol-models", type=float, default=1e-6)
    cl.add_argument("--atol-questions", type=float, default=1e-4)
    cl.add_argument("--limit-models", type=int, default=None)
    cl.add_argument("--limit-questions", type=int, default=None)
    cll = sub.add_parser(
        "cladder-llm",
        help="CLadder NL yes/no LLM accuracy sample (compare to published SOTA)",
    )
    cll.add_argument("--data-dir", type=Path, required=True)
    cll.add_argument("--out", type=Path, required=True)
    cll.add_argument("--model", default="gemini-3.5-flash-lite")
    cll.add_argument("--per-rung", type=int, default=12)
    cll.add_argument("--seed", type=int, default=20251118)
    cll.add_argument("--min-interval", type=float, default=12.0)
    clc = sub.add_parser(
        "cladder-certified",
        help="PCCR-certified CLadder yes/no solver (full-set SOTA challenge)",
    )
    clc.add_argument("--data-dir", type=Path, required=True)
    clc.add_argument("--out", type=Path, required=True)
    clc.add_argument("--limit", type=int, default=None)
    clcot = sub.add_parser(
        "cladder-causalcot",
        help="CausalCoT (+ optional critic) CLadder NL sample via Gemini",
    )
    clcot.add_argument("--data-dir", type=Path, required=True)
    clcot.add_argument("--out", type=Path, required=True)
    clcot.add_argument("--model", default="gemini-3.5-flash-lite")
    clcot.add_argument("--critic-model", default="gemini-3.5-flash-lite")
    clcot.add_argument("--no-critic", action="store_true")
    clcot.add_argument("--per-rung", type=int, default=12)
    clcot.add_argument("--seed", type=int, default=20251118)
    clcot.add_argument("--min-interval", type=float, default=8.0)

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

    if args.cmd == "cladder":
        from research.proof_carrying_causal_reasoning_v1.external.run_cladder_eval import (
            main as cladder_main,
        )

        argv = ["--out", str(args.out)]
        if args.zip:
            argv.extend(["--zip", str(args.zip)])
        if args.data_dir:
            argv.extend(["--data-dir", str(args.data_dir)])
        argv.extend(["--atol-models", str(args.atol_models)])
        argv.extend(["--atol-questions", str(args.atol_questions)])
        if args.limit_models is not None:
            argv.extend(["--limit-models", str(args.limit_models)])
        if args.limit_questions is not None:
            argv.extend(["--limit-questions", str(args.limit_questions)])
        return cladder_main(argv)

    if args.cmd == "cladder-llm":
        from research.proof_carrying_causal_reasoning_v1.external.cladder_llm_eval import (
            main as cladder_llm_main,
        )

        return cladder_llm_main(
            [
                "--data-dir",
                str(args.data_dir),
                "--out",
                str(args.out),
                "--model",
                args.model,
                "--per-rung",
                str(args.per_rung),
                "--seed",
                str(args.seed),
                "--min-interval",
                str(args.min_interval),
            ]
        )

    if args.cmd == "cladder-certified":
        from research.proof_carrying_causal_reasoning_v1.external.cladder_certified_solver import (
            main as certified_main,
        )

        argv = ["--data-dir", str(args.data_dir), "--out", str(args.out)]
        if args.limit is not None:
            argv.extend(["--limit", str(args.limit)])
        return certified_main(argv)

    if args.cmd == "cladder-causalcot":
        from research.proof_carrying_causal_reasoning_v1.external.cladder_causalcot import (
            main as causalcot_main,
        )

        argv = [
            "--data-dir",
            str(args.data_dir),
            "--out",
            str(args.out),
            "--model",
            args.model,
            "--critic-model",
            args.critic_model,
            "--per-rung",
            str(args.per_rung),
            "--seed",
            str(args.seed),
            "--min-interval",
            str(args.min_interval),
        ]
        if args.no_critic:
            argv.append("--no-critic")
        return causalcot_main(argv)

    return 2


if __name__ == "__main__":
    sys.exit(main())
