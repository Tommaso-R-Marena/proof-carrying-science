"""Scientific-intelligence CLI: bounded experiments, independent acceptance."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import subprocess

from pcs.jsonio import strict_json_loads
from .corpus import generate
from .experiments import evaluate, reproduce, verify_lean
from .learning import train
from .logic import check, lean_source
from .project import compile_project, invalidate
from .search import ReasoningEnv, memory, search, train_bandit, verify_episode


def read(path, limit=65536):
    with Path(path).open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Input exceeds the byte budget")
    return strict_json_loads(raw.decode("utf-8"))


def emit(value, output=None):
    raw = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if output:
        with Path(output).open("x", encoding="utf-8") as handle:
            handle.write(raw)
    else:
        print(raw, end="")


def command(args):
    try:
        op = args.omega_command
        if op == "intake":
            result = compile_project(read(args.input))
        elif op == "impact":
            result = invalidate(read(args.input), args.changed)
        elif op == "check":
            value = read(args.input)
            result = check(value)
            if args.lean_output:
                with Path(args.lean_output).open("x", encoding="utf-8") as handle:
                    handle.write(lean_source(value))
        elif op == "search":
            result = search(read(args.input), strategy=args.strategy, model=read(args.model, 131072) if args.model else None,
                            checks=args.checks, depth=args.depth, seed=args.seed)
        elif op == "replay":
            episode = read(args.input, 4 * 1024 * 1024)
            verify_episode(episode)
            result = {"verified": True, "episode_sha256": episode["episode_sha256"], "pcs_authority": False}
        elif op == "generate":
            result = generate(seed=args.seed, per_family=args.per_family)
        elif op == "train":
            result = train(read(args.input, 4 * 1024 * 1024), mode=args.mode, seed=args.seed, epochs=args.epochs)
        elif op == "bandit":
            result = train_bandit(read(args.input, 4 * 1024 * 1024), seed=args.seed, episodes=args.episodes)
        elif op == "evaluate":
            models = {Path(p).stem: read(p, 131072) for p in args.models}
            result, _ = evaluate(read(args.input, 4 * 1024 * 1024), models, budgets=args.budgets, seed=args.seed)
        elif op == "reproduce":
            result = reproduce(args.output, seed=args.seed, per_family=args.per_family, epochs=args.epochs,
                               bandit_episodes=args.bandit_episodes, budgets=args.budgets)
            emit(result)
            return 0
        elif op == "verify-lean":
            result = verify_lean(args.input)
        elif op == "memory":
            result = memory(read(args.input, 4 * 1024 * 1024))
        elif op == "env":
            env = ReasoningEnv(read(args.input), budget=args.budget)
            actions = read(args.actions)
            if type(actions) is not list or len(actions) > args.budget:
                raise ValueError("Actions must be a bounded list")
            transitions = [env.step(a) for a in actions]
            result = {"initial_goal": env._goal_sha, "transitions": transitions, "history": env.history, "pcs_authority": False}
        elif op == "optimize-check":
            from pcs.certiforge_adapter_v1 import evaluate as cf_check, research_claim_graph
            proposal = read(args.proposal)
            receipt = cf_check(proposal, Path(args.input), checker=Path(args.checker),
                               checker_sha256=args.checker_sha256, checker_source_commit=args.checker_source_commit)
            result = {"format": "pcs-omega-optimization-bridge-v1", "receipt": receipt, "pcs_authority": False}
            if receipt["state"] == "CHECKED_EXHAUSTIVE":
                result["research_graph"] = research_claim_graph(proposal, receipt, Path(args.input))
        else:
            raise ValueError("Unknown Omega operation")
        emit(result, getattr(args, "output", None))
        if op == "check" and not result["equivalent"] or op == "search" and result["solution"] is None:
            return 1
        if op == "optimize-check" and result["receipt"]["state"] != "CHECKED_EXHAUSTIVE":
            return 1
        return 0
    except (ValueError, OSError, TypeError, KeyError, RecursionError, subprocess.SubprocessError) as exc:
        print(json.dumps({"format": "pcs-omega-error-v1", "error": str(exc), "pcs_authority": False}), file=sys.stderr)
        return 2


def register(sub):
    parser = sub.add_parser("omega", help="Experimental scientific reasoning: explicit intake, CPU learning, independent checking")
    ops = parser.add_subparsers(dest="omega_command", required=True)
    for name in ("intake", "impact", "check", "search", "replay", "generate", "train", "bandit", "evaluate", "reproduce", "verify-lean", "memory", "env", "optimize-check"):
        p = ops.add_parser(name)
        p.set_defaults(func=command)
        if name not in {"generate", "reproduce"}:
            p.add_argument("input")
        if name not in {"reproduce", "verify-lean"}:
            p.add_argument("-o", "--output")
        if name in {"generate", "train", "bandit", "evaluate", "reproduce", "search"}:
            p.add_argument("--seed", type=int, default=20261009)
        if name in {"generate", "reproduce"}:
            p.add_argument("--per-family", type=int, default=24)
        if name in {"train", "reproduce"}:
            p.add_argument("--epochs", type=int, default=24)
        if name in {"evaluate", "reproduce"}:
            p.add_argument("--budgets", type=int, nargs="+", default=[4, 8])
        if name == "reproduce":
            p.add_argument("--output", required=True)
            p.add_argument("--bandit-episodes", type=int, default=1600)
        elif name == "impact":
            p.add_argument("--changed", nargs="+", required=True)
        elif name == "check":
            p.add_argument("--lean-output")
        elif name == "search":
            p.add_argument("--strategy", choices=("bfs", "random", "structural", "learned"), default="structural")
            p.add_argument("--model")
            p.add_argument("--checks", type=int, default=8)
            p.add_argument("--depth", type=int, default=3)
        elif name == "train":
            p.add_argument("--mode", choices=("bag", "graph"), default="graph")
        elif name == "bandit":
            p.add_argument("--episodes", type=int, default=1600)
        elif name == "evaluate":
            p.add_argument("--models", nargs="+", required=True)
        elif name == "env":
            p.add_argument("--actions", required=True)
            p.add_argument("--budget", type=int, default=8)
        elif name == "optimize-check":
            p.add_argument("--proposal", required=True)
            p.add_argument("--checker", required=True)
            p.add_argument("--checker-sha256", required=True)
            p.add_argument("--checker-source-commit", required=True)
