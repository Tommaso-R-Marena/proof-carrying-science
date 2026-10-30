#!/usr/bin/env python3
"""Execute the assurance-lattice composition experiment and freeze evidence."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcs.assurance_lattice_v1 import (  # noqa: E402
    adversarial_campaign,
    evaluate,
    formal_source,
    kernel_replay,
    proof_source,
)
from pcs.canonical_json import canonicalize_jcs_bytes  # noqa: E402

EXAMPLES = ROOT / "examples" / "assurance_lattice_v1"
OUT = Path(__file__).resolve().parent / "final"


def _load(name: str) -> bytes:
    return canonicalize_jcs_bytes(json.loads((EXAMPLES / name).read_text()))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = {
        "composed_scientific_chain": _load("composed_scientific_chain.json"),
        "bridged_upgrade": _load("bridged_upgrade.json"),
        "silent_formal_forgery": _load("silent_formal_forgery.json"),
    }
    results = {}
    for name, raw in cases.items():
        report = evaluate(raw)
        campaign = adversarial_campaign(raw)
        kernel = kernel_replay(raw, timeout=90)
        results[name] = {
            "package_sha256": report["package_sha256"],
            "python_outcome": report["outcome"],
            "violations": report["violations"],
            "certified_claim_ids": report["certified_claim_ids"],
            "adversarial_campaign_pass": campaign["campaign_pass"],
            "false_formal_accepts": campaign["false_formal_accepts"],
            "kernel_status": kernel["status"],
            "kernel_checked": kernel.get("kernel_checked", False),
            "kernel_axioms": kernel.get("kernel_axioms", []),
        }
        (OUT / f"{name}.python-replay.json").write_bytes(canonicalize_jcs_bytes(report))
        (OUT / f"{name}.adversarial.json").write_bytes(canonicalize_jcs_bytes(campaign))
        (OUT / f"{name}.kernel-replay.json").write_bytes(canonicalize_jcs_bytes(kernel))
        (OUT / f"{name}.Replay.lean").write_bytes(proof_source(raw))

    (OUT / "PCSAssuranceLattice.lean.sha256").write_text(
        __import__("hashlib").sha256(formal_source()).hexdigest() + "\n", encoding="utf-8")
    summary = {
        "format": "pcs-assurance-lattice-experiment-v1",
        "cases": results,
        "acceptance_criteria": {
            "composed_chain_python_pass": results["composed_scientific_chain"]["python_outcome"] == "PASS",
            "composed_chain_kernel_checked": results["composed_scientific_chain"]["kernel_checked"] is True,
            "forgery_python_fail": results["silent_formal_forgery"]["python_outcome"] == "FAIL",
            "forgery_no_kernel_support": results["silent_formal_forgery"]["kernel_checked"] is False,
            "bridged_upgrade_pass": results["bridged_upgrade"]["python_outcome"] == "PASS",
            "zero_false_formal_accepts_on_composed":
                results["composed_scientific_chain"]["false_formal_accepts"] == 0,
        },
        "scientific_acceptance": False,
        "notes": [
            "Finite typed epistemic composition only.",
            "No continuum accuracy, empirical validity, or production authority claimed.",
        ],
    }
    summary["experiment_pass"] = all(summary["acceptance_criteria"].values())
    (OUT / "EXPERIMENT.json").write_bytes(canonicalize_jcs_bytes(summary))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["experiment_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
