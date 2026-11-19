"""Evaluate the frozen public text without giving the parser any reference labels."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from research.proof_carrying_causal_reasoning_v1.external import typed_language
from research.proof_carrying_causal_reasoning_v1.external.blind_predict import predict as prior_predict

HERE = Path(__file__).resolve().parent
PINS = {"cases": "9c2b498c571a8a062cf52b3cb7e48492ba006f7dff5026df7dcc528e41a2c409",
        "parser": "5e94ee9f087d30a87339c72e8a38127f104d37eec7d5bf36d3b0ae7d9bb6988b"}


def report():
    raw = (HERE / "cases.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != PINS["cases"] or hashlib.sha256(
        Path(typed_language.__file__).read_bytes()).hexdigest() != PINS["parser"]:
        raise ValueError("the frozen exercise or parser changed")
    cases = json.loads(raw)
    result = {}
    for strategy, solve in [("phase1", lambda p: prior_predict("A", 0, p)),
                            ("phase2", typed_language.predict)]:
        statuses, groups, rows = Counter(), defaultdict(Counter), []
        for example in cases:
            output = solve(example["public"])
            gold, pred = example["reference"], output["prediction"]
            if pred is None:
                status = "required_abstention" if gold is None else "missed_answer"
            else:
                status = "correct" if pred == gold else "incorrect"
            statuses[status] += 1
            groups[example["family"]][status] += 1
            rows.append({"id": example["id"], "status": status, "prediction": pred, "reason": output["reason"]})
        result[strategy] = dict(counts=statuses, by_family=groups, rows=rows)
    return result


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, indent=2))
