"""Trusted CLadder issuer and scorer. Run preparation, prediction and scoring separately."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from ..kernel.dag import CausalDAG
from . import finite_replay as replay


def _table(value, arity):
    if arity:
        if type(value) is not list or len(value) != 2:
            raise ValueError("each binary parent needs exactly two branches")
        return _table(value[0], arity - 1) + _table(value[1], arity - 1)
    if type(value) not in (int, float, Decimal):
        raise ValueError("probability must be a numeric scalar")
    number = Decimal(str(value))
    if (
        not number.is_finite()
        or not 0 <= number <= 1
        or number.as_tuple().exponent < -75
    ):
        raise ValueError("invalid probability")
    return [str(Fraction(number))]


def _structured(meta, model):
    if (
        meta.get("query_type") != "ate"
        or meta.get("treated") is not True
        or meta.get("result") is not True
        or type(meta.get("polarity")) is not bool
        or model.get("equation_type") != "bernoulli"
    ):
        return None
    structure, params = model.get("structure"), model.get("params")
    if (
        type(structure) is not str
        or type(params) is not dict
        or len(params) > replay.MAX_NODES
    ):
        return None
    edges = []
    for edge in structure.split(","):
        ends = edge.strip().split("->")
        if len(ends) != 2 or not all(replay.NAME.fullmatch(n) for n in ends):
            return None
        edges.append(tuple(ends))
    if len(set(edges)) != len(edges):
        return None
    nodes = sorted({name for edge in edges for name in edge})
    graph = CausalDAG.from_edges(nodes, edges)
    mechanisms = {}
    for key, table in params.items():
        match = re.fullmatch(r"p\((\w+)(?: \| (\w+(?:, \w+)*))?\)", key)
        if not match:
            return None
        name, listed = match.groups()
        parents = listed.split(", ") if listed else []
        if (
            name in mechanisms
            or set(parents) != graph.parents(name)
            or len(parents) != len(set(parents))
        ):
            return None
        # CLadder uses both a scalar and a singleton vector for root CPTs.
        if not parents and type(table) is list and len(table) == 1:
            table = table[0]
        mechanisms[name] = {
            "name": name,
            "parents": parents,
            "p1": _table(table, len(parents)),
        }
    problem = {
        "assumptions": replay.ASSUMPTIONS,
        "domain": [0, 1],
        "treatment": "X",
        "outcome": "Y",
        "estimand": "ATE",
        "direction": "increase" if meta["polarity"] else "decrease",
        "nodes": [mechanisms[n] for n in graph.topological_order()],
    }
    replay.check_problem(problem)
    return problem


def project(question, model, protocol):
    if protocol == "A":
        visible = {
            "background": model.get("background"),
            "given_info": question.get("given_info"),
            "question": question.get("question"),
        }
        return visible if all(type(s) is str for s in visible.values()) else None
    if protocol != "B":
        raise ValueError("unknown protocol")
    try:
        return _structured(question["meta"], model)
    except (ValueError, KeyError, TypeError):
        return None


def _batch(questions, models, protocol):
    rows = []
    seen = set()
    for question in questions:
        qid = question["question_id"]
        if type(qid) is not int or qid in seen:
            raise ValueError("invalid or duplicate question id")
        seen.add(qid)
        model = models.get(question["meta"].get("model_id"), {})
        rows.append({"id": qid, "task": project(question, model, protocol)})
    return {"protocol": protocol, "rows": rows}


def prepare(questions, models, protocol, path):
    public = _batch(questions, models, protocol)
    with path.open("xb") as stream:
        stream.write(replay.canonical(public) + b"\n")


def _summary(observations):
    n = len(observations)
    correct = observations.count(True)
    incorrect = observations.count(False)
    answered = correct + incorrect
    if answered:
        p = correct / answered
        z = 1.959963984540054
        center = (p + z * z / (2 * answered)) / (1 + z * z / answered)
        half = (
            z
            * math.sqrt(p * (1 - p) / answered + z * z / (4 * answered**2))
            / (1 + z * z / answered)
        )
        interval = [max(0, center - half), min(1, center + half)]
    else:
        interval = None
    return {
        "total": n,
        "correct": correct,
        "incorrect": incorrect,
        "abstained": n - answered,
        "coverage": answered / n if n else None,
        "selective_accuracy": correct / answered if answered else None,
        "selective_wilson95_iid_descriptive": interval,
        "unconditional_accuracy": correct / n if n else None,
    }


def score(questions, models, public_path, predictions_path, expected_sha256):
    raw = predictions_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("frozen prediction digest mismatch")
    frozen = json.loads(raw)
    protocol = frozen["protocol"]
    public = _batch(questions, models, protocol)
    if (
        public != json.loads(public_path.read_bytes())
        or replay.digest(public) != frozen["public_sha256"]
    ):
        raise ValueError("prediction input differs from source")
    observations = []
    groups = {k: defaultdict(list) for k in ("graph_id", "query_type", "rung", "split")}
    verified = 0
    for q, item, result in zip(questions, public["rows"], frozen["rows"], strict=True):
        pred = result["prediction"]
        if item["id"] != result["id"] or pred not in (None, "yes", "no"):
            raise ValueError("prediction does not cover the ordered issued questions")
        if protocol == "B" and (pred is not None or "certificate" in result):
            cert = result.get("certificate", {})
            if (
                not replay.verify(item["id"], item["task"], replay.canonical(cert))
                or pred != cert["prediction"]
            ):
                raise ValueError("rejected structured certificate")
            verified += 1
        label = q["answer"]
        if label not in ("yes", "no"):
            raise ValueError("invalid scoring label")
        match = pred == label if pred is not None else None
        observations.append(match)
        meta = q["meta"]
        # Group all questions about one model together. The benchmark has
        # previously been exposed; this partition cannot reverse exposure.
        fold = int(hashlib.sha256(str(meta["model_id"]).encode()).hexdigest(), 16) % 10
        split = "development" if fold == 0 else ("validation" if fold == 1 else "test")
        for name, buckets in groups.items():
            group = split if name == "split" else str(meta.get(name, "unspecified"))
            buckets[group].append(match)
    return {
        "protocol": protocol,
        "model_calls": 0,
        "verified_certificates": verified,
        "public_sha256": replay.digest(public),
        "predictions_sha256": expected_sha256,
        "overall": _summary(observations),
        "groups": {
            k: {g: _summary(v) for g, v in buckets.items()}
            for k, buckets in groups.items()
        },
    }


def load(data_dir):
    questions = json.loads((data_dir / "cladder-v1-q-balanced.json").read_bytes())
    models = json.loads(
        (data_dir / "cladder-v1-meta-models.json").read_bytes(), parse_float=Decimal
    )
    by_id = {}
    for m in models:
        if m["model_id"] in by_id:
            raise ValueError("duplicate model id")
        by_id[m["model_id"]] = m
    return questions, by_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("protocol", choices=("A", "B"))
    prep.add_argument("data_dir", type=Path)
    prep.add_argument("public", type=Path)
    scorer = sub.add_parser("score")
    scorer.add_argument("data_dir", type=Path)
    scorer.add_argument("public", type=Path)
    scorer.add_argument("predictions", type=Path)
    scorer.add_argument("sha256")
    args = parser.parse_args()
    q, m = load(args.data_dir)
    if args.cmd == "prepare":
        prepare(q, m, args.protocol, args.public)
    else:
        print(
            json.dumps(
                score(q, m, args.public, args.predictions, args.sha256),
                sort_keys=True,
                indent=2,
            )
        )
