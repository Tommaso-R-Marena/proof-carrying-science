"""Trainable position-sensitive expression DAG policy for existing proof search.

Models rank receiver-produced typed actions. Shared expressions and bound-variable
edges come from state_graph; the Lean environment remains the only verifier.
JSON checkpoints contain tensors, never executable deserialization.
"""
from pathlib import Path
import hashlib
import json
import torch
from torch import nn
from .state_graph import encode_state
from .model import KINDS, features, token
from .environment import render_action

FORMAT = "pcs-expression-dag-policy-v3"
ALIASES = {"induct_nat": "cases", "induct_list": "cases", "normalize": "simp", "rewrite_back": "rewrite"}


def tensors(state):
    graph = encode_state(state, max_nodes=4096, max_occurrences=16384)
    nodes = graph["nodes"]
    values = [token(n["kind"] + ":" + ("" if n["kind"] in {"local", "meta", "forall", "lambda", "let"} else n["value"])) for n in nodes]
    edges = []
    for parent, node in enumerate(nodes):
        for position, child in enumerate(node["children"]):
            edges.extend([(child, parent, min(position, 3)), (parent, child, 4 + min(position, 3))])
    paths = {}
    def occurrences(index, path):
        paths[tuple(path)] = index
        for position, child in enumerate(nodes[index]["children"]):
            occurrences(child, [*path, position])
    for root in graph["roots"]:
        occurrences(root["node"], [root["goal"], -1 if root["role"] == "target" else root["local"]])
    for binding in graph["bindings"]:
        source, target = paths[tuple(binding["occurrence_path"])], paths[tuple(binding["binder_path"])]
        edges.extend([(source, target, 8), (target, source, 9)])
    # Separate role nodes prevent unordered pooling from losing target/context.
    for root in graph["roots"]:
        index = len(values)
        values.append(token("role:" + root["role"]))
        edges.extend([(root["node"], index, 10), (index, root["node"], 11)])
    if not values:
        values = [token("closed")]
    return values, edges


class DAGPolicy(nn.Module):
    def __init__(self, width=16, architecture="dag"):
        super().__init__()
        if type(width) is not int or width != 16 or type(architecture) is not str or architecture not in {"dag", "bag"}:
            raise ValueError("unsupported DAG architecture")
        self.width, self.architecture = width, architecture
        self.tokens = nn.Embedding(257, width)
        self.actions = nn.Embedding(len(KINDS), width)
        self.edge_types = nn.Embedding(12, width)
        self.message = nn.Linear(width, width)
        self.update = nn.Linear(2 * width, width)
        self.policy = nn.Sequential(nn.Linear(2 * width + 12, width), nn.Tanh(), nn.Linear(width, 1))
        self.value = nn.Linear(width, 1)
        self.uncertainty = nn.Linear(width, 1)

    def forward(self, state, options):
        values, edges = tensors(state)
        device = self.tokens.weight.device
        h = self.tokens(torch.tensor(values, device=device))
        if self.architecture == "dag" and edges:
            source, target, relation = torch.tensor(edges, device=device).T
            for _ in range(2):
                messages = torch.tanh(self.message(h[source]) + self.edge_types(relation))
                aggregate = torch.zeros_like(h).index_add(0, target, messages)
                count = torch.zeros(len(values), device=device).index_add(0, target, torch.ones(len(target), device=device))
                h = torch.tanh(self.update(torch.cat([h, aggregate / count.clamp_min(1).unsqueeze(1)], dim=1)))
        pooled = h.mean(0)
        for option in options:
            render_action(option)
        if options:
            actions = self.actions(torch.tensor([KINDS.index(ALIASES.get(a["kind"], a["kind"])) for a in options], device=device))
            actions = actions + self.tokens(torch.tensor([token("action:" + str(a["argument"])) for a in options], device=device))
            extra = torch.tensor([features(state, a) for a in options], device=device)
            logits = self.policy(torch.cat([pooled.expand(len(options), -1), actions, extra], dim=1)).squeeze(1)
        else:
            logits = pooled.new_empty(0)
        return logits, self.value(pooled).squeeze(), self.uncertainty(pooled).sigmoid().squeeze()

    def rank(self, state, options):
        self.eval()
        with torch.no_grad():
            return self(state, options)[0].cpu().tolist()

    def save(self, path, metadata):
        payload = {"format": FORMAT, "width": self.width, "architecture": self.architecture,
                   "metadata": metadata, "weights": {k: v.detach().cpu().tolist() for k, v in self.state_dict().items()}}
        Path(path).write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @classmethod
    def load(cls, path, expected_sha):
        raw = Path(path).read_bytes()
        if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError("checkpoint integrity failure")
        payload = json.loads(raw)
        if set(payload) != {"format", "width", "architecture", "metadata", "weights"} or payload["format"] != FORMAT:
            raise ValueError("unsupported DAG checkpoint")
        model = cls(payload["width"], payload["architecture"])
        if type(payload["weights"]) is not dict or set(payload["weights"]) != set(model.state_dict()):
            raise ValueError("checkpoint tensor schema mismatch")
        try:
            weights = {k: torch.tensor(v) for k, v in payload["weights"].items()}
        except (TypeError, ValueError, RuntimeError):
            raise ValueError("invalid checkpoint tensor encoding") from None
        if any(not torch.isfinite(v).all() or v.shape != model.state_dict()[k].shape for k, v in weights.items()):
            raise ValueError("invalid checkpoint tensor")
        model.load_state_dict(weights, strict=True)
        return model
