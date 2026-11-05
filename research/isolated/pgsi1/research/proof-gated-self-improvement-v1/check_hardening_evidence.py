"""Verify recorded campaign bytes, source identities and research-only scope.

Historical producer binary pin is recorded, not authenticated by an unsigned
inventory. Live CI separately rebuilds and executes the receiver-owned authority.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from build_authority import source_inventory

HERE = Path(__file__).resolve().parent


def check(folder):
    folder = Path(folder)
    index = json.loads((folder / "SHA256.json").read_text())
    for name, expected in index.items():
        if Path(name).name != name:
            raise ValueError("Unsafe evidence name")
        p = folder / name
        if p.is_file():
            raw = p.read_bytes()
        else:
            compressed = folder / (name + ".gz")
            with gzip.open(compressed, "rb") as stream:
                raw = stream.read(32 * 1024 * 1024 + 1)
            if len(raw) > 32 * 1024 * 1024:
                raise ValueError("Evidence expansion budget exceeded")
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Evidence byte substitution: " + name)
    result = json.loads((folder / "RESULTS.json").read_text())
    expected_paths = {str(p.relative_to(HERE)) for p in HERE.glob("*.py")}
    expected_paths.update(
        str(p.relative_to(HERE)) for p in (HERE / "authority").iterdir()
    )
    expected_paths.add("ARISTOTLE_INTEGRATION_BOUNDARY.json")
    if set(result["source_sha256"]) != expected_paths:
        raise ValueError("Incomplete or unexpected research source inventory")
    for name, expected in result["source_sha256"].items():
        path = (HERE / name).resolve()
        if (
            not path.is_relative_to(HERE)
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError(
                "Current research source differs from qualified evidence: " + name
            )
    manifest = json.loads((folder / "NATIVE_AUTHORITY_MANIFEST.json").read_text())
    if manifest["sources"] != source_inventory():
        raise ValueError("Formal/native source boundary mismatch")
    if (
        result["native_gate_transitions_checked"] != 16384
        or result["native_python_gate_mismatches"] != 0
        or result["kernel_proved_universal_analyzer"] is not False
        or result["native_execution_refinement_proved"] is not False
        or result["external_blind_empirical_validation"] is not False
        or result["accelerating_recursive_self_improvement_established"] is not False
    ):
        raise ValueError("Evidence scope was promoted")
    protocol = json.loads((folder / "PROTOCOL.json").read_text())
    if set(protocol["training_start_ids"]) & set(protocol["evaluation_start_ids"]):
        raise ValueError("Training/evaluation state leakage")
    if (
        protocol["selection_uses_heldout_errors"] is not False
        or protocol["universal_policies_know_the_entire_modeled_target"] is not True
    ):
        raise ValueError("Incorrect empirical independence claim")
    return {
        "format": "pgsi-recorded-evidence-integrity-v1",
        "files_verified": len(index),
        "source_files_verified": len(result["source_sha256"]),
        "semantic_results_sha256": result["semantic_results_sha256"],
        "unsigned_producer_history_authenticated": False,
        "scientific_acceptance": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, default=HERE / "evidence/hardening-v1")
    a = p.parse_args()
    print(json.dumps(check(a.folder), sort_keys=True))
