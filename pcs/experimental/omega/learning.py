"""CPU rankers over pre-action syntax and a fixed typed graph encoder.

The graph experiment trains a ranking head over two message-passing rounds;
its encoder is fixed, not an end-to-end trained GNN. No checker labels or future
feedback are features. A checkpoint can rank proposals, never accept them.
"""
from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path
import random
import re

from .logic import OPS, action_id, actions, apply_action, check, digest, exact, integer, task, walk

OPERATIONS = ("insert_not", "remove_not", "swap", "replace_and", "replace_or", "replace_implies")
FEATURE_VERSION = "omega-preaction-features/1"


def histogram(formula):
    counts = [0.0] * len(OPS)
    for _, node in walk(formula):
        counts[OPS.index(node["op"])] += 1 / 63
    return counts


def onehot(op):
    return [float(op == p) for p in OPS]


@lru_cache(maxsize=4096)
def graph_encoding(raw):
    formula = json.loads(raw)
    nodes = dict(walk(formula))
    neighbors = {p: [q for q in nodes if (q and q[:-1] == p) or (p and p[:-1] == q)] for p in nodes}
    level = {p: onehot(n["op"]) for p, n in nodes.items()}
    layers = [level]
    for _ in range(2):
        level = {p: [sum(layers[-1][q][i] for q in [p] + neighbors[p]) / (1 + len(neighbors[p]))
                     for i in range(len(OPS))] for p in nodes}
        layers.append(level)
    return {p: sum((layer[p] for layer in layers), []) for p in nodes}


def features(value, action, mode):
    task(value)
    if mode not in {"bag", "graph"}:
        raise ValueError("Unknown feature encoder")
    proposed = apply_action(value["candidate"], action, value["variables"])
    path = tuple(action["path"])
    nodes = dict(walk(value["candidate"]))
    source_nodes = dict(walk(value["source"]))
    node = nodes[path]
    src, cand, after = histogram(value["source"]), histogram(value["candidate"]), histogram(proposed)
    out = [1.0] + src + cand + [a - b for a, b in zip(after, cand)] + onehot(node["op"])
    out += [float(action["operation"] == o) for o in OPERATIONS]
    out += [len(path) / 8, len(value["variables"]) / 4, (sum(after) - sum(cand))]
    if mode == "graph":
        out += graph_encoding(json.dumps(value["candidate"], sort_keys=True))[path]
        out += graph_encoding(json.dumps(value["source"], sort_keys=True)).get(path, [0.0] * 21)
        out += onehot(nodes[path[:-1]]["op"]) if path else [0.0] * 7
        out += [float(bool(path) and path[-1] == side) for side in ("left", "right", "body")]
        out += [float(source_nodes.get(path) == node)]
    return out


def dimension(mode):
    return 91 if mode == "graph" else 38


def source_digest():
    return digest({p.name: p.read_text() for p in sorted(Path(__file__).parent.glob('*.py'))})


def validate_model(model):
    exact(model, {"format", "feature_mode", "feature_version", "dimension", "weights", "training", "authority", "model_sha256"}, "model")
    mode = model["feature_mode"]
    if (model["format"] != "pcs-omega-ranker-v1" or mode not in {"bag", "graph"} or
            model["feature_version"] != FEATURE_VERSION or type(model["dimension"]) is not int or
            model["dimension"] != dimension(mode) or model["authority"] != "NONE"):
        raise ValueError("Unsupported model contract")
    weights = model["weights"]
    if (type(weights) is not list or len(weights) != dimension(mode) or
            any(type(w) not in (int, float) or not math.isfinite(w) or abs(w) > 1000 for w in weights)):
        raise ValueError("Invalid model weights")
    exact(model["training"], {"algorithm", "seed", "epochs", "examples", "task_ids", "families", "task_digests", "source_digest", "corpus_sha256"}, "training metadata")
    meta = model["training"]
    if meta["algorithm"] not in ("weighted-logistic-SGD", "one-step-contextual-bandit-REINFORCE"):
        raise ValueError("Unknown training algorithm")
    integer(meta["seed"], 0, 2**32 - 1, "training seed")
    integer(meta["epochs"], 1, 20000, "training epochs")
    integer(meta["examples"], 1, 131072, "training examples")
    for field in ("task_ids", "families", "task_digests"):
        values = meta[field]
        if type(values) is not list or not 1 <= len(values) <= 1024 or any(type(v) is not str or not 1 <= len(v) <= 128 for v in values) or len(set(values)) != len(values):
            raise ValueError("Invalid training metadata array")
    if len(meta["task_ids"]) != len(meta["task_digests"]):
        raise ValueError("Training task bindings differ in length")
    for value in meta["task_digests"] + [meta["source_digest"], meta["corpus_sha256"]]:
        if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("Invalid training digest")
    if model["model_sha256"] != digest({k: v for k, v in model.items() if k != "model_sha256"}):
        raise ValueError("Checkpoint digest mismatch")
    return model


def checkpoint(weights, mode, training):
    result = {"format": "pcs-omega-ranker-v1", "feature_mode": mode, "feature_version": FEATURE_VERSION,
              "dimension": dimension(mode), "weights": weights, "training": training, "authority": "NONE"}
    result["model_sha256"] = digest(result)
    return validate_model(result)


def rank(value, candidates, model):
    validate_model(model)
    return sorted(candidates, key=lambda a: (-sum(x * w for x, w in zip(features(value, a, model["feature_mode"]), model["weights"])), action_id(a)))


def train(corpus, mode="graph", *, seed=20261009, epochs=24):
    from .corpus import validate_corpus
    corpus = validate_corpus(corpus)
    integer(epochs, 1, 100, "epochs")
    integer(seed, 0, 2**32 - 1, "seed")
    records = [r for r in corpus["records"] if r["partition"] == "train"]
    if not records:
        raise ValueError("No authorized training records")
    examples = []
    for record in records:
        value = record["task"]
        # Recompute labels from the immutable original task, never import labels.
        for action in actions(value["candidate"], value["variables"]):
            proposal = {**value, "candidate": apply_action(value["candidate"], action, value["variables"])}
            examples.append((features(value, action, mode), float(check(proposal)["equivalent"])))
    weights = [0.0] * dimension(mode)
    rng = random.Random(seed)
    for _ in range(epochs):
        rng.shuffle(examples)
        for xs, label in examples:
            z = max(-30.0, min(30.0, sum(x * w for x, w in zip(xs, weights))))
            error = label - 1 / (1 + math.exp(-z))
            # Positive-label weighting corrects the deliberately sparse action corpus.
            rate = 0.03 * (8 if label else 1)
            weights = [w + rate * (error * x - 0.0001 * w) for w, x in zip(weights, xs)]
    metadata = {"algorithm": "weighted-logistic-SGD", "seed": seed, "epochs": epochs,
                "examples": len(examples), "task_ids": [r["id"] for r in records],
                "families": sorted({r["family"] for r in records}), "task_digests": [r["task_sha256"] for r in records],
                "source_digest": source_digest(), "corpus_sha256": digest(records)}
    return checkpoint(weights, mode, metadata)
