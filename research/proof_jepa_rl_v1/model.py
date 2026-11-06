"""Trainable action-conditioned proof-state JEPA. All outputs are proposals.

The graph topology and bounded symbolic action features reuse PCS's untrusted
research representations. Embeddings, message passing, pooling, predictor and
heads are optimized end to end. The target encoder is an EMA, never an optimizer
parameter. No checkpoint or loss can produce a Lean acceptance receipt.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re

import torch
from torch import nn
from torch.nn import functional as F

from pcs.experimental.prover.environment import reference_expression, render_action
from pcs.experimental.prover.model import features, token

KINDS = ("intro", "constructor", "assumption", "rfl", "left", "right",
         "contradiction", "simp", "exact", "apply", "cases", "rewrite", "lemma",
         "witness", "induct_nat", "induct_list", "normalize", "rewrite_back")
FORMAT = "pcs-proof-jepa-experiment-v1"


def ordered_graph(state):
    """Bounded, ordered Lean-Expr graph with alpha-normalized local identities.

    Child roles distinguish function/argument and binder-type/body. Local ids are
    mapped to context positions, not erased, so repeated-variable structure is
    preserved without training on elaborator allocation names. Pretty-printed
    hypothesis types and binder display names are deliberately not tokenized.
    The 257-bucket vocabulary still has hash collisions: this is a model input,
    never a formal canonicalization or equivalence decision.
    """
    nodes, edges, roles = [token("state")], [], [0]
    def append(value, parent, role):
        if len(nodes) >= 4096:
            raise ValueError("state graph exceeds bound")
        index = len(nodes)
        nodes.append(token(value)); roles.append(role)
        edges.extend(((parent, index), (index, parent)))
        return index
    def visit(expr, parent, role, identities, depth=0):
        if depth > 256:
            raise ValueError("state expression exceeds depth bound")
        kind, value = expr["kind"], expr["value"]
        if kind == "local":
            value = str(identities.get(value, "unresolved"))
        elif kind in {"goal", "forall", "lambda", "let"}:
            value = ""
        index = append(kind + ":" + value, parent, role)
        for child_index, child in enumerate(expr["children"]):
            visit(child, index, 4 + min(child_index, 3), identities, depth + 1)
    for goal_index, goal in enumerate(state["goals"]):
        identities = {local.get("id", local["name"]): index for index, local in enumerate(goal["locals"])}
        if "_local_ids" in state:
            identities = {value: index for index, value in enumerate(state["_local_ids"])}
        target = append("target", 0, 8 + min(goal_index, 7))
        visit(goal["expression"], target, 3, identities)
        for local in goal["locals"]:
            hypothesis = append("hypothesis", target, 2)
            visit(local["expression"], hypothesis, 3, identities)
    return nodes, edges, roles


class GraphEncoder(nn.Module):
    """Two trainable bidirectional message-passing rounds over Lean Expr trees."""
    def __init__(self, width):
        super().__init__()
        self.tokens = nn.Embedding(257, width)
        self.roles = nn.Embedding(16, width)
        self.message = nn.ModuleList(nn.Linear(width, width) for _ in range(2))
        self.update = nn.ModuleList(nn.Linear(2 * width, width) for _ in range(2))
        self.norm = nn.ModuleList(nn.LayerNorm(width) for _ in range(2))
        self.pool = nn.Linear(3 * width, width)

    def forward(self, state):
        nodes, edges, roles = ordered_graph(state)
        device = self.tokens.weight.device
        h = self.tokens(torch.tensor(nodes, dtype=torch.long, device=device))
        h = h + self.roles(torch.tensor(roles, dtype=torch.long, device=device))
        if edges:
            src, dst = torch.tensor(edges, dtype=torch.long, device=device).T
            counts = h.new_zeros(len(nodes)).index_add(0, dst, h.new_ones(len(dst)))
        for message, update, norm in zip(self.message, self.update, self.norm):
            aggregate = torch.zeros_like(h)
            if edges:
                aggregate.index_add_(0, dst, message(h[src]))
                aggregate = aggregate / counts.clamp_min(1).unsqueeze(1)
            h = norm(h + torch.tanh(update(torch.cat((h, aggregate), dim=1))))
        return torch.tanh(self.pool(torch.cat((h[0], h.mean(0), h.max(0).values))))


class ProofJEPA(nn.Module):
    """CPU-compatible graph JEPA with learned retrieval and actor/critic heads.

    ``predictive_loss`` consumes externally collected checker outcomes. It does
    not certify the supplied records. Training provenance must independently bind
    them to receipts; imported self-labelled records must not be trusted.
    """
    def __init__(self, width=24):
        super().__init__()
        if type(width) is not int or not 8 <= width <= 64:
            raise ValueError("width must be an integer between 8 and 64")
        self.width = width
        self.online = GraphEncoder(width)
        self.target = copy.deepcopy(self.online)
        self.target.requires_grad_(False)
        self.action_kind = nn.Embedding(len(KINDS), width)
        self.action_argument = nn.Embedding(257, width)
        self.predictor = nn.Sequential(nn.Linear(3 * width + 12, 2 * width), nn.GELU(), nn.Linear(2 * width, width))
        self.policy = nn.Sequential(nn.Linear(4 * width + 12, width), nn.Tanh(), nn.Linear(width, 1))
        self.value = nn.Sequential(nn.Linear(width, width), nn.Tanh(), nn.Linear(width, 1))
        self.invalid = nn.Sequential(nn.Linear(3 * width + 12, width), nn.Tanh(), nn.Linear(width, 1))
        self.cost = nn.Sequential(nn.Linear(3 * width + 12, width), nn.Tanh(), nn.Linear(width, 1))
        self.retrieval = nn.Linear(width, width, bias=False)
        self.last_predictive_metrics = {}

    def encode(self, state):
        return self.online(state)

    @torch.no_grad()
    def encode_target(self, state):
        return self.target(state)

    def _action(self, state, action):
        render_action(action)
        if action["kind"] not in KINDS:
            raise ValueError("unsupported JEPA action")
        device = self.action_kind.weight.device
        a = self.action_kind.weight[KINDS.index(action["kind"])] + self.action_argument.weight[token(str(action["argument"]))]
        expression = None
        if state["goals"] and action["kind"] in {"exact", "apply", "rewrite", "rewrite_back"}:
            expression = reference_expression(state, str(action["argument"]))
        if expression is None:
            premise = a.new_zeros(self.width)
        else:
            premise = self.encode({"goals": [{"expression": expression, "target": "", "locals": []}],
                                   "_local_ids": [local.get("id", local["name"]) for local in state["goals"][0]["locals"]]})
        f = torch.tensor(features(state, action), dtype=a.dtype, device=device)
        return a, premise, f

    def predict(self, latent, state, action):
        a, premise, f = self._action(state, action)
        return self.predictor(torch.cat((latent, a, premise, f)))

    def forward(self, state, options):
        h = self.encode(state)
        scores, invalids = [], []
        for action in options:
            a, premise, f = self._action(state, action)
            context = torch.cat((h, a, premise, f))
            predicted = self.predictor(context)
            invalid = self.invalid(context).sigmoid().squeeze()
            cost = F.softplus(self.cost(context)).squeeze()
            retrieval = (self.retrieval(h) * premise).sum() / math.sqrt(self.width)
            score = self.policy(torch.cat((h, a, premise, predicted, f))).squeeze()
            score = score + .1 * retrieval + .2 * self.value(predicted).sigmoid().squeeze() - .1 * invalid - .01 * cost
            scores.append(score)
            invalids.append(invalid)
        return (torch.stack(scores) if scores else h.new_empty(0),
                self.value(h).squeeze(),
                torch.stack(invalids) if invalids else h.new_empty(0))

    def rank(self, state, options):
        self.eval()
        with torch.no_grad():
            result = self(state, options)[0]
            if not torch.isfinite(result).all():
                raise ValueError("nonfinite proposal scores")
            return result.cpu().tolist()

    @torch.no_grad()
    def update_target(self, momentum=.99):
        if type(momentum) not in (float, int) or not math.isfinite(momentum) or not 0 <= momentum < 1:
            raise ValueError("invalid EMA momentum")
        for target, online in zip(self.target.parameters(), self.online.parameters()):
            target.mul_(momentum).add_(online, alpha=1 - momentum)

    def predictive_loss(self, transitions, proof_guided=False):
        """Predict actual successor embeddings; never reconstruct input tokens.

        Invalid records supervise rejection only. Optional ``future`` records
        unroll the latent predictor over observed multi-step transitions. Optional
        ``equivalent_state`` supervision is used only in proof-guided mode and
        must carry an external 64-hex ``equivalence_receipt_sha256`` binding.
        This syntactic binding is provenance plumbing, not receipt verification.
        """
        if not transitions:
            raise ValueError("empty transition batch")
        latents, predictions, targets, rejection_losses, value_losses, costs = [], [], [], [], [], []
        multistep, equivalences = [], []
        for record in transitions:
            state, action = record["state"], record["action"]
            if type(record["valid"]) is not bool:
                raise ValueError("valid label must be an actual checker boolean")
            h = self.encode(state)
            latents.append(h)
            a, premise, f = self._action(state, action)
            context = torch.cat((h, a, premise, f))
            label = h.new_tensor(float(not record["valid"]))
            rejection_losses.append(F.binary_cross_entropy_with_logits(self.invalid(context).squeeze(), label))
            checker_cost = record.get("checker_cost", 1.)
            if type(checker_cost) not in (int, float) or not math.isfinite(checker_cost) or not 0 <= checker_cost <= 1000:
                raise ValueError("invalid observed checker cost")
            costs.append((F.softplus(self.cost(context)).squeeze() - math.log1p(checker_cost)).square())
            remaining = record.get("remaining")
            if remaining is not None:
                if type(remaining) is not int or remaining < 0:
                    raise ValueError("invalid remaining horizon")
                value_losses.append((self.value(h).sigmoid().squeeze() - 1 / (1 + remaining)).square())
            if not record["valid"]:
                continue
            prediction = self.predictor(context)
            target = self.encode_target(record["next_state"])
            predictions.append(prediction)
            targets.append(target)
            previous_state = record["next_state"]
            latent = prediction
            for step in (record.get("future", [])[:3] if proof_guided else []):
                latent = self.predict(latent, previous_state, step["action"])
                multistep.append(F.mse_loss(latent, self.encode_target(step["next_state"])))
                previous_state = step["next_state"]
            if proof_guided and "equivalent_state" in record:
                receipt = record.get("equivalence_receipt_sha256", "")
                if type(receipt) is not str or re.fullmatch(r"[0-9a-f]{64}", receipt) is None:
                    raise ValueError("equivalence supervision requires receipt binding")
                equivalent = self.encode(record["equivalent_state"])
                equivalences.append(F.mse_loss(self.encode(record["next_state"]), equivalent))
        zero = latents[0].sum() * 0
        predictive = F.mse_loss(torch.stack(predictions), torch.stack(targets)) if predictions else zero
        online_batch = torch.stack(latents)
        # VICReg-style variance floor and off-diagonal covariance penalties.
        # A singleton has no empirical variance; no spurious variance is claimed.
        if len(latents) > 1:
            variance = F.relu(.2 - torch.sqrt(online_batch.var(0, unbiased=False) + 1e-4)).mean()
            centered = online_batch - online_batch.mean(0)
            covariance = centered.T @ centered / (len(latents) - 1)
            offdiagonal = covariance - torch.diag(torch.diagonal(covariance))
            covariance_loss = offdiagonal.square().sum() / self.width
            measured_std = online_batch.std(0, unbiased=False).mean()
        else:
            variance = covariance_loss = measured_std = zero
        mean = lambda values: torch.stack(values).mean() if values else zero
        multi = mean(multistep)
        equivalence = mean(equivalences)
        rejection, horizon, cost = mean(rejection_losses), mean(value_losses), mean(costs)
        loss = predictive + .5 * variance + .02 * covariance_loss
        if proof_guided:
            loss = loss + .5 * multi + .1 * rejection + .1 * horizon + .01 * cost + .2 * equivalence
        self.last_predictive_metrics = {k: float(v.detach()) for k, v in {
            "loss": loss, "successor_mse": predictive, "multistep_mse": multi,
            "variance_penalty": variance, "covariance_penalty": covariance_loss,
            "embedding_std": measured_std, "invalid_bce": rejection,
            "horizon_mse": horizon, "cost_mse": cost, "equivalence_mse": equivalence}.items()}
        self.last_predictive_metrics.update({"valid_predictions": len(predictions), "multistep_targets": len(multistep), "equivalence_pairs": len(equivalences)})
        return loss

    def save(self, path, metadata):
        payload = {"format": FORMAT, "width": self.width, "authority": "NONE", "metadata": metadata,
                   "weights": {k: v.detach().cpu().tolist() for k, v in self.state_dict().items()}}
        raw = (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        if len(raw) > 8_000_000:
            raise ValueError("checkpoint exceeds byte bound")
        Path(path).write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def load(cls, path, expected_sha):
        if type(expected_sha) is not str or re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None:
            raise ValueError("expected checkpoint digest is required")
        with Path(path).open("rb") as stream:
            raw = stream.read(8_000_001)
        if len(raw) > 8_000_000 or hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError("checkpoint integrity failure")
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate checkpoint key")
                result[key] = value
            return result
        def reject_constant(value):
            raise ValueError("nonfinite checkpoint constant")
        payload = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)
        if (type(payload) is not dict or set(payload) != {"format", "width", "authority", "metadata", "weights"}
                or payload["format"] != FORMAT or payload["authority"] != "NONE" or type(payload["metadata"]) is not dict):
            raise ValueError("unsupported experimental checkpoint")
        model = cls(payload["width"])
        expected = model.state_dict()
        if type(payload["weights"]) is not dict or set(payload["weights"]) != set(expected):
            raise ValueError("checkpoint parameter keys differ")
        converted = {}
        def valid_numbers(value):
            return all(valid_numbers(v) for v in value) if type(value) is list else type(value) in (int, float) and math.isfinite(value)
        for key, value in payload["weights"].items():
            if not valid_numbers(value):
                raise ValueError("checkpoint parameter must contain finite numbers")
            try:
                tensor = torch.tensor(value, dtype=expected[key].dtype)
            except (TypeError, ValueError, RuntimeError) as ex:
                raise ValueError("invalid parameter tensor") from ex
            if tensor.shape != expected[key].shape or not torch.isfinite(tensor).all():
                raise ValueError("checkpoint shape or finiteness mismatch")
            converted[key] = tensor
        model.load_state_dict(converted, strict=True)
        return model
