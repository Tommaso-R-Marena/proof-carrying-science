"""Strict receiver-owned, data-only whole-domain mathematical replay.

No production authority, storage promotion, or external empirical validity.
Hashes detect drift; the owner, Lean kernel/toolchain and host remain trusted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
ROOT = RESEARCH.parent.parent
sys.path.insert(0, str(RESEARCH / "kernel"))
from replay import (
    Kernel as BaseKernel,
    audit,
    canonical,
    digest,
    lean_net,
    net,
    rows,
    z,
)
from affine_certificates import model_hash
from promotion_v2 import _read_regular, strict_json
from universal_relu import Net


def expression(cert, expected_nets):
    ns = tuple(expected_nets)
    if len(ns) != 3 or any(type(n) is not Net for n in ns):
        raise ValueError("Receiver owns three exact models")
    if sum(len(n.terms) for n in ns) > 128:
        raise ValueError("Total model width budget exceeded")
    # Validate every parameter even for a negative claim.
    arguments = " ".join(lean_net(n) for n in ns)
    if (
        type(cert) is not dict
        or set(cert) != {"format", "model_sha256", "cells", "result", "kernel_proved"}
        or cert["format"] != "pgsi-pointwise-dominance-v1"
        or cert["kernel_proved"] is not False
    ):
        raise ValueError("Invalid exact certificate schema")
    if cert["model_sha256"] != [model_hash(n) for n in ns]:
        raise ValueError("Certificate differs from receiver-owned models")
    row_text = rows(cert, 3)  # Validate bounded typed data even for a negative claim.
    result = cert["result"]
    if (
        type(result) is not dict
        or set(result) != {"passes", "counterexample"}
        or type(result["passes"]) is not bool
    ):
        raise ValueError("Invalid decision schema")
    if result["passes"]:
        if result["counterexample"] is not None:
            raise ValueError("Positive claim contains counterexample")
        return f"(.dominates {arguments} {row_text} : Claim)"
    return f"(.notDominates {arguments} {z(result['counterexample'])} : Claim)"


def module(expressions):
    if not 1 <= len(expressions) <= 128:
        raise ValueError("Batch budget exceeded")
    return (
        "import Pointwise\nset_option maxRecDepth 10000\n"
        "set_option maxHeartbeats 20000000\n"
        "open PCS.Research.IntegerAffine PCS.Research.Pointwise\n"
        "namespace PCS.Research.PointwiseReplay\n"
        "def claims : List PCS.Research.Pointwise.Claim := [\n"
        + ",\n".join(expressions)
        + "]\n"
        "theorem checked : claims.all PCS.Research.Pointwise.check = true := by decide\n"
        "theorem claims_sound : ∀ c ∈ claims, PCS.Research.Pointwise.Meaning c := batch_sound claims checked\n"
        "#print axioms claims_sound\nend PCS.Research.PointwiseReplay\n"
    )


def critical_sources():
    from replay import critical_sources as base_sources

    sources = base_sources()
    for pattern in ("*.py", "*.lean", "tests/*.py"):
        sources.update(
            {str(p.relative_to(ROOT)): digest(p) for p in HERE.glob(pattern)}
        )
    return sources


class Kernel:
    def __init__(self, output):
        self.output = Path(output).absolute()
        self.output.mkdir(mode=0o700, exist_ok=False)
        self.sources = critical_sources()
        self.base = BaseKernel(self.output / "base")
        self.env = dict(
            self.base.env,
            LEAN_PATH=str(self.output) + os.pathsep + self.base.env["LEAN_PATH"],
        )
        self.pins = {}
        self.run(HERE / "Pointwise.lean", self.output / "Pointwise.olean")
        self.pins = {p: digest(p) for p in self.output.glob("*.olean")}
        declared = {
            "PCS.Research.Pointwise." + n
            for n in re.findall(
                r"^theorem ([A-Za-z0-9_]+)", (HERE / "Pointwise.lean").read_text(), re.M
            )
        }
        text = (
            "import Pointwise\n"
            + "\n".join("#print axioms " + n for n in sorted(declared))
            + "\n"
        )
        path = self.output / "Audit.lean"
        path.write_text(text)
        raw = self.run(path)
        self.axioms = audit(raw, declared)
        (self.output / "AXIOMS.json").write_bytes(canonical(self.axioms) + b"\n")
        self.count = 0

    def check_sources(self):
        self.base.check_sources()
        if critical_sources() != self.sources:
            raise RuntimeError("Pointwise source changed during replay")
        if any(digest(p) != h for p, h in self.pins.items()):
            raise RuntimeError("Compiled pointwise checker changed during replay")

    def run(self, path, olean=None):
        self.check_sources()
        args = [self.base.lean, "-M4096", "--root=" + str(HERE)]
        if olean is not None:
            args += ["-o", str(olean)]
        args += [str(path)]
        p = subprocess.run(
            args, env=self.env, cwd=HERE, capture_output=True, text=True, timeout=120
        )
        (self.output / (path.stem + "-lean.log")).write_text(p.stdout + p.stderr)
        self.check_sources()
        if p.returncode or p.stderr:
            raise RuntimeError(
                "Kernel rejection or failure:\n" + (p.stdout + p.stderr)[-6000:]
            )
        return p.stdout

    def replay(self, expressions, name):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            raise ValueError("Invalid receiver output name")
        raw = module(expressions).encode()
        path = self.output / (name + ".lean")
        with path.open("xb") as f:
            f.write(raw)
        expected = hashlib.sha256(raw).hexdigest()
        if digest(path) != expected:
            raise RuntimeError("Generated proof changed before replay")
        start = time.perf_counter()
        axioms = audit(self.run(path), {"PCS.Research.PointwiseReplay.claims_sound"})
        if digest(path) != expected:
            raise RuntimeError("Generated proof changed during replay")
        self.count += len(expressions)
        return {
            "file": path.name,
            "sha256": expected,
            "claims": len(expressions),
            "elapsed_seconds": time.perf_counter() - start,
            "axioms": axioms,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = _read_regular(args.request, 4 * 1024 * 1024)
    data = strict_json(raw)
    if (
        type(data) is not dict
        or set(data) != {"models", "certificate"}
        or type(data["models"]) is not list
    ):
        raise ValueError("Invalid receiver-owned request")
    expr = expression(data["certificate"], tuple(net(n) for n in data["models"]))
    k = Kernel(args.output)
    proof = k.replay([expr], "Received")
    receipt = {
        "format": "pgsi-pointwise-replay-v1",
        "verified_property": "whole-integer-pointwise-absolute-error-dominance",
        "verified_verdict": "HOLDS"
        if data["certificate"]["result"]["passes"]
        else "REFUTED",
        "counterexample": data["certificate"]["result"]["counterexample"],
        "request_sha256": hashlib.sha256(raw).hexdigest(),
        "sources": k.sources,
        "proof": proof,
        "lean_version": k.base.version,
        "kernel_checked_encoded_mathematical_claim": True,
        "native_execution_refinement_proved": False,
        "promotion_performed": False,
        "production_authority": False,
        "external_scientific_validation": False,
    }
    (k.output / "RECEIPT.json").write_bytes(canonical(receipt) + b"\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
