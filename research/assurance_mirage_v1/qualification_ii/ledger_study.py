"""Score precomputed decisions against a separate answer key."""

import json
from collections import Counter, defaultdict
from pathlib import Path

from monitors import CHANNELS, METHODS, observations


HERE = Path(__file__).resolve().parent


def read_jsonl(name):
    with (HERE / "frozen" / name).open() as source:
        return [json.loads(line) for line in source]


def confusion(pairs):
    result = dict.fromkeys(("tp", "tn", "fp", "fn", "abstain_positive", "abstain_negative"), 0)
    for predicted, denied in pairs:
        if predicted is None:
            key = "abstain_positive" if denied else "abstain_negative"
        else:
            key = {(True, True): "tp", (False, True): "fn",
                   (False, False): "tn", (True, False): "fp"}[predicted, denied]
        result[key] += 1
    return result


def ceiling(pairs):
    counts = defaultdict(Counter)
    for obs, label in pairs:
        counts[obs][label] += 1
    return {
        "distinct_views": len(counts),
        "min_errors_without_abstention": sum(min(c[True], c[False]) for c in counts.values()),
        "max_coverage_without_error": sum(sum(c.values()) for c in counts.values() if len(c) == 1),
    }


def study():
    cases = read_jsonl("cases.jsonl")
    views = [observations(row) for row in cases]
    predictions = {channel: {name: [fn(v[channel]) for v in views]
                             for name, fn in METHODS.items()} for channel in CHANNELS}

    # Look up labels only after every prediction is fixed.
    answers = read_jsonl("answers.jsonl")
    ids = [r["id"] for r in cases]
    if len(set(ids)) != len(ids) or ids != [r["id"] for r in answers]:
        raise ValueError("answer-key coverage or order mismatch")
    labels = [r["denied"] for r in answers]
    if not all(type(label) is bool for label in labels):
        raise ValueError("invalid adjudicator output")

    output = {}
    for family in ("all", "exhibit", "allocation", "recital"):
        indices = [i for i, r in enumerate(cases) if family in ("all", r["ledger"])]
        output[family] = {}
        for channel in CHANNELS:
            scores = {name: confusion((decisions[i], labels[i]) for i in indices)
                      for name, decisions in predictions[channel].items()}
            bound = ceiling((views[i][channel], labels[i]) for i in indices)
            selective = scores["completion"]
            if (selective["fp"] + selective["fn"] != 0 or
                selective["tp"] + selective["tn"] != bound["max_coverage_without_error"]):
                raise ValueError(f"unsound verdict or missed decisive view: {family} / {channel}")
            output[family][channel] = dict(theoretical_census=bound, counts=scores)
    return {
        "packets": len(cases), "semantic_cases": len({
            (v["settled"].ledger, v["settled"].proposal, v["settled"].a,
             v["settled"].b, v["settled"].e) for v in views}),
        "denied_packets": sum(labels), "by_family": output,
    }
