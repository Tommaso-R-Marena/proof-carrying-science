"""Small CPU/GPU PyTorch graph policy, value and invalid-action heads.

Models select from receiver-produced actions. They cannot alter Lean authority.
Weights are portable JSON arrays; loading never executes pickle or model code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch
from torch import nn

from .environment import candidates, reference_expression
from .ir import digest

torch.set_num_threads(2)
KINDS = ["intro", "constructor", "assumption", "rfl", "left", "right",
         "contradiction", "simp", "exact", "apply", "cases", "rewrite", "lemma", "witness"]


def token(s):
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:4], "big") % 257


def graph(state):
    nodes, edges = [token("state")], []
    def visit(expr, parent):
        i = len(nodes)
        value = expr["value"]
        # Remove elaborator allocation identifiers from learnt expression tokens.
        if expr["kind"] in {"local", "goal"}:
            value = ""
        nodes.append(token(expr["kind"] + ":" + value))
        edges.extend([(parent, i), (i, parent)])
        for child in expr["children"]:
            visit(child, i)
    for goal in state["goals"]:
        i = len(nodes)
        nodes.append(token("target"))
        edges.extend([(0, i), (i, 0)])
        visit(goal["expression"], i)
        for local in goal["locals"]:
            j = len(nodes)
            nodes.append(token("hypothesis:" + local["type"]))
            edges.extend([(i, j), (j, i)])
            visit(local["expression"], j)
    if len(nodes) > 4096:
        raise ValueError("state graph exceeds bound")
    return nodes, edges


def features(state, action):
    g = state["goals"][0] if state["goals"] else {"target": "", "locals": [], "expression": {"kind": ""}}
    arg = str(action["argument"] or "")
    direct = next((l["type"] for l in g["locals"] if l["name"] == arg), "")
    matching = bool(state["goals"]) and action["kind"] == "exact" and reference_expression(state, arg) == g["expression"]
    return [float(matching), float("∧" in direct),
            float("→" in direct), float("=" in direct), float(g["expression"]["kind"] == "forall"),
            float("∧" in g["target"]), float("∨" in g["target"]), float("=" in g["target"]),
            min(len(g["locals"]), 12) / 12, min(len(state["goals"]), 8) / 8,
            float(arg.endswith(".1")), float(arg.endswith(".2"))]


class ReasoningNetwork(nn.Module):
    def __init__(self, width=24, architecture="graph"):
        super().__init__()
        if architecture not in {"graph", "bag"}:
            raise ValueError("unknown architecture")
        self.width, self.architecture = width, architecture
        self.tokens = nn.Embedding(257, width)
        self.actions = nn.Embedding(len(KINDS), width)
        self.message = nn.Linear(width, width)
        self.update = nn.Linear(width * 2, width)
        self.policy = nn.Sequential(nn.Linear(width * 2 + 12, width), nn.Tanh(), nn.Linear(width, 1))
        self.value = nn.Sequential(nn.Linear(width, width), nn.Tanh(), nn.Linear(width, 1))
        self.uncertainty = nn.Linear(width, 1)

    def encode(self, state):
        device = self.tokens.weight.device
        nodes, edges = graph(state)
        h = self.tokens(torch.tensor(nodes, device=device))
        if self.architecture == "graph" and edges:
            src, dst = torch.tensor(edges, device=device).T
            for _ in range(2):
                messages = self.message(h[src])
                aggregated = torch.zeros_like(h).index_add(0, dst, messages)
                counts = torch.zeros(len(nodes), device=device).index_add(0, dst, torch.ones(len(dst), device=device))
                h = torch.tanh(self.update(torch.cat([h, aggregated / counts.clamp_min(1).unsqueeze(1)], dim=1)))
        return h.mean(0)

    def forward(self, state, options):
        h = self.encode(state)
        device = h.device
        if options:
            a = self.actions(torch.tensor([KINDS.index(o["kind"]) for o in options], device=device))
            a = a + self.tokens(torch.tensor([token("action:" + str(o["argument"])) for o in options], device=device))
            f = torch.tensor([features(state, o) for o in options], device=device)
            logits = self.policy(torch.cat([h.expand(len(options), -1), a, f], dim=1)).squeeze(1)
        else:
            logits = h.new_empty(0)
        return logits, self.value(h).squeeze(), self.uncertainty(h).sigmoid().squeeze()

    def rank(self, state, options):
        self.eval()
        with torch.no_grad():
            return self(state, options)[0].cpu().tolist()

    def save(self, path, metadata):
        payload = {"format": "pcs-reasoning-network-v1", "width": self.width,
                   "architecture": self.architecture, "metadata": metadata,
                   "weights": {k: v.detach().cpu().tolist() for k, v in self.state_dict().items()}}
        Path(path).write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @classmethod
    def load(cls, path, expected_sha):
        raw = Path(path).read_bytes()
        if len(raw) > 2_000_000 or hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError("checkpoint integrity failure")
        p = json.loads(raw)
        if set(p) != {"format", "width", "architecture", "metadata", "weights"} or p["format"] != "pcs-reasoning-network-v1" or p["width"] != 24:
            raise ValueError("unsupported checkpoint")
        model = cls(p["width"], p["architecture"])
        state = {k: torch.tensor(v) for k, v in p["weights"].items()}
        if any(not torch.isfinite(v).all() for v in state.values()):
            raise ValueError("non-finite checkpoint")
        model.load_state_dict(state, strict=True)
        return model


def imitate(model, episodes, epochs=40, seed=17):
    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=.008)
    examples = []
    for episode in episodes:
        if episode["split"] != "train" or episode["result"]["status"] != "verified":
            continue
        actions = episode["result"]["receipt"]["actions"]
        for i, action in enumerate(actions):
            state = episode["result"]["states"][i]
            options = candidates(state)
            if action in options:
                examples.append((state, options, options.index(action), len(actions) - i))
    if not examples:
        raise ValueError("no independently verified training transitions")
    initial = {n: p.detach().clone() for n, p in model.named_parameters()}
    losses = []
    for _ in range(epochs):
        for i in torch.randperm(len(examples)).tolist():
            state, options, label, remaining = examples[i]
            logits, value, uncertainty = model(state, options)
            loss = nn.functional.cross_entropy(logits.unsqueeze(0), torch.tensor([label], device=logits.device))
            loss = loss + .1 * (value - 1 / remaining).square() + .02 * uncertainty.square()
            opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.); opt.step()
        losses.append(float(loss.detach()))
    return {"examples": len(examples), "epochs": epochs, "last_loss": losses[-1],
            "changed_parameters": [n for n, p in model.named_parameters() if not torch.equal(p, initial[n])],
            "training_data_sha256": digest([{ "goal": e["goal"], "actions": e["result"]["receipt"]["actions"]}
                                           for e in episodes if e["split"] == "train" and e["result"]["status"] == "verified"])}


def actor_critic(model, env, training_tasks, episodes=16, seed=31):
    """On-policy sequential actor–critic; only env.step determines rewards."""
    torch.manual_seed(seed)
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    records = []
    before = digest({k: v.detach().tolist() for k, v in model.state_dict().items()})
    for episode in range(episodes):
        task = training_tasks[episode % len(training_tasks)]
        if task["split"] != "train":
            raise ValueError("evaluation firewall: RL may use training tasks only")
        state, info = env.reset(task["goal"])
        logs, values, rewards, entropies, trace = [], [], [], [], []
        for step in range(env.max_steps):
            options = candidates(state)
            logits, value, _ = model(state, options)
            distribution = torch.distributions.Categorical(logits=logits)
            selected = distribution.sample()
            action = options[int(selected)]
            next_state, reward, terminated, truncated, result = env.step(action)
            logs.append(distribution.log_prob(selected)); values.append(value)
            entropies.append(distribution.entropy()); rewards.append(reward)
            trace.append({"state": state, "action": action, "reward": reward, "status": result["status"]})
            state = next_state
            if terminated or truncated:
                break
        returns, total = [], 0.
        for reward in reversed(rewards):
            total = reward + .97 * total
            returns.insert(0, total)
        loss = sum(-log * (value.new_tensor(ret) - value.detach()) + .5 * (value - ret).square() - .002 * entropy
                   for log, value, ret, entropy in zip(logs, values, returns, entropies)) / len(logs)
        optimizer.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step()
        records.append({"goal_sha256": info["goal_sha256"], "steps": trace,
                        "status": result["status"], "receipt": result.get("receipt"),
                        "error": result.get("error"), "loss": float(loss.detach())})
    after = digest({k: v.detach().tolist() for k, v in model.state_dict().items()})
    return {"algorithm": "sequential-on-policy-actor-critic-v1", "before": before, "after": after,
            "weights_changed": before != after, "episodes": records,
            "verified_episodes": sum(r["status"] == "verified" for r in records)}
