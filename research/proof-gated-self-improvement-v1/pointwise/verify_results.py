"""Bounded evidence receiver. Checks provenance; does not execute archived code."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

from receive import HERE, audit, canonical, critical_sources, digest, _read_regular


def verify(folder, expected=None):
    folder = Path(folder)
    index = json.loads(_read_regular(folder / "SHA256.json", 262144))
    if type(index) is not dict or len(index) > 512:
        raise ValueError("Inventory budget")
    present = {
        p.name
        for p in folder.iterdir()
        if p.is_file()
        and p.suffix in {".json", ".log", ".gz"}
        and p.name != "SHA256.json"
    }
    required = {
        "RESULTS.json",
        "PROTOCOL.json",
        "DECISIONS.json",
        "SEARCH_GRAPH.json",
        "AXIOMS.json",
        "Audit-lean.log",
        "PROOFS.tar.gz",
    }
    if set(index) != present or not required <= present:
        raise ValueError("Incomplete or unexpected inventory")
    for name, sha in index.items():
        if (
            Path(name).name != name
            or hashlib.sha256(
                _read_regular(folder / name, 16 * 1024 * 1024)
            ).hexdigest()
            != sha
        ):
            raise ValueError("Evidence path or digest mismatch")
    result = json.loads((folder / "RESULTS.json").read_text())
    if result["source_sha256"] != critical_sources():
        raise ValueError("Incomplete or changed critical sources")
    protocol = json.loads((folder / "PROTOCOL.json").read_text())
    if (
        protocol["source_sha256"] != result["source_sha256"]
        or digest(folder / "PROTOCOL.json") != result["protocol_sha256"]
    ):
        raise ValueError("Protocol binding mismatch")
    names = {
        "PCS.Research.Pointwise." + n
        for n in re.findall(
            r"^theorem ([A-Za-z0-9_]+)", (HERE / "Pointwise.lean").read_text(), re.M
        )
    }
    axioms = audit((folder / "Audit-lean.log").read_text(), names)
    if json.loads((folder / "AXIOMS.json").read_text()) != axioms or result[
        "pointwise_theorems"
    ] != len(names):
        raise ValueError("Axiom inventory mismatch")
    if any(
        result.get(k) is not v
        for k, v in {
            "kernel_checked_encoded_mathematical_claims": True,
            "native_execution_refinement_proved": False,
            "production_authority": False,
            "external_empirical_validation": False,
        }.items()
    ):
        raise ValueError("Research scope changed")
    semantic = {
        k: result[k]
        for k in (
            "outcomes",
            "kernel_claims",
            "universal_transitions",
            "pointwise_theorems",
            "search_graph",
        )
    }
    if (
        hashlib.sha256(canonical(semantic)).hexdigest()
        != result["semantic_results_sha256"]
    ):
        raise ValueError("Semantic digest mismatch")
    outcomes = result["outcomes"]
    if (
        result["kernel_claims"] != 17992
        or result["universal_transitions"] != 16384
        or outcomes["finite_accepted"] != 4081
        or outcomes["pointwise_positive"] + outcomes["pointwise_negative"] != 16384
    ):
        raise ValueError("Incomplete experiment")
    proofs = {r["file"]: r for r in result["proofs"]}
    if (
        len(proofs) != len(result["proofs"])
        or sum(r["claims"] for r in proofs.values()) != result["kernel_claims"]
    ):
        raise ValueError("Duplicate or incomplete proof accounting")
    for name, record in proofs.items():
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*\.lean", name):
            raise ValueError("Invalid generated module name")
        checked = audit(
            (folder / (Path(name).stem + "-lean.log")).read_text(),
            {"PCS.Research.PointwiseReplay.claims_sound"},
        )
        if checked != record["axioms"]:
            raise ValueError("Concrete proof audit binding mismatch")
    decisions = json.loads((folder / "DECISIONS.json").read_text())
    transitions = decisions["transitions"]
    if len(decisions["models"]) != 128 or len(transitions) != 16384:
        raise ValueError("Incomplete transition inventory")
    for i, item in enumerate(transitions):
        if (
            item["old"] != i // 128
            or item["new"] != i % 128
            or type(item["finite"]) is not bool
            or type(item["pointwise"]) is not bool
        ):
            raise ValueError("Duplicate, unordered or invalid transition inventory")
    if (
        sum(d["pointwise"] for d in transitions) != outcomes["pointwise_positive"]
        or sum(d["finite"] for d in transitions) != outcomes["finite_accepted"]
        or sum(d["finite"] and d["pointwise"] for d in transitions)
        != outcomes["finite_and_pointwise_accepted"]
        or json.loads((folder / "SEARCH_GRAPH.json").read_text())
        != result["search_graph"]
    ):
        raise ValueError("Outcome binding mismatch")
    total, seen = 0, set()
    with tarfile.open(folder / "PROOFS.tar.gz", "r:gz") as archive:
        for member in archive:
            total += member.size
            if (
                not member.isfile()
                or member.name not in proofs
                or Path(member.name).name != member.name
                or member.name in seen
                or member.size > 4 * 1024 * 1024
                or total > 256 * 1024 * 1024
            ):
                raise ValueError("Invalid or excessive archive member")
            raw = archive.extractfile(member).read(member.size + 1)
            if hashlib.sha256(raw).hexdigest() != proofs[member.name]["sha256"]:
                raise ValueError("Proof bytes changed")
            seen.add(member.name)
    if seen != set(proofs):
        raise ValueError("Missing proofs")
    if (
        expected is not None
        and json.loads(Path(expected).read_text())["semantic_results_sha256"]
        != result["semantic_results_sha256"]
    ):
        raise ValueError("Frozen experiment did not reproduce")
    return {
        "source_files": len(result["source_sha256"]),
        "kernel_claims": result["kernel_claims"],
        "proof_modules": len(proofs),
        "semantic_results_sha256": result["semantic_results_sha256"],
        "archived_code_executed": False,
        "unsigned_history_authenticated": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--expected", type=Path)
    args = p.parse_args()
    print(json.dumps(verify(args.folder, args.expected), sort_keys=True))
