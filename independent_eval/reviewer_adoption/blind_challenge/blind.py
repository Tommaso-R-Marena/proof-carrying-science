"""Create blinded reviewer packets from synthetic cases.

Strips ground-truth labels and expected_* fields. Does not invent human results.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any


REDACT_KEYS = {
    "ground_truth_label",
    "ground_truth",
    "expected_judgment",
    "expected_label",
    "answer",
    "answer_key",
}


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if key in REDACT_KEYS or key.startswith("expected_"):
                continue
            out[key] = _redact(value)
        return out
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


def load_cases(cases_dir: str | Path) -> list[dict[str, Any]]:
    """Load labeled synthetic cases for the blinded scoring suite.

    Only top-level ``*.json`` files that include ``ground_truth_label`` are
    used. Neighboring unlabeled practice materials (if present) are ignored so
    this scorer does not invent labels. Duplicate ``case_id`` values keep the
    first path in sorted order.
    """
    root = Path(cases_dir)
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(root.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "case_id" not in data:
            # Skip non-case JSON rather than inventing structure.
            continue
        if "ground_truth_label" not in data:
            continue
        cid = str(data["case_id"])
        if cid in seen:
            continue
        seen.add(cid)
        cases.append(data)
    if not cases:
        raise FileNotFoundError(
            f"no labeled case JSON files (with ground_truth_label) in {root}"
        )
    return cases


def build_blind_packet(
    cases: list[dict[str, Any]],
    *,
    seed: int = 0,
) -> dict[str, Any]:
    rng = random.Random(seed)
    indexed = list(enumerate(cases))
    rng.shuffle(indexed)
    blinded_cases = []
    mapping = []
    for opaque_i, (orig_i, case) in enumerate(indexed, start=1):
        opaque_id = f"CASE-{opaque_i:02d}"
        redacted = _redact(case)
        body = {k: v for k, v in redacted.items() if k != "case_id"}
        body["opaque_id"] = opaque_id
        blinded_cases.append(body)
        mapping.append(
            {
                "opaque_id": opaque_id,
                "raw_case_id": case["case_id"],
                "source_index": orig_i,
                "ground_truth_label": case.get("ground_truth_label"),
            }
        )
    return {
        "format": "pcs-blind-challenge-packet-v1",
        "seed": seed,
        "blinding": {
            "labels_removed": sorted(REDACT_KEYS),
            "human_results_included": False,
            "note": "Packet contains synthetic cases only; no human study outcomes.",
        },
        "cases": blinded_cases,
        "facilitator_map": mapping,
    }


def write_packet(packet: dict[str, Any], out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    reviewer_packet = {
        "format": packet["format"],
        "seed": packet["seed"],
        "blinding": packet["blinding"],
        "cases": packet["cases"],
    }
    (out / "reviewer_packet.json").write_text(
        json.dumps(reviewer_packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "facilitator_map.json").write_text(
        json.dumps(
            {
                "format": "pcs-blind-challenge-facilitator-map-v1",
                "seed": packet["seed"],
                "mapping": packet["facilitator_map"],
                "warning": "Contains ground-truth labels. Do not give to blinded reviewers.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return out / "reviewer_packet.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a blinded reviewer challenge packet.")
    parser.add_argument("--cases-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    cases = load_cases(args.cases_dir)
    packet = build_blind_packet(cases, seed=args.seed)
    path = write_packet(packet, args.out)
    print(f"wrote {path}")
    print(f"wrote {Path(args.out) / 'facilitator_map.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
