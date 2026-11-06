"""Train a small scratch scientific dual encoder and evaluate lexical controls.

Usage: python research/scientific_understanding_v2/learning/train_retrieval.py
This program reads only this authored benchmark, never scientific project data.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from retrieval import feature_ids, rank, tokenize, _validate_checkpoint
from synthetic_benchmark import build_benchmark, dataset_sha256, SPLIT_FAMILIES

SEED = 1729
WIDTH = 24
BUCKETS = 256
EPOCHS = 40


def write_json(path, data):
    raw = (json.dumps(data, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def train(train_data, vocabulary, shuffled=False):
    import torch
    torch.set_num_threads(1)
    torch.manual_seed(SEED)
    class Encoder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(len(vocabulary)+1+BUCKETS, WIDTH)
            self.hidden = torch.nn.Linear(WIDTH, WIDTH)
            self.output = torch.nn.Linear(WIDTH, WIDTH)
        def forward(self, tokens, mask):
            pooled = (self.embedding(tokens)*mask.unsqueeze(-1)).sum(1)/mask.sum(1, keepdim=True)
            return torch.nn.functional.normalize(self.output(torch.tanh(self.hidden(pooled))), dim=1)
    def batch(texts):
        ids = [feature_ids(t, vocabulary, BUCKETS) for t in texts]
        size = max(map(len, ids))
        tokens = torch.zeros((len(ids), size), dtype=torch.long)
        mask = torch.zeros((len(ids), size))
        for i, row in enumerate(ids):
            tokens[i, :len(row)] = torch.tensor(row)
            mask[i, :len(row)] = 1
        return tokens, mask
    model = Encoder()
    queries = train_data["queries"]
    documents = train_data["candidates"]
    q = batch([x["text"] for x in queries])
    d = batch([x["text"] for x in documents])
    positions = {x["id"]: i for i, x in enumerate(documents)}
    labels = [positions[x["positive_id"]] for x in queries]
    if shuffled:
        random.Random(SEED+1).shuffle(labels)
    targets = torch.tensor(labels)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.018, weight_decay=0.0001)
    losses = []
    start = time.perf_counter()
    for _ in range(EPOCHS):
        optimizer.zero_grad()
        scores = model(*q) @ model(*d).T / 0.09
        loss = torch.nn.functional.cross_entropy(scores, targets)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    weights = {"embedding": model.embedding.weight.detach().tolist(),
               "hidden_weight": model.hidden.weight.detach().tolist(),
               "hidden_bias": model.hidden.bias.detach().tolist(),
               "output_weight": model.output.weight.detach().tolist(),
               "output_bias": model.output.bias.detach().tolist()}
    artifact = {"schema": "scientific-source-encoder-v1", "width": WIDTH,
                "character_buckets": BUCKETS, "vocabulary": vocabulary, "weights": weights,
                "seed": SEED, "training_label_shuffle": shuffled,
                "role": "source relevance only; never semantic correctness or checker authority"}
    _validate_checkpoint(artifact)
    return artifact, {"seconds": time.perf_counter()-start, "epochs": EPOCHS,
                      "initial_loss": losses[0], "final_loss": losses[-1],
                      "parameters": sum(p.numel() for p in model.parameters())}


def evaluate(data, mode, checkpoint=None):
    examples = []
    for q in data["queries"]:
        scores = rank(q["text"], data["candidates"], mode, checkpoint)
        ordering = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        positive = next(i for i, d in enumerate(data["candidates"]) if d["id"] == q["positive_id"])
        position = ordering.index(positive)+1
        examples.append({"query_id": q["id"], "positive_id": q["positive_id"],
                         "rank": position, "top_id": data["candidates"][ordering[0]]["id"],
                         "candidate_count": len(scores)})
    return {"top1": sum(e["rank"] == 1 for e in examples)/len(examples),
            "mrr": sum(1/e["rank"] for e in examples)/len(examples),
            "n": len(examples), "examples": examples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=HERE/"artifacts")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    data = build_benchmark()
    vocabulary = {word: i+1 for i, word in enumerate(sorted({t for part in ("queries", "candidates")
                    for item in data["train"][part] for t in tokenize(item["text"])}))}
    report = {"schema": "scientific-source-retrieval-evaluation-v1", "seed": SEED,
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "dataset_sha256": dataset_sha256(data), "split_families": SPLIT_FAMILIES,
              "data_origin": "Authored synthetic query-source pairs only; scientificprojects evaluation-only",
              "selection": "Architecture, 40 epochs and optimizer fixed before any test evaluation; no test selection",
              "models": {}, "metrics": {}}
    paths = {}
    for name, shuffled in (("neural", False), ("randomized_labels", True)):
        artifact, stats = train(data["train"], vocabulary, shuffled)
        path = args.output_dir/("scientific_encoder.json" if not shuffled else "randomized_encoder.json")
        sha = write_json(path, artifact)
        path.with_suffix(path.suffix+".sha256").write_text(sha+"\n")
        paths[name] = path
        report["models"][name] = {**stats, "checkpoint": path.name, "sha256": sha,
                                   "json_bytes": path.stat().st_size, "vocabulary_size": len(vocabulary)}
    # The test set is touched only after both fixed-training checkpoints are complete.
    for split in ("train", "validation", "test"):
        report["metrics"][split] = {}
        for name in ("bm25", "tfidf", "neural", "randomized_labels"):
            report["metrics"][split][name] = evaluate(data[split], "neural" if name in paths else name,
                                                       paths.get(name))
    report["runtime_seconds"] = time.perf_counter()-started
    neural = report["metrics"]["test"]["neural"]
    best = max(report["metrics"]["test"][name]["mrr"] for name in ("bm25", "tfidf"))
    report["finding"] = ("Neural test MRR exceeds both lexical baselines on this small authored benchmark."
                         if neural["mrr"] > best else
                         "Negative finding: neural test MRR does not exceed the strongest lexical baseline.")
    report["limitations"] = ["Toy synthetic family split does not establish transfer to publication sources.",
        "One predeclared seed and architecture; no statistical significance claim.",
        "Source relevance scores do not establish entailment, truth, or proof authority.",
        "This is contrastive retrieval training, not JEPA; native P1/P2 models and weights were not reused."]
    write_json(args.output_dir/"evaluation.json", report)
    write_json(args.output_dir/"authored_benchmark.json", data)
    print(json.dumps({"finding": report["finding"], "runtime_seconds": report["runtime_seconds"],
                      "test": {k: {m: v[m] for m in ("top1", "mrr", "n")} for k, v in report["metrics"]["test"].items()}}, indent=2))


if __name__ == "__main__":
    main()
