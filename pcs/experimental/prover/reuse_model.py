"""Trainable goal/premise graph matching, using kernel-extracted lemma types.

The cross-attention head compares a goal representation with each checked lemma
representation. This is an untrusted ranking model; Lean decides applicability.
"""
import hashlib
import json
from pathlib import Path

import torch
from torch import nn

from .model import ReasoningNetwork, KINDS, features, token


class ReuseNetwork(ReasoningNetwork):
    def __init__(self, width=24, architecture="graph"):
        super().__init__(width, architecture)
        self.goal_query = nn.Linear(width, width, bias=False)
        self.premise_key = nn.Linear(width, width, bias=False)
        self.premise_gate = nn.Linear(width * 2, 1)

    def forward(self, state, options):
        logits, value, uncertainty = super().forward(state, options)
        if not options:
            return logits, value, uncertainty
        goal = self.encode(state)
        catalog = {e["name"]: e["expression"] for e in state.get("available_lemmas", [])}
        additions = []
        for action in options:
            expression = catalog.get(action["argument"])
            if action["kind"] in {"apply", "rewrite", "rewrite_back"} and expression is not None:
                premise = self.encode({"goals": [{"target": "checked lemma", "locals": [], "expression": expression}]})
                attention = (self.goal_query(goal) * self.premise_key(premise)).sum() / self.width ** .5
                gate = self.premise_gate(torch.cat([goal, premise])).squeeze()
                additions.append(attention + gate)
            else:
                additions.append(goal.new_zeros(()))
        return logits + torch.stack(additions), value, uncertainty

    def save(self, path, metadata):
        payload = {"format": "pcs-reuse-network-v1", "width": self.width,
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
        if set(p) != {"format", "width", "architecture", "metadata", "weights"} or p["format"] != "pcs-reuse-network-v1" or p["width"] != 24:
            raise ValueError("unsupported reuse checkpoint")
        model = cls(p["width"], p["architecture"])
        state = {k: torch.tensor(v) for k, v in p["weights"].items()}
        if any(not torch.isfinite(v).all() for v in state.values()):
            raise ValueError("non-finite checkpoint")
        model.load_state_dict(state, strict=True)
        return model
