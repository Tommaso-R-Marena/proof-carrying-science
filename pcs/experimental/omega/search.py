"""Budgeted search, replayable trajectories, and a genuine checker RL environment."""
from __future__ import annotations

from copy import deepcopy
import math
import random
import re

from .logic import action_id, actions, apply_action, check, digest, exact, integer, task, verify_receipt
from .learning import features, rank, checkpoint, dimension, source_digest


def structural_distance(a, b):
    if a == b:
        return 0
    if a["op"] != b["op"]:
        return 1 + sum(structural_distance(a.get(k, {"op": "false"}), b.get(k, {"op": "false"}))
                       for k in ("body", "left", "right") if k in a or k in b)
    if a["op"] == "atom":
        return int(a["symbol"] != b["symbol"])
    return sum(structural_distance(a[k], b[k]) for k in ("body", "left", "right") if k in a)


def search(value, *, strategy="structural", model=None, checks=8, depth=3, seed=42):
    task(value)
    integer(checks, 1, 128, "checker budget")
    integer(depth, 1, 4, "search depth")
    integer(seed, 0, 2**32 - 1, "search seed")
    if strategy not in {"bfs", "random", "structural", "learned"}:
        raise ValueError("Unsupported search strategy")
    if strategy == "learned" and model is None:
        raise ValueError("Learned search requires an actual checkpoint")
    initial, attempts, solved = check(value), [], None
    frontier = [(deepcopy(value["candidate"]), 0)]
    seen = {digest(value["candidate"])}
    rng = random.Random(seed)
    used = 1
    if initial["equivalent"]:
        solved = {"candidate": deepcopy(value["candidate"]), "receipt": initial}
    while frontier and used < checks and solved is None:
        formula, level = frontier.pop(0)
        if level >= depth:
            continue
        current = {**value, "candidate": formula}
        candidates = actions(formula, value["variables"])
        if strategy == "random":
            rng.shuffle(candidates)
        elif strategy == "structural":
            candidates.sort(key=lambda a: (structural_distance(value["source"], apply_action(formula, a, value["variables"])), action_id(a)))
        elif strategy == "learned":
            candidates = rank(current, candidates, model)
        for action in candidates:
            candidate = apply_action(formula, action, value["variables"])
            key = digest(candidate)
            if key in seen:
                continue
            seen.add(key)
            receipt = check({**value, "candidate": candidate})
            used += 1
            attempts.append({"parent_sha256": digest(formula), "action": action,
                             "candidate": candidate, "depth": level + 1, "receipt": receipt})
            if receipt["equivalent"]:
                solved = {"candidate": candidate, "receipt": receipt}
                break
            frontier.append((candidate, level + 1))
            # Both generated states and checker invocations are strictly bounded.
            if used == checks:
                break
    result = {"format": "pcs-omega-search-v1", "original_task": deepcopy(value),
              "original_task_sha256": digest(value), "strategy": strategy,
              "model_sha256": model["model_sha256"] if model is not None else None,
              "seed": seed, "budget": {"checks": checks, "depth": depth},
              "initial_receipt": initial, "attempts": attempts, "checks_used": used,
              "status": "BOOLEAN_VERIFIED" if solved is not None else "BUDGET_OR_SEARCH_EXHAUSTED",
              "solution": solved, "pcs_authority": False, "lean_kernel_checked": False}
    result["episode_sha256"] = digest(result)
    return result


