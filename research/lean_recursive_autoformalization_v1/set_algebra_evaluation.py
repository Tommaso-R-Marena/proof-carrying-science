"""Replay the public, exposed FormL4 Basic population on exactly the English field."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from .forml4_protocol import DATA_SHA256, REVISION, grammar_census
from .set_algebra import parse_english, check_pair

# Trusted reader for a small *formal* signature in the external reference file.
# The theorem name and proof do not define its meaning and never run as Lean.
SET_FUNCTIONS = re.compile(
    r"theorem [A-Za-z_][A-Za-z0-9_']*\s*:\s*"
    r"\(\(· ([⊓⊔∩∪]) ·\) : Set α → Set α → Set α\) = \(· ([⊓⊔∩∪]) ·\)\s*\Z")
SYMBOL = {"⊓": "inf", "⊔": "sup", "∩": "inter", "∪": "union"}


def external_reference(formal):
    head, sep, _ = formal.partition(":=")
    m = SET_FUNCTIONS.fullmatch(head) if sep else None
    if not m:
        return None
    variables = ["X", "Y"]
    args = [{"var": v} for v in variables]
    return {"variables": variables, "premises": [],
            "conclusion": {"equal": [{SYMBOL[m[1]]: args}, {SYMBOL[m[2]]: args}]}}


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def evaluate(path: Path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATA_SHA256:
        raise ValueError("different upstream FormL4 release")
    population = json.loads(raw)
    # First finish every proposal. The candidate API sees only the English string.
    proposals = [parse_english(row["nl_problem"]) for row in population]
    baseline = grammar_census(path)
    items = []
    for i, candidate in enumerate(proposals):
        if candidate is None:
            continue
        row = population[i]
        reference = external_reference(row["formal"])
        entry = {"source_index": i, "english_sha256": sha(row["nl_problem"]),
                 "formal_sha256": sha(row["formal"]), "candidate": candidate,
                 "reference": reference}
        if reference is not None:
            entry["review"] = check_pair(reference, candidate)
        else:
            # Self-comparison here is exclusively a proof/elaboration diagnostic.
            proof = check_pair(candidate, candidate)
            entry["review"] = {"correspondence": "UNSUPPORTED_FORMAL_SIGNATURE",
                               "elaborated": proof["elaborated"], "proof": "NOT_CHECKED"}
            entry["standalone_proof"] = proof
        items.append(entry)
    return {
        "benchmark": "FormL4 Basic", "revision": REVISION, "sha256": DATA_SHA256,
        "historically_exposed_development_distribution": True,
        "population": len(population), "distinct_english": len(set(r["nl_problem"] for r in population)),
        "old_parser_candidates": len(baseline["candidate_ids"]), "parsed": len(items),
        "parser_abstentions": len(proposals) - len(items),
        "elaborated": sum(item["review"]["elaborated"] for item in items),
        "external_correspondence": sum(item["review"]["correspondence"] == "EQUIVALENT" for item in items),
        "external_correspondence_and_proof": sum(item["review"]["proof"] == "KERNEL_CHECKED" for item in items),
        "formal_signature_abstentions": sum(item["reference"] is None for item in items),
        "model_requests": 0, "items": items,
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("basic_test", type=Path)
    args = cli.parse_args()
    print(json.dumps(evaluate(args.basic_test), indent=2, sort_keys=True))
