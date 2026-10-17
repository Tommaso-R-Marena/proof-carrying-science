"""Replay the parametric family blockade; post-hoc and separately source-bound."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from receive import Kernel, RESEARCH, ROOT, audit, canonical, digest


def run(output):
    old = RESEARCH / "kernel/results/supported-family-v1/FamilyTail.lean"
    new = HERE / "BlockFamily.lean"
    sources = {str(p.relative_to(ROOT)): digest(p) for p in (old, new, Path(__file__))}
    k = Kernel(output)
    before = digest(old)
    p = subprocess.run(
        [
            k.base.lean,
            "-M4096",
            "--root=" + str(old.parent),
            "-o",
            str(k.output / "FamilyTail.olean"),
            str(old),
        ],
        env=k.env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    (k.output / "FamilyTail.log").write_text(p.stdout + p.stderr)
    if p.returncode or p.stderr or digest(old) != before:
        raise RuntimeError("Retained family proof failed or changed")
    old_audit = audit(
        p.stdout,
        {"PCS.Research.SupportedCounterexampleFamily.every_tail_input_worsens"},
    )
    k.pins[k.output / "FamilyTail.olean"] = digest(k.output / "FamilyTail.olean")
    fresh_audit = audit(
        k.run(new),
        {
            "PCS.Research.PointwiseFamilyBlock.no_positive_certificate",
            "PCS.Research.PointwiseFamilyBlock.no_guard_authorization",
        },
    )
    if sources != {name: digest(ROOT / name) for name in sources}:
        raise RuntimeError("Post-hoc experiment source drift")
    for path in (old, new):
        (k.output / path.name).write_bytes(path.read_bytes())
    result = {
        "format": "pgsi-pointwise-family-block-v1",
        "post_hoc": True,
        "sources": sources,
        "core_sources": k.sources,
        "lean_version": k.base.version,
        "retained_family_axioms": old_audit,
        "new_theorem_axioms": fresh_audit,
        "claim": "For every integer k >= 18 and every purported cell certificate, the worsening-tail family cannot pass the pointwise checker or its finite-gate composition.",
        "valid_bounded_PGSI1_family": [18, 31],
        "production_authority": False,
        "native_execution_refinement_proved": False,
        "external_scientific_validation": False,
    }
    (k.output / "RESULT.json").write_bytes(canonical(result) + b"\n")
    inventory = {
        p.name: digest(p)
        for p in k.output.iterdir()
        if p.is_file() and p.suffix in {".json", ".lean", ".log"}
    }
    (k.output / "SHA256.json").write_bytes(canonical(inventory) + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    run(p.parse_args().output)
