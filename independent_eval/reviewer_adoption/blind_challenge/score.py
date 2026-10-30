"""Score blind-challenge response sheets against sealed ground truth.

Does not invent human results. Synthetic fixture responses must set
`synthetic: true` and `human_study: false`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_JUDGMENTS = {
    "accept_as_valid",
    "reject_as_invalid",
    "accept_computational_only",
    "abstain",
}


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object in {path}")
    return data


def score_responses(
    ground_truth: dict[str, Any],
    responses_doc: dict[str, Any],
) -> dict[str, Any]:
    labels: dict[str, str] = dict(ground_truth.get("labels") or {})
    correct_map: dict[str, list[str]] = {
        k: list(v) for k, v in (ground_truth.get("correct_responses") or {}).items()
    }
    responses = list(responses_doc.get("responses") or [])
    if not responses:
        raise ValueError("responses document has no responses")

    if responses_doc.get("human_study") is True and not responses_doc.get("attested_human_run"):
        raise ValueError(
            "refusing to score a document marked human_study=true without "
            "attested_human_run; this tool does not invent human results"
        )

    per_case: list[dict[str, Any]] = []
    n_correct = 0
    n_scored = 0
    for row in responses:
        raw_id = row.get("raw_case_id")
        judgment = row.get("judgment")
        if raw_id not in labels:
            raise KeyError(f"unknown raw_case_id in responses: {raw_id}")
        if judgment not in ALLOWED_JUDGMENTS:
            raise ValueError(f"invalid judgment '{judgment}' for {raw_id}")
        truth = labels[raw_id]
        accepted = set(correct_map.get(truth) or [])
        is_correct = judgment in accepted
        n_scored += 1
        if is_correct:
            n_correct += 1
        per_case.append(
            {
                "opaque_id": row.get("opaque_id"),
                "raw_case_id": raw_id,
                "ground_truth_label": truth,
                "judgment": judgment,
                "correct": is_correct,
            }
        )

    accuracy = (n_correct / n_scored) if n_scored else 0.0
    return {
        "format": "pcs-blind-challenge-score-v1",
        "synthetic": bool(responses_doc.get("synthetic")),
        "human_study": bool(responses_doc.get("human_study")),
        "n_scored": n_scored,
        "n_correct": n_correct,
        "accuracy": accuracy,
        "per_case": per_case,
        "claims": [
            "Automated scoring of supplied response sheets only.",
            "No invented human results.",
            "No claim of inter-rater reliability or external validation.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score blind challenge responses.")
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--responses", required=True)
    parser.add_argument("--out", help="Optional JSON output path")
    args = parser.parse_args(argv)
    result = score_responses(load_json(args.ground_truth), load_json(args.responses))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
