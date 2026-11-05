"""Trainable English encoder for restricted formalization-domain ranking.

This is a grammar-constrained classifier/reranker, not a general English-to-Lean
sequence model. Grammar and type checking remain receiver-owned.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import torch
from torch import nn

from .language import formalize
from .model import token
from .ir import digest


class FormalizationRanker(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(257, 16)
        self.head = nn.Sequential(nn.Linear(16, 16), nn.Tanh(), nn.Linear(16, 4))

    def forward(self, text):
        words = re.findall(r"[a-z]+|[0-9]+|[^\s]", text.lower())[:512]
        if not words:
            raise ValueError("empty formalization input")
        indices = torch.tensor([token(w) for w in words], device=self.embedding.weight.device)
        return self.head(self.embedding(indices).mean(0))

    def rank(self, source, ir):
        domains = {b["type"] for b in ir["binders"]}
        label = {"Prop": 0, "Nat": 1, "Int": 2}.get(next(iter(domains), ""), 3)
        with torch.no_grad():
            return float(self(source).softmax(0)[label])

    def save(self, path):
        payload = {"format": "pcs-formalization-ranker-v1", "weights": {
            k: v.detach().cpu().tolist() for k, v in self.state_dict().items()}}
        Path(path).write_text(json.dumps(payload, separators=(",", ":")) + "\n")
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @classmethod
    def load(cls, path, expected_sha):
        raw = Path(path).read_bytes()
        if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError("formalization checkpoint integrity failure")
        p = json.loads(raw)
        if set(p) != {"format", "weights"} or p["format"] != "pcs-formalization-ranker-v1":
            raise ValueError("unsupported formalization checkpoint")
        model = cls()
        state = {k: torch.tensor(v) for k, v in p["weights"].items()}
        if any(not torch.isfinite(v).all() for v in state.values()):
            raise ValueError("nonfinite formalization checkpoint")
        model.load_state_dict(state, strict=True)
        return model


def train(path, seed=19, epochs=60):
    torch.manual_seed(seed)
    pairs = []
    for name in ["a", "b", "c", "x", "y", "z", "u", "v"]:
        for frame in ["For all", "For every", "For any"]:
            for words, label, formula in [("propositions", 0, f"{name} implies {name}"),
                ("natural numbers", 1, f"{name} + 0 equals {name}"),
                ("integers", 2, f"{name} equals {name}")]:
                text = f"{frame} {words} {name}, {formula}."
                result = formalize(text)
                if result["status"] != "supported":
                    raise RuntimeError("unpaired training source")
                pairs.append({"text": text, "label": label, "ir": result["candidates"][0]["ir"],
                              "license": "Apache-2.0", "source": "PCS authored", "split": "train"})
    for text in ["Prove everything.", "Every graph is connected.", "For all real numbers x, x is blue."]:
        pairs.append({"text": text, "label": 3, "ir": None, "license": "Apache-2.0", "source": "PCS authored", "split": "train"})
    model = FormalizationRanker()
    before = digest({k: v.tolist() for k, v in model.state_dict().items()})
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    for _ in range(epochs):
        for i in torch.randperm(len(pairs)).tolist():
            example = pairs[i]
            loss = nn.functional.cross_entropy(model(example["text"]).unsqueeze(0), torch.tensor([example["label"]]))
            optimizer.zero_grad(); loss.backward(); optimizer.step()
    sha = model.save(path)
    after = digest({k: v.tolist() for k, v in model.state_dict().items()})
    return model, {"checkpoint_sha256": sha, "parameters": sum(p.numel() for p in model.parameters()),
                   "epochs": epochs, "examples": len(pairs), "dataset_sha256": digest(pairs),
                   "weights_changed": before != after, "pairs": pairs,
                   "limitations": "Learns restricted domain/abstention ranking; does not learn general structured output or certify English intent."}
