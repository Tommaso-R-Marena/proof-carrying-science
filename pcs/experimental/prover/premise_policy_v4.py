"""Grounded goal/premise interaction network; Lean remains the only authority.

The model receives signatures from the receiver's exact theorem catalog rather
than learning theorem-name embeddings. JSON checkpoints never execute pickle.
"""
from pathlib import Path
import hashlib
import json
import math
import torch
from torch import nn
from .dag_policy_v3 import tensors
from .model import token
from .induction_ir import digest
from .environment import reference_expression

FORMAT = "pcs-grounded-premise-policy-v4"
torch.set_num_threads(2)


def premise_name(action):
    argument = action.get("argument")
    if type(argument) is str:
        return argument
    if type(argument) is dict:
        return argument.get("premise", argument.get("name", ""))
    return action.get("premise", "")


class PremisePolicy(nn.Module):
    def __init__(self, catalog, *, architecture="graph", width=16):
        super().__init__()
        if architecture not in {"graph", "bag"} or type(width) is not int or width != 16:
            raise ValueError("unsupported grounded architecture")
        if type(catalog) is not list or not 1 <= len(catalog) <= 4096:
            raise ValueError("bounded real theorem catalog required")
        self.catalog = {}
        for entry in catalog:
            if type(entry) is not dict or type(entry.get("name")) is not str or type(entry.get("expression")) is not dict:
                raise ValueError("elaborated premise signature required")
            if entry["name"] in self.catalog:
                raise ValueError("duplicate theorem catalog name")
            self.catalog[entry["name"]] = entry
        self.catalog_sha256 = digest(catalog)
        self.architecture, self.width = architecture, width
        self.tokens = nn.Embedding(257, width)
        self.edge_types = nn.Embedding(12, width)
        self.message = nn.Linear(width, width)
        self.update = nn.Linear(2 * width, width)
        self.action_kind = nn.Embedding(257, width)
        self.policy = nn.Sequential(nn.Linear(5 * width + 4, width), nn.Tanh(), nn.Linear(width, 1))
        self.value = nn.Linear(width, 1)
        self.uncertainty = nn.Linear(width, 1)
        self._signature_graphs = {}
        self.inference_calls = 0

    def signature(self, state, action):
        name = premise_name(action)
        if action["kind"].endswith("_lemma"):
            if type(name) is not str or name not in self.catalog:
                raise ValueError("unknown receiver theorem signature")
            return self.catalog[name]["expression"]
        if not (action["kind"].endswith("_local") or action["kind"].startswith("induction_")):
            return None
        if type(name) is not str or any(part not in {"1", "2"} for part in name.split(".")[1:]):
            raise ValueError("unknown local proof signature")
        expression = reference_expression(state, name) if state["goals"] else None
        if expression is not None:
            return expression
        raise ValueError("unknown local proof signature")

    @staticmethod
    def _statement(expression):
        return {"goals": [{"expression": expression, "target": "", "locals": []}]}

    def _encode(self, values, edges):
        device = self.tokens.weight.device
        h = self.tokens(torch.tensor(values, device=device))
        if self.architecture == "graph" and edges:
            source, target, relation = torch.tensor(edges, device=device).T
            for _ in range(2):
                messages = torch.tanh(self.message(h[source]) + self.edge_types(relation))
                aggregate = torch.zeros_like(h).index_add(0, target, messages)
                count = torch.zeros(len(values), device=device).index_add(0, target, torch.ones(len(target), device=device))
                h = torch.tanh(self.update(torch.cat([h, aggregate / count.clamp_min(1).unsqueeze(1)], dim=1)))
        return h.mean(0)

    def forward(self, state, options):
        # Catalog metadata cannot accidentally become model proof-state features.
        goal = self._encode(*tensors({"goals": state["goals"]}))
        if not options:
            return goal.new_empty(0), self.value(goal).squeeze(), self.uncertainty(goal).sigmoid().squeeze()
        premises, kind_tokens, extras = [], [], []
        encoded_signatures = {}
        for action in options:
            if type(action) is not dict or type(action.get("kind")) is not str:
                raise ValueError("typed receiver action required")
            expression = self.signature(state, action)
            if expression is None:
                premise = self.tokens(torch.tensor(token("no-premise"), device=goal.device))
            else:
                identity = digest(expression)
                if identity not in self._signature_graphs:
                    if len(self._signature_graphs) >= 4096:
                        self._signature_graphs.clear()
                    self._signature_graphs[identity] = tensors(self._statement(expression))
                if identity not in encoded_signatures:
                    encoded_signatures[identity] = self._encode(*self._signature_graphs[identity])
                premise = encoded_signatures[identity]
            premises.append(premise)
            # Direction/position are action grammar data, never theorem names.
            argument = action.get("argument")
            direction = argument.get("direction", "") if type(argument) is dict else ""
            occurrence = argument.get("occurrence", 0) if type(argument) is dict else 0
            kind_tokens.append(token("action-kind:" + action["kind"] + ":" + str(direction)))
            extras.append([float(expression is not None), min(len(state["goals"]), 8) / 8,
                           min(sum(len(g["locals"]) for g in state["goals"]), 24) / 24,
                           min(occurrence, 4) / 4])
        premises = torch.stack(premises)
        goals = goal.expand(len(options), -1)
        kinds = self.action_kind(torch.tensor(kind_tokens, device=goal.device))
        numeric = torch.tensor(extras, device=goal.device)
        logits = self.policy(torch.cat([goals, premises, goals * premises, (goals - premises).abs(), kinds, numeric], dim=1)).squeeze(1)
        return logits, self.value(goal).squeeze(), self.uncertainty(goal).sigmoid().squeeze()

    def rank(self, state, options):
        self.eval(); self.inference_calls += 1
        with torch.no_grad():
            return self(state, options)[0].cpu().tolist()

    def payload(self, metadata):
        return {"format": FORMAT, "architecture": self.architecture, "width": self.width,
                "catalog_sha256": self.catalog_sha256, "metadata": metadata,
                "weights": {k: v.detach().cpu().tolist() for k, v in self.state_dict().items()}}

    def save(self, path, metadata):
        raw = (json.dumps(self.payload(metadata), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        Path(path).write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def from_payload(cls, payload, catalog):
        if type(payload) is not dict or set(payload) != {"format", "architecture", "width", "catalog_sha256", "metadata", "weights"} or payload["format"] != FORMAT:
            raise ValueError("unsupported premise checkpoint")
        model = cls(catalog, architecture=payload["architecture"], width=payload["width"])
        if model.catalog_sha256 != payload["catalog_sha256"]:
            raise ValueError("checkpoint bound to a different theorem catalog")
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

    @classmethod
    def load(cls, path, expected_sha, catalog):
        raw = Path(path).read_bytes()
        if len(raw) > 2_000_000 or hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError("checkpoint integrity failure")
        return cls.from_payload(json.loads(raw), catalog)


def save_training_checkpoint(path, model, optimizer, progress):
    if type(optimizer) is not torch.optim.Adam or len(optimizer.param_groups) != 1:
        raise ValueError("only explicit single-group Adam resume is supported")
    state = optimizer.state_dict()
    payload = {"format": "pcs-premise-adam-resume-v4", "model": model.payload({"experimental": True}),
               "optimizer": {"param_groups": state["param_groups"], "state": {
                   str(index): {key: value.detach().cpu().tolist() if torch.is_tensor(value) else value for key, value in entry.items()}
                   for index, entry in state["state"].items()}},
               "torch_rng": torch.get_rng_state().tolist(), "progress": progress}
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    Path(path).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def load_training_checkpoint(path, expected_sha, catalog):
    raw = Path(path).read_bytes()
    if len(raw) > 4_000_000 or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("training checkpoint integrity failure")
    payload = json.loads(raw)
    if type(payload) is not dict or set(payload) != {"format", "model", "optimizer", "torch_rng", "progress"} or payload["format"] != "pcs-premise-adam-resume-v4":
        raise ValueError("unsupported optimizer checkpoint")
    model = PremisePolicy.from_payload(payload["model"], catalog)
    encoded = payload["optimizer"]
    if type(encoded) is not dict or set(encoded) != {"param_groups", "state"} or type(encoded["state"]) is not dict:
        raise ValueError("invalid optimizer schema")
    groups = encoded["param_groups"]
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    expected_groups = optimizer.state_dict()["param_groups"]
    if type(groups) is not list or len(groups) != 1 or type(groups[0]) is not dict or set(groups[0]) != set(expected_groups[0]) or groups[0]["params"] != expected_groups[0]["params"]:
        raise ValueError("invalid optimizer parameter groups")
    for name in ["lr", "eps", "weight_decay"]:
        if type(groups[0][name]) not in {int, float} or not math.isfinite(groups[0][name]) or groups[0][name] < 0:
            raise ValueError("invalid optimizer scalar")
    if len(groups[0]["betas"]) != 2 or any(type(b) not in {int, float} or not 0 <= b < 1 for b in groups[0]["betas"]):
        raise ValueError("invalid optimizer decay")
    restored = {}
    parameters = list(model.parameters())
    for index, entry in encoded["state"].items():
        if type(index) is not str or not index.isdigit() or str(int(index)) != index or not 0 <= int(index) < len(parameters) or type(entry) is not dict or set(entry) != {"step", "exp_avg", "exp_avg_sq"}:
            raise ValueError("invalid Adam state schema")
        try:
            item = {key: torch.tensor(value) for key, value in entry.items()}
        except (TypeError, ValueError, RuntimeError):
            raise ValueError("invalid optimizer tensor encoding") from None
        if item["step"].numel() != 1 or not 0 <= float(item["step"]) <= 1_000_000:
            raise ValueError("invalid optimizer step")
        if any(item[key].shape != parameters[int(index)].shape for key in ["exp_avg", "exp_avg_sq"]) or any(not value.isfinite().all() for value in item.values()):
            raise ValueError("invalid optimizer moment")
        restored[int(index)] = item
    optimizer.load_state_dict({"param_groups": groups, "state": restored})
    rng = payload["torch_rng"]
    if type(rng) is not list or len(rng) != len(torch.get_rng_state()) or any(type(i) is not int or not 0 <= i <= 255 for i in rng):
        raise ValueError("invalid RNG state")
    torch.set_rng_state(torch.tensor(rng, dtype=torch.uint8))
    return model, optimizer, payload["progress"]
