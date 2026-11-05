"""Offline incident tabletop simulator.

Explicitly refuses to perform live credential changes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object: {path}")
    return data


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def score_exercise(answer: str, keywords: list[str]) -> dict[str, Any]:
    norm = _normalize(answer)
    hit = [kw for kw in keywords if _normalize(kw) in norm]
    return {
        "matched_keywords": hit,
        "keyword_coverage": (len(hit) / len(keywords)) if keywords else 0.0,
        "passed_heuristic": len(hit) >= max(1, (len(keywords) + 1) // 2),
    }


def evaluate_after_action(
    scenario: dict[str, Any],
    responses: dict[str, Any],
) -> dict[str, Any]:
    if responses.get("live_credential_changes_performed") is True:
        raise RuntimeError(
            "tabletop simulator forbids live credential changes; "
            "set live_credential_changes_performed=false"
        )
    if scenario.get("live_credential_changes_allowed") is True:
        raise RuntimeError("scenario incorrectly allows live credential changes")

    criteria = list(scenario.get("after_action_criteria") or [])
    notes = " ".join(responses.get("after_action_notes") or [])
    notes_norm = _normalize(notes)
    checks = []
    for criterion in criteria:
        if "live credential" in criterion.lower():
            ok = responses.get("live_credential_changes_performed") is False
        else:
            tokens = [t for t in re.split(r"[^a-z0-9]+", criterion.lower()) if len(t) > 3]
            hits = sum(1 for t in tokens if t in notes_norm)
            ok = hits >= max(1, min(3, max(1, len(tokens) // 4)))
        checks.append({"criterion": criterion, "passed": ok})

    exercises = []
    answers = responses.get("answers") or {}
    for ex in scenario.get("exercises") or []:
        ans = str(answers.get(ex["id"], ""))
        exercises.append(
            {
                "id": ex["id"],
                "prompt": ex.get("prompt"),
                "answer": ans,
                **score_exercise(ans, list(ex.get("acceptable_keywords") or [])),
            }
        )

    return {
        "format": "pcs-tabletop-result-v1",
        "scenario_id": scenario.get("scenario_id"),
        "offline_only": True,
        "live_credential_changes_performed": False,
        "exercises": exercises,
        "after_action": checks,
        "passed": all(e["passed_heuristic"] for e in exercises) and all(c["passed"] for c in checks),
        "claims": [
            "Offline tabletop evaluation only.",
            "No live credential rotation or key mutation was performed.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an offline PCS incident tabletop.")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--responses", required=True)
    parser.add_argument("--out", help="Optional JSON result path")
    args = parser.parse_args(argv)
    scenario = load_json(args.scenario)
    responses = load_json(args.responses)
    if responses.get("scenario_id") and responses["scenario_id"] != scenario.get("scenario_id"):
        raise SystemExit("response scenario_id does not match scenario")
    result = evaluate_after_action(scenario, responses)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
