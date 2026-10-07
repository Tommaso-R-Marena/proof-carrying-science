#!/usr/bin/env python3
"""Validate source-attested Lean declaration snapshots for PCS ProofLab.

This does not run a Lean kernel or certify any educational game proof plan.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "Units": ("train", 13),
    "Binding": ("train", 8),
    "EnvFacts": ("train", 6),
    "Checkers": ("train", 5),
    "PKPDCheck": ("evaluation", 8),
    "Workflow": ("evaluation", 7),
    "IndexProofs": ("challenge", 6),
    "PackageProofs": ("challenge", 8),
}
CORE_REVISION = "cff0b67595abd4862ab0c156b157f262b169eca5"

def blob_sha256_or_git_sha1(data: bytes) -> str:
    """Git SHA-1 of the exact source blob, not a cryptographic security proof."""
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def source_signature(text: str, name: str):
    m = re.search(r"^[ \t]*(?:private[ \t]+)?theorem[ \t]+" +
                  re.escape(name) + r"(?![A-Za-z0-9_'])", text, re.M)
    if m is None:
        raise ValueError(f"Selected theorem {name} disappeared from source")
    cut = text.find(":=", m.start())
    if cut < 0 or cut - m.start() > 1700:
        raise ValueError(f"Theorem header no longer parses for {name}")
    return " ".join(text[m.start():cut].split()), text.count("\n", 0, m.start()) + 1

def validate():
    seen = set()
    counts = {"train": 0, "evaluation": 0, "challenge": 0}
    for module, (split, count) in MODULES.items():
        path = ROOT / "benchmarks" / "prooflab" / f"{module}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("format") != "pcs-prooflab-source-module-v1" or \
           payload.get("source_revision") != CORE_REVISION or \
           payload.get("module") != module or payload.get("split") != split:
            raise ValueError(f"Invalid source snapshot metadata for {module}")
        if len(payload["records"]) != count:
            raise ValueError(f"Unexpected task count for {module}")
        for record in payload["records"]:
            if record["id"] in seen or record["module"] != module or record["split"] != split:
                raise ValueError(f"Duplicated or reclassified theorem in {module}")
            seen.add(record["id"])
            info = record["source"]
            if info["revision"] != CORE_REVISION:
                raise ValueError("Source revision was not pinned")
            source = (ROOT / info["path"]).resolve()
            if not source.is_relative_to(ROOT) or not source.is_file():
                raise ValueError("Nonlocal source path")
            data = source.read_bytes()
            if blob_sha256_or_git_sha1(data) != info["blob_sha"]:
                raise ValueError(f"Source bytes changed for {record['id']}")
            signature, line = source_signature(data.decode("utf-8"), record["name"])
            if record["statement"] != signature or info["line"] != line:
                raise ValueError(f"Theorem header/line changed for {record['id']}")
            if ":=" in signature or record.get("status") != "source_declared_kernel_not_attested":
                raise ValueError("Proof body exposed or fake Lean certification")
            counts[split] += 1
    if len(seen) != 61 or counts != {"train": 32, "evaluation": 15, "challenge": 14}:
        raise ValueError("Holdout or source count changed")
    return {"records": len(seen), "by_split": counts, "source_blob_attested": 61,
            "new_kernel_builds": 0}

if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
