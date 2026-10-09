"""Versioned CPU experiments with actual solve-rate and negative-result reports."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from pcs.jsonio import strict_json_loads

from .corpus import generate, validate_corpus
from .learning import source_digest, train, validate_model
from .logic import digest, integer, lean_source
from .search import memory, search, train_bandit, verify_episode


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_artifact(path):
    with Path(path).open("rb") as handle:
        raw = handle.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Experiment artifact exceeds byte bound")
    return strict_json_loads(raw.decode("utf-8"))


def wilson(solved, total):
    if total == 0:
        return None
    z, p = 1.96, solved / total
    divisor = 1 + z * z / total
    center = (p + z * z / (2 * total)) / divisor
    half = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / divisor
    return [max(0, center - half), min(1, center + half)]


def evaluate(corpus, models, *, budgets=(4, 8), seed=20261009):
    validate_corpus(corpus)
    integer(seed, 0, 2**32 - 1, "evaluation seed")
    if type(budgets) not in (tuple, list) or not 1 <= len(budgets) <= 4 or len(set(budgets)) != len(budgets):
        raise ValueError("Use 1–4 distinct checker budgets")
    for budget in budgets:
        integer(budget, 1, 128, "evaluation budget")
    train_digests = {r["task_sha256"] for r in corpus["records"] if r["partition"] == "train"}
    for model in models.values():
        validate_model(model)
        if set(model["training"]["task_digests"]) != train_digests:
            raise ValueError("Checkpoint trained on a different or contaminated corpus")
    rows, trajectories = [], []
    for partition in ("validation", "test"):
        records = [r for r in corpus["records"] if r["partition"] == partition]
        for budget in budgets:
            for name in ["bfs", "random", "structural"] + sorted(models):
                outputs, elapsed, family_counts = [], 0.0, {}
                for record in records:
                    started = time.perf_counter()
                    episode = search(record["task"], strategy=name if name in {"bfs", "random", "structural"} else "learned",
                                     model=models.get(name), checks=budget, depth=3, seed=seed + len(outputs))
                    elapsed += time.perf_counter() - started
                    verify_episode(episode)
                    solved = episode["solution"] is not None
                    outputs.append({"task_id": record["id"], "family": record["family"],
                                    "solved": solved, "checks": episode["checks_used"], "episode_sha256": episode["episode_sha256"]})
                    counts = family_counts.setdefault(record["family"], {"tasks": 0, "solved": 0})
                    counts["tasks"] += 1
                    counts["solved"] += int(solved)
                    if partition == "test" and name == "graph" and budget == max(budgets):
                        trajectories.append(episode)
                total, solved_count = len(outputs), sum(r["solved"] for r in outputs)
                rows.append({"partition": partition, "strategy": name, "checker_budget": budget,
                             "tasks": total, "solved": solved_count, "solve_rate": solved_count / total if total else None,
                             "descriptive_wilson_95": wilson(solved_count, total),
                             "mean_checker_calls": sum(r["checks"] for r in outputs) / total if total else None,
                             "search_wall_seconds": elapsed, "families": family_counts, "results": outputs})
    comparison = []
    for budget in budgets:
        test_rows = [r for r in rows if r["partition"] == "test" and r["checker_budget"] == budget]
        baseline = max((r for r in test_rows if r["strategy"] in {"bfs", "random", "structural"}), key=lambda r: r["solved"])
        for r in test_rows:
            if r["strategy"] not in models:
                continue
            comparison.append({"checker_budget": budget, "strategy": r["strategy"], "best_baseline": baseline["strategy"],
                               "solve_count_delta": r["solved"] - baseline["solved"],
                               "outperformed_baseline_on_this_sample": r["solved"] > baseline["solved"]})
    return {"format": "pcs-omega-evaluation-v1", "seed": seed, "corpus_sha256": corpus["corpus_sha256"],
            "models": {n: m["model_sha256"] for n, m in models.items()}, "rows": rows, "comparison": comparison,
            "tier": "A/B: first-party generated Boolean problems and fixed family holdouts",
            "limitations": ["Public generated families, not blind or external research problems",
                            "Equal checker budgets; model inference and feature computation have different wall costs",
                            "Single-seed sample, not evidence of broad scientific generalization or statistical superiority",
                            "Wilson intervals describe sampled task outcomes, not independent human participants",
                            "Graph ablation uses a fixed encoder and learned head; no end-to-end GNN was trained"],
            "pcs_authority": False}, trajectories


def reproduce(output, *, seed=20261009, per_family=24, epochs=24, bandit_episodes=1600, budgets=(4, 8)):
    output = Path(output)
    if output.exists():
        raise ValueError("Use a new output directory; existing research results are preserved")
    output.mkdir(parents=True)
    start = time.perf_counter()
    corpus = generate(seed=seed, per_family=per_family)
    write(output / "corpus.json", corpus)
    models = {}
    training_times = {}
    for mode in ("bag", "graph"):
        started = time.perf_counter()
        models[mode] = train(corpus, mode=mode, seed=seed, epochs=epochs)
        training_times[mode] = time.perf_counter() - started
        write(output / "models" / (mode + ".json"), models[mode])
    started = time.perf_counter()
    bandit = train_bandit(corpus, seed=seed, episodes=bandit_episodes)
    training_times["bandit"] = time.perf_counter() - started
    models["bandit"] = bandit["model"]
    write(output / "models/bandit.json", bandit["model"])
    write(output / "bandit-training.json", {k: v for k, v in bandit.items() if k != "model"})
    evaluation, trajectories = evaluate(corpus, models, budgets=budgets, seed=seed)
    write(output / "evaluation.json", evaluation)
    write(output / "trajectories.json", trajectories)
    write(output / "memory.json", memory(trajectories))
    positive = []
    for index, episode in enumerate(trajectories):
        if episode["solution"]:
            value = {**episode["original_task"], "candidate": episode["solution"]["candidate"]}
            positive.append(lean_source(value).replace("omega_equivalence", f"omega_equivalence_{index}"))
    (output / "VerifiedSolutions.lean").write_text("\n".join(positive), encoding="utf-8")
    # Include a genuine false target: compilation must reject it independently.
    (output / "RejectOriginal.lean").write_text(lean_source(corpus["records"][0]["task"]), encoding="utf-8")
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parents[3], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=Path(__file__).parents[3], text=True))
    except (OSError, subprocess.CalledProcessError):
        head, dirty = None, None
    config = {"format": "pcs-omega-run-v1", "seed": seed, "per_family": per_family,
              "epochs": epochs, "bandit_episodes": bandit_episodes, "checker_budgets": list(budgets),
              "dataset_counts": dict(Counter(r["partition"] for r in corpus["records"])),
              "training_wall_seconds": training_times, "elapsed_wall_seconds": time.perf_counter() - start,
              "python": sys.version, "platform": platform.platform(), "source_commit": head,
              "source_worktree_dirty": dirty, "omega_source_digest": source_digest(),
              "corpus_sha256": corpus["corpus_sha256"], "model_digests": {n: m["model_sha256"] for n, m in models.items()},
              "proposed_lean_theorems": len(positive), "lean_kernel_checked": False,
              "hardware": "CPU-only; standard-library training, no model API", "pcs_authority": False}
    write(output / "run.json", config)
    write_report(output, config, evaluation)
    return config


def verify_lean(output):
    """Compile fixed generated templates; this is not arbitrary-code execution."""
    output = Path(output)
    config = read_artifact(output / "run.json")
    trajectories = read_artifact(output / "trajectories.json")
    expected = []
    for index, episode in enumerate(trajectories):
        verify_episode(episode)
        if episode["solution"]:
            value = {**episode["original_task"], "candidate": episode["solution"]["candidate"]}
            expected.append(lean_source(value).replace("omega_equivalence", f"omega_equivalence_{index}"))
    corpus = validate_corpus(read_artifact(output / "corpus.json"))
    if ((output / "VerifiedSolutions.lean").read_text() != "\n".join(expected) or
            (output / "RejectOriginal.lean").read_text() != lean_source(corpus["records"][0]["task"])):
        raise ValueError("Only exact regenerated fixed proof templates may execute")
    if not expected:
        raise ValueError("No independently solved targets to kernel-check")
    # Only regenerated fixed templates execute. Strip cloud/API credentials;
    # this is not a general sandbox for submitted Lean or Python programs.
    environment = {k: os.environ[k] for k in ("PATH", "ELAN_HOME", "ELAN_TOOLCHAIN", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT", "WINDIR") if k in os.environ}
    version = subprocess.check_output(["lean", "--version"], text=True, timeout=30, env=environment)
    if "version 4.28.0" not in version:
        raise ValueError("Use the project-pinned Lean 4.28.0")
    positive = subprocess.run(["lean", str((output / "VerifiedSolutions.lean").resolve())], capture_output=True, text=True, timeout=180, env=environment)
    negative = subprocess.run(["lean", str((output / "RejectOriginal.lean").resolve())], capture_output=True, text=True, timeout=30, env=environment)
    (output / "lean-positive.log").write_text(positive.stdout + positive.stderr)
    (output / "lean-negative.log").write_text(negative.stdout + negative.stderr)
    if positive.returncode != 0 or negative.returncode == 0:
        raise ValueError("Positive kernel checks or the negative rejection control failed")
    # Each theorem emits its actual axiom inventory via #print axioms.
    inventories = [s for s in positive.stdout.splitlines() if "depends on axioms" in s or "does not depend on any axioms" in s]
    if len(inventories) != len(expected):
        raise ValueError("Incomplete actual theorem axiom inventory")
    receipt = {"format": "pcs-omega-lean-suite-v1", "lean_version": version.strip(),
               "positive_theorems": len(expected), "positive_sha256": hashlib.sha256("\n".join(expected).encode("utf-8")).hexdigest(),
               "negative_sha256": hashlib.sha256(lean_source(corpus["records"][0]["task"]).encode("utf-8")).hexdigest(),
               "negative_target_rejected": True, "axiom_inventory": inventories,
               "scope": "Concrete generated Boolean equivalence targets only; no Python/Lean generator refinement theorem or scientific-intent proof",
               "pcs_authority": False}
    write(output / "lean-result.json", receipt)
    config["lean_kernel_checked"] = True
    write(output / "run.json", config)
    write_report(output, config, read_artifact(output / "evaluation.json"))
    return receipt


def write_report(output, config, evaluation):
    lines = ["# PCS Omega experimental reasoning report", "", "This report records actual CPU training and independently replayed Boolean search. It does not establish general scientific intelligence.", "", "## Experiment", "",
             f"Seed: {config['seed']}. Source: `{config['source_commit']}`; dirty worktree: {config['source_worktree_dirty']}. Exact Omega source digest: `{config['omega_source_digest']}`.",
             f"Dataset: {config['dataset_counts']}. Fixed whole-family separation plus alpha-normalized source and truth-pair deduplication. First-party synthetic Apache-2.0 data; no participant data.",
             f"Models: weighted logistic heads (bag: 38 parameters; graph: 91); fixed two-round typed AST message passing; one-step REINFORCE bandit. Training times (seconds): {config['training_wall_seconds']}.",
             "", "## Held-out measurements", "", "| Partition | Strategy | Checker budget | Solved / tasks | Mean checks | Search seconds |", "|---|---|---:|---:|---:|---:|"]
    for r in evaluation["rows"]:
        lines.append(f"| {r['partition']} | {r['strategy']} | {r['checker_budget']} | {r['solved']} / {r['tasks']} | {r['mean_checker_calls']:.3f} | {r['search_wall_seconds']:.3f} |")
    lines += ["", "## Comparisons and limits", ""]
    for comparison in evaluation["comparison"]:
        lines.append(f"- {comparison['strategy']} at {comparison['checker_budget']} checks: solve-count difference {comparison['solve_count_delta']:+d} versus best sampled baseline {comparison['best_baseline']}.")
    lines += ["", "No superiority is assumed; retain the strongest baseline when learning does not improve it. Check budgets include the initial counterexample check. Candidate truth comes exclusively from the independent checker. Public held-out generated families are not blind, external projects, novel mathematics or clinical validation.",
              "", f"Generated theorem targets: {config['proposed_lean_theorems']}. Actual Lean suite checked: {config['lean_kernel_checked']}. Inspect lean-result.json for actual theorem/axiom inventory when present. Original falsified target is an independent negative compilation control.",
              "", "## Reproduce", "", "```bash", f"pcs omega reproduce --output NEW_DIRECTORY --seed {config['seed']} --per-family {config['per_family']} --epochs {config['epochs']} --bandit-episodes {config['bandit_episodes']}", "pcs omega verify-lean NEW_DIRECTORY", "```", "",
              "Artifacts: corpus.json, models/*.json, bandit-training.json, evaluation.json, trajectories.json, memory.json, generated Lean templates, run.json. Authority remains NONE; interpretation grounding and registered scientific assurance stay open."]
    (Path(output) / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
