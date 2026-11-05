"""Bounded hash/source/result verification; never executes archived Lean source."""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
from replay import HERE, canonical, digest, critical_sources, audit, _read_regular
import re


def verify(folder, expected=None):
    folder = Path(folder)
    index = json.loads(_read_regular(folder / "SHA256.json", 262144))
    if type(index) is not dict or len(index) > 512:
        raise ValueError("Evidence inventory budget")
    present = {
        p.name
        for p in folder.iterdir()
        if p.is_file()
        and p.suffix in {".json", ".gz", ".log"}
        and p.name != "SHA256.json"
    }
    required = {
        "RESULTS.json",
        "PROTOCOL.json",
        "MODEL_CLASSIFICATION.json",
        "FORMAL_AUDIT.json",
        "AXIOM_AUDIT.log",
        "PROOFS.tar.gz",
    }
    if not required <= set(index) or set(index) != present:
        raise ValueError("Incomplete or unexpected evidence inventory")
    for name, sha in index.items():
        if Path(name).name != name or not (folder / name).is_file():
            raise ValueError("Invalid evidence path")
        if (
            hashlib.sha256(_read_regular(folder / name, 16 * 1024 * 1024)).hexdigest()
            != sha
        ):
            raise ValueError("Evidence bytes changed: " + name)
    r = json.loads((folder / "RESULTS.json").read_text())
    if r["source_sha256"] != critical_sources():
        raise ValueError("Incomplete or changed proof source inventory")
    names = set(
        re.findall(
            r"^#print axioms ([A-Za-z0-9_.]+)$", (HERE / "Audit.lean").read_text(), re.M
        )
    )
    axioms = audit((folder / "AXIOM_AUDIT.log").read_text(), names)
    if json.loads((folder / "FORMAL_AUDIT.json").read_text()) != axioms:
        raise ValueError("Axiom audit binding mismatch")
    if (
        r["kernel_checked_encoded_mathematical_claims"] is not True
        or r["serialized_host_refinement_proved"] is not False
        or r["production_authority"] is not False
        or r["external_empirical_validation"] is not False
    ):
        raise ValueError("Evidence scope changed")
    expected_outcomes = {
        "finite_accepted": 4081,
        "finite_lost_correct": 76,
        "finite_max_error_regression": 441,
        "finite_both_regressions": 12,
        "both_stronger_filters": 3576,
        "nonvacuous_guard_acceptances": 741,
        "vacuous_stronger_filter_acceptances": 2835,
        "two_unit_configurations": 729,
        "random_multiunit_cases": 64,
    }
    if any(r["outcomes"].get(k) != v for k, v in expected_outcomes.items()):
        raise ValueError("Unexpected exhaustive results")
    if (
        r["kernel_claims"] != 19169
        or r["universal_transitions"] != 16384
        or r["axioms_audited"] != 37
        or len(axioms) != 37
        or r["outcomes"]["universal_preserves_positive"]
        + r["outcomes"]["universal_preserves_negative"]
        != 16384
        or r["outcomes"]["models_with_correct_witness"]
        + r["outcomes"]["models_with_no_correct_integer"]
        != 128
    ):
        raise ValueError("Incomplete qualification")
    protocol = json.loads((folder / "PROTOCOL.json").read_text())
    if (
        protocol["source_sha256"] != r["source_sha256"]
        or digest(folder / "PROTOCOL.json") != r["protocol_sha256"]
    ):
        raise ValueError("Protocol binding mismatch")
    semantic = {
        key: r[key]
        for key in (
            "outcomes",
            "universal_transitions",
            "kernel_claims",
            "axioms_audited",
        )
    }
    if hashlib.sha256(canonical(semantic)).hexdigest() != r["semantic_results_sha256"]:
        raise ValueError("Semantic digest mismatch")
    records = r["batches"] + r["guard_batches"] + r["scaling"]
    if sum(x["claims"] for x in records) != r["kernel_claims"]:
        raise ValueError("Incomplete kernel claim accounting")
    proofs = {x["file"]: x for x in records}
    if len(proofs) != len(records):
        raise ValueError("Duplicate proof identity")
    total = 0
    seen = set()
    with tarfile.open(folder / "PROOFS.tar.gz", mode="r:gz") as archive:
        for member in archive:
            total += member.size
            if (
                not member.isfile()
                or Path(member.name).name != member.name
                or member.name not in proofs
                or member.name in seen
                or member.size > 4 * 1024 * 1024
                or total > 256 * 1024 * 1024
            ):
                raise ValueError("Invalid or excessive proof archive")
            raw = archive.extractfile(member).read(member.size + 1)
            if hashlib.sha256(raw).hexdigest() != proofs[member.name]["sha256"]:
                raise ValueError("Proof archive substitution")
            seen.add(member.name)
    if seen != set(proofs):
        raise ValueError("Missing proof modules")
    if expected is not None:
        old = json.loads(Path(expected).read_text())
        if old["semantic_results_sha256"] != r["semantic_results_sha256"]:
            raise ValueError("Frozen experiment decisions did not reproduce")
    return {
        "format": "pgsi-affine-kernel-evidence-check-v1",
        "source_files": len(r["source_sha256"]),
        "proof_modules": len(proofs),
        "kernel_claims": r["kernel_claims"],
        "semantic_results_sha256": r["semantic_results_sha256"],
        "unsigned_history_authenticated": False,
        "archived_code_executed": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--expected", type=Path)
    a = p.parse_args()
    print(json.dumps(verify(a.folder, a.expected), sort_keys=True))
