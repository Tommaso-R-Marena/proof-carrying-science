#!/usr/bin/env python3
"""Private PCS ProofLab source-proof corpus extractor.

Extracts first-party Lean source proofs, not kernel-elaborated proof states.
The true validation authority is a fresh Lean build of the exact source revision.
Never publish proof bodies to the public website from this extractor.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from scripts.validate_prooflab_benchmark import ROOT, MODULES, validate, CORE_REVISION

COMMAND = re.compile(
    r"^(?:theorem|lemma|def|private[ \t]+(?:theorem|lemma|def)|"
    r"structure|instance|namespace|section|end)[ \t]*\b", re.M
)
FORBIDDEN = re.compile(r"\b(sorry|admit)\b")

def proof_text_from_source(source: str, name: str) -> str:
    start = re.search(
        r"^[ \t]*(?:private[ \t]+)?theorem[ \t]+" +
        re.escape(name) + r"(?![A-Za-z0-9_'])", source, re.M
    )
    if start is None:
        raise ValueError(f"Missing theorem {name}")
    point = source.find(":=", start.start())
    if point < 0 or point - start.start() > 1700:
        raise ValueError("Theorem header is missing its definition")
    suffix = source[point + 2:]
    stop = COMMAND.search(suffix)
    text = suffix[:stop.start()] if stop else suffix
    text = text.rstrip()
    if not text:
        raise ValueError(f"Empty proof text for {name}")
    # Fail rather than silently assigning training labels to an admitted proof.
    if FORBIDDEN.search(text):
        raise ValueError(f"Unverified placeholder or admission in {name}")
    return text

def extract(split: str = "all"):
    validate()
    if split not in ("all", "train", "evaluation", "challenge"):
        raise ValueError("Unknown split")
    records = []
    for module, (group_split, count) in MODULES.items():
        if split != "all" and group_split != split:
            continue
        manifest = json.loads((ROOT / "benchmarks/prooflab" / (module + ".json")).read_text())
        source = (ROOT / manifest["records"][0]["source"]["path"]).read_text()
        for item in manifest["records"]:
            proof = proof_text_from_source(source, item["name"])
            nonempty = [line.strip() for line in proof.splitlines()
                        if line.strip() and not line.strip().startswith("--")]
            records.append({
                "id": item["id"],
                "module": module,
                "split": group_split,
                "source_revision": CORE_REVISION,
                "source_line": item["source"]["line"],
                "source_blob_sha": item["source"]["blob_sha"],
                "lean_statement": item["statement"],
                "raw_source_proof": proof,
                "proof_sha256": hashlib.sha256(proof.encode()).hexdigest(),
                "observed_source_lines": len(nonempty),
                "source_identifier_mentions": item["syntactic_reference_mentions"],
                "kernel_verified_in_this_export": False,
                "ground_truth_type": "first_party_lean_source_text_not_elaborated_proof_state"
            })
    return {
        "format": "pcs-prooflab-private-source-proof-corpus-v1",
        "source_revision": CORE_REVISION,
        "split": split,
        "visibility": "PRIVATE_FIRST_PARTY_SOURCE_ONLY",
        "required_further_verification": [
            "Fresh matching Lean 4 and Mathlib kernel build of the exact commit",
            "Proof-state extraction in the Lean elaborator before use as next-tactic labels",
            "Independent project and tactic held-out evaluation",
            "No sharing with unauthorised external training partners"
        ],
        "records": records
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["all", "train", "evaluation", "challenge"],
                        default="train")
    parser.add_argument("--out", type=Path, required=True,
                        help="Local private output location; never a public site directory")
    args = parser.parse_args()
    destination = args.out.resolve()
    if destination.is_relative_to(ROOT / "site") or destination.is_relative_to(ROOT / "public"):
        raise ValueError("Refusing to put private source proofs into a public site path")
    data = extract(args.split)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"records": len(data["records"]), "split": data["split"],
                      "path": str(destination), "fresh_lean_proofs": 0}))

if __name__ == "__main__":
    main()
