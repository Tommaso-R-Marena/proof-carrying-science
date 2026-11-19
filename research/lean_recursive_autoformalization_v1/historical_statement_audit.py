"""Recount historical rows and replay two editorial semantic rejections on exact bytes."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from .forml4_protocol import digest, wilson

ROOT = Path(__file__).resolve().parent / "results" / "sota_competitive"
# These judgments are specific to a source and a candidate. Any change needs review.
REVIEWS = {
    ("50fec2f7bbe8917c2001b56ede6a650c0254263ecaf627d6fb9850baa3c4d635",
     "883e6fc51fd58a8a4d4aff8df77fced992abc9e3ba988d43cb10f58b3f62fc97"):
        "The source asks about Borel sigma-algebras. The candidate asserts B ⊆ closure A whenever A ⊆ B. "
        "Take A empty and B a singleton in a nonempty discrete space.",
    ("d120bea9749dc843f7f10484021dd1da94aac0de369d51eed90ff8be400bff4c",
     "3a9bb607f512d142c78860bbb9647be6822c7ba967976415844acc226c7eee6e"):
        "The source asks about volume. Infinite (Set.univ : Set ℝ) concerns cardinality. "
        "A countably infinite set can have zero Lebesgue measure.",
}


def review(english: str, code: str) -> dict:
    key = digest(english), digest(code)
    return {"english_sha256": key[0], "candidate_sha256": key[1],
            "status": "SEMANTICALLY_REJECTED" if key in REVIEWS else "UNKNOWN",
            "basis": REVIEWS.get(key), "method": "retrospective editorial adjudication"}


def replay() -> dict:
    primary = ROOT / "sota_competitive_summary.json"
    secondary = ROOT / "forml4_expand_40_79.json"
    rows = json.loads(primary.read_bytes())["forml4_basic"]["rows"] + json.loads(secondary.read_bytes())["rows"]
    if [row["id"] for row in rows] != [f"forml4_basic_{i}" for i in range(80)]:
        raise ValueError("historical slice changed")
    verdicts = []
    for row in rows:
        for attempt in row["attempts"]:
            if attempt.get("compiled"):
                item = review(row["english"], attempt.get("code") or "")
                if item["status"] != "UNKNOWN":
                    verdicts.append(dict(item, id=row["id"]))
    successes = sum(row["compiled"] for row in rows)
    actual = hashlib.sha256(primary.read_bytes()).hexdigest()
    expected = json.loads((ROOT / "SHA256.json").read_text())[primary.name]
    return {
        "n": len(rows), "attempts_recorded": sum(len(row["attempts"]) for row in rows),
        "first_candidate_compile_count": sum(bool(row["attempts"][0].get("compiled")) for row in rows),
        "any_attempt_compile_count": successes,
        "wilson95_descriptive_only": wilson(successes, len(rows)),
        "winners": dict(Counter(row["winner"] or "none" for row in rows)),
        "semantically_rejected": verdicts, "unassessed_successes": successes - len(verdicts),
        "proof_checks_in_historical_metric": 0, "fresh_model_calls": 0,
        "historical_summary_sha256": actual, "frozen_manifest_sha256_for_summary": expected,
        "manifest_matches": actual == expected,
        "expansion_file_sha256": hashlib.sha256(secondary.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2, sort_keys=True))