def verify_episode(episode):
    exact(episode, {"format", "original_task", "original_task_sha256", "strategy", "model_sha256",
                    "seed", "budget", "initial_receipt", "attempts", "checks_used", "status", "solution",
                    "pcs_authority", "lean_kernel_checked", "episode_sha256"}, "episode")
    if episode["format"] != "pcs-omega-search-v1" or episode["pcs_authority"] is not False or episode["lean_kernel_checked"] is not False:
        raise ValueError("Unsupported episode or false authority")
    if type(episode["strategy"]) is not str or episode["strategy"] not in {"bfs", "random", "structural", "learned"}:
        raise ValueError("Unsupported recorded strategy")
    integer(episode["seed"], 0, 2**32 - 1, "seed")
    integer(episode["checks_used"], 1, 128, "checks used")
    if episode["model_sha256"] is not None and (type(episode["model_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", episode["model_sha256"])):
        raise ValueError("Invalid checkpoint binding")
    if episode["strategy"] == "learned" and episode["model_sha256"] is None:
        raise ValueError("Learned episode missing checkpoint binding")
    value = task(episode["original_task"])
    if episode["original_task_sha256"] != digest(value):
        raise ValueError("Original scientific target changed")
    exact(episode["budget"], {"checks", "depth"}, "budget")
    budget = integer(episode["budget"]["checks"], 1, 128, "checker budget")
    limit = integer(episode["budget"]["depth"], 1, 4, "depth")
    verify_receipt(value, episode["initial_receipt"])
    states = {digest(value["candidate"]): (value["candidate"], 0)}
    entries = episode["attempts"]
    if type(entries) is not list or len(entries) >= budget or episode["checks_used"] != len(entries) + 1:
        raise ValueError("Checker accounting drift")
    solved = {"candidate": value["candidate"], "receipt": episode["initial_receipt"]} if episode["initial_receipt"]["equivalent"] else None
    for entry in entries:
        exact(entry, {"parent_sha256", "action", "candidate", "depth", "receipt"}, "attempt")
        integer(entry["depth"], 1, limit, "transition depth")
        if solved is not None or entry["parent_sha256"] not in states:
            raise ValueError("Missing parent or transitions after termination")
        parent, level = states[entry["parent_sha256"]]
        candidate = apply_action(parent, entry["action"], value["variables"])
        key = digest(candidate)
        if candidate != entry["candidate"] or key in states or entry["depth"] != level + 1 or level + 1 > limit:
            raise ValueError("Forged action, repeated state or depth")
        verify_receipt({**value, "candidate": candidate}, entry["receipt"])
        states[key] = (candidate, level + 1)
        if entry["receipt"]["equivalent"]:
            solved = {"candidate": candidate, "receipt": entry["receipt"]}
    if episode["solution"] != solved or episode["status"] != ("BOOLEAN_VERIFIED" if solved else "BUDGET_OR_SEARCH_EXHAUSTED"):
        raise ValueError("False terminal reward or solution")
    if episode["episode_sha256"] != digest({k: v for k, v in episode.items() if k != "episode_sha256"}):
        raise ValueError("Episode commitment mismatch")
    return True


class ReasoningEnv:
    """No submitted execution: constrained AST transitions and fixed checker reward."""

    def __init__(self, value, *, budget=8):
        self._initial = deepcopy(task(value))
        self._goal_sha = digest(self._initial["source"])
        self.budget = integer(budget, 1, 128, "environment budget")
        self.reset()

    def reset(self):
        self._value = deepcopy(self._initial)
        self.steps = 0
        self.checks = 1
        self.receipt = check(self._value)
        self.done = self.receipt["equivalent"]
        self.history = []
        return self.observe()

    def observe(self):
        return {"format": "pcs-omega-proof-state-v1", "task": deepcopy(self._value),
                "source_sha256": self._goal_sha, "receipt": deepcopy(self.receipt),
                "actions_remaining": self.budget - self.steps, "done": self.done,
                "pcs_authority": False}

    def step(self, action):
        if digest(self._value["source"]) != self._goal_sha:
            raise ValueError("Immutable reasoning goal changed")
        if self.done or self.steps >= self.budget:
            raise ValueError("Episode already terminated")
        self.steps += 1
        feedback, reward = "INVALID_ACTION", -0.1
        try:
            if action == {"kind": "ABSTAIN"}:
                self.done, feedback, reward = True, "ABSTAINED", 0.0
            elif action in ({"kind": "CHECK_EQUIVALENCE"}, {"kind": "REQUEST_COUNTEREXAMPLE"}):
                self.receipt = check(self._value)
                self.checks += 1
                feedback, reward = "RECHECKED", -0.02
            else:
                formula = apply_action(self._value["candidate"], action, self._value["variables"])
                self._value = {**self._value, "candidate": formula}
                self.receipt = check(self._value)
                self.checks += 1
                feedback = "BOOLEAN_VERIFIED" if self.receipt["equivalent"] else "COUNTEREXAMPLE"
                reward = 1.0 if self.receipt["equivalent"] else -0.02
        except (ValueError, KeyError, TypeError):
            pass
        self.done = self.done or self.receipt["equivalent"] or self.steps == self.budget
        event = {"action": deepcopy(action), "feedback": feedback, "reward": reward,
                 "task_sha256": digest(self._value), "checks_used": self.checks}
        self.history.append(event)
        return {"state": self.observe(), "reward": reward, "terminated": self.done, "feedback": feedback}


def train_bandit(corpus, *, seed=20261009, episodes=1600):
    from .corpus import validate_corpus
    validate_corpus(corpus)
    integer(episodes, 1, 20000, "bandit episodes")
    integer(seed, 0, 2**32 - 1, "seed")
    records = [r for r in corpus["records"] if r["partition"] == "train"]
    if not records:
        raise ValueError("No training episodes")
    rng, weights, wins = random.Random(seed), [0.0] * dimension("graph"), 0
    trace = []
    for index in range(episodes):
        record = records[rng.randrange(len(records))]
        value, env = record["task"], ReasoningEnv(record["task"], budget=1)
        candidates = actions(value["candidate"], value["variables"])
        vectors = [features(value, a, "graph") for a in candidates]
        scores = [sum(x * w for x, w in zip(xs, weights)) for xs in vectors]
        scale = max(scores)
        exps = [math.exp(max(-40, s - scale)) for s in scores]
        probabilities = [s / sum(exps) for s in exps]
        chosen = rng.choices(range(len(candidates)), weights=probabilities)[0]
        transition = env.step(candidates[chosen])
        reward = transition["reward"]
        wins += int(reward == 1.0)
        for i in range(len(weights)):
            expected = sum(p * x[i] for p, x in zip(probabilities, vectors))
            weights[i] += 0.08 * reward * (vectors[chosen][i] - expected)
        trace.append({"episode": index, "task_id": record["id"], "action": candidates[chosen],
                      "reward": reward, "feedback": transition["feedback"],
                      "task_sha256": record["task_sha256"], "receipt": transition["state"]["receipt"]})
    meta = {"algorithm": "one-step-contextual-bandit-REINFORCE", "seed": seed, "epochs": episodes,
            "examples": episodes, "task_ids": [r["id"] for r in records], "families": sorted({r["family"] for r in records}),
            "task_digests": [r["task_sha256"] for r in records], "source_digest": source_digest(), "corpus_sha256": digest(records)}
    return {"model": checkpoint(weights, "graph", meta), "training_wins": wins, "episodes": episodes,
            "trace": trace, "scope": "One-step bandit; no demonstrated long-horizon RL or external scientific transfer"}


def memory(episodes):
    """Replay before retention; speculative notes cannot become trusted premises."""
    if type(episodes) is not list or len(episodes) > 1024:
        raise ValueError("Research memory size bound exceeded")
    entries = []
    for episode in episodes:
        verify_episode(episode)
        entries.append({"episode_sha256": episode["episode_sha256"], "original_task_sha256": episode["original_task_sha256"],
                        "boolean_result": episode["status"], "counterexample": episode["initial_receipt"]["counterexample"],
                        "checks_used": episode["checks_used"], "scientific_premise_authority": False})
    core = {"format": "pcs-omega-research-memory-v1", "entries": entries, "pcs_authority": False}
    return {**core, "memory_sha256": digest(core)}
