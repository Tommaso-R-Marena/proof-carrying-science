"""Strict data-to-Lean replay for research integer affine certificates.

Generated theorems use kernel reduction (`decide`), never native_decide, a
producer verdict, or an assumed model-training trace. The receiver supplies the
exact models/property. This proves the encoded mathematical claim, not Python,
compiler, OS, GPU, serialized-artifact correspondence or production authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
ROOT = RESEARCH.parent.parent
sys.path.insert(0, str(RESEARCH))
from affine_certificates import model_hash
from build_authority import source_inventory
from promotion_v2 import canonical, strict_json, _read_regular
from universal_relu import Net, Term

MAX_TERMS = 128
MAX_CELLS = 513
MAX_BITS = 512
APPROVED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def integer(x):
    if type(x) is not int or x.bit_length() > MAX_BITS:
        raise ValueError("Expected bounded-size exact integer")
    return x


def net(data):
    if type(data) is not dict or set(data) != {"bias", "terms"}:
        raise ValueError("Expected exact model fields")
    if type(data["terms"]) is not list or len(data["terms"]) > MAX_TERMS:
        raise ValueError("Model width budget exceeded")
    terms = []
    for t in data["terms"]:
        if type(t) is not list or len(t) != 3:
            raise ValueError("Expected coefficient/weight/bias triple")
        terms.append(Term(*(integer(x) for x in t)))
    return Net(tuple(terms), integer(data["bias"]))


def z(x):
    x = integer(x)
    return f"({x} : Int)"


def opt(x):
    return "none" if x is None else f"(some {z(x)})"


def lean_net(n):
    if type(n) is not Net:
        raise ValueError("Receiver-owned exact model required")
    return (
        "(⟨["
        + ",".join(
            "⟨" + ",".join(z(x) for x in (t.coefficient, t.weight, t.bias)) + "⟩"
            for t in n.terms
        )
        + "],"
        + z(n.bias)
        + "⟩ : Net)"
    )


def rows(cert, count):
    cells = cert["cells"]
    if type(cells) is not list or not 1 <= len(cells) <= MAX_CELLS:
        raise ValueError("Cell budget exceeded")
    result = []
    for c in cells:
        if type(c) is not dict or set(c) != {"low", "high", "affine"}:
            raise ValueError("Expected exact cell fields")
        forms = c["affine"]
        if type(forms) is not list or len(forms) != count:
            raise ValueError("Affine model arity mismatch")
        fs = []
        for f in forms:
            if type(f) is not list or len(f) != 2:
                raise ValueError("Expected affine coefficient pair")
            fs.append("⟨" + ",".join(z(x) for x in f) + "⟩")
        if count == 2:
            fs.append("⟨0,0⟩")
        result.append(
            "⟨⟨" + opt(c["low"]) + "," + opt(c["high"]) + "⟩," + ",".join(fs) + "⟩"
        )
    return "[" + ",".join(result) + "]"


def expression(cert, expected_nets, property_name, interval=None, witness=None):
    """Only emit typed numeric constructors; never interpolate untrusted code."""
    ns = tuple(expected_nets)
    if property_name not in {"equal", "preserves", "max_error"}:
        raise ValueError("Unknown receiver property")
    count = 3 if property_name == "preserves" else 2
    if len(ns) != count or any(type(n) is not Net for n in ns):
        raise ValueError("Receiver model arity mismatch")
    if sum(len(n.terms) for n in ns) > MAX_TERMS:
        raise ValueError("Total model width budget exceeded")
    expected_fields = {
        "format",
        "property",
        "model_sha256",
        "interval",
        "cells",
        "result",
        "kernel_proved",
    }
    if (
        type(cert) is not dict
        or set(cert) != expected_fields
        or cert["format"] != "pgsi-integer-affine-certificate-v1"
        or cert["property"] != property_name
        or cert["kernel_proved"] is not False
        or cert["model_sha256"] != [model_hash(n) for n in ns]
        or cert["interval"] != (list(interval) if interval is not None else None)
    ):
        raise ValueError("Certificate differs from receiver-owned claim/models")
    arguments = " ".join(lean_net(n) for n in ns)
    result = cert["result"]
    if type(result) is not dict:
        raise ValueError("Expected result object")
    if property_name == "max_error":
        if (
            type(interval) is not tuple
            or len(interval) != 2
            or set(result) != {"max_error", "argmax"}
            or witness is not None
        ):
            raise ValueError("Invalid maximum request")
        lo, hi = map(integer, interval)
        m = integer(result["max_error"])
        if m < 0:
            raise ValueError("Negative absolute error")
        return f"(.maximum {arguments} {rows(cert, count)} {z(lo)} {z(hi)} {m} {z(result['argmax'])} : Claim)"
    if (
        interval is not None
        or set(result) != {"passes", "counterexample"}
        or type(result["passes"]) is not bool
    ):
        raise ValueError("Invalid universal request")
    if not result["passes"]:
        if witness is not None:
            raise ValueError("Negative decision cannot request nonvacuity")
        tag = "notEqual" if property_name == "equal" else "notPreserves"
        # A negative witness needs no partition assumptions. The kernel evaluates it.
        return f"(.{tag} {arguments} {z(result['counterexample'])} : Claim)"
    if result["counterexample"] is not None:
        raise ValueError("Positive decision contains a counterexample")
    if witness is not None:
        if property_name != "preserves":
            raise ValueError("Nonvacuity applies to preservation")
        return f"(.nonvacuous {arguments} {rows(cert, count)} {z(witness)} : Claim)"
    tag = "equal" if property_name == "equal" else "preserves"
    return f"(.{tag} {arguments} {rows(cert, count)} : Claim)"


def module(expressions):
    if not 1 <= len(expressions) <= 256:
        raise ValueError("Kernel batch budget exceeded")
    return (
        "import CertificateClaims\n"
        "set_option maxRecDepth 10000\n"
        "set_option maxHeartbeats 20000000\n"
        "open PCS.Research.IntegerAffine\n"
        "namespace PCS.Research.Replayed\n"
        "def claims : List Claim := [\n" + ",\n".join(expressions) + "]\n"
        "theorem checked : claims.all checkClaim = true := by decide\n"
        "theorem claims_sound : ∀ c ∈ claims, Meaning c := checkBatch_sound claims checked\n"
        "#print axioms claims_sound\n"
        "end PCS.Research.Replayed\n"
    )


def audit(raw, expected):
    pat = re.compile(
        r"'([^']+)' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)"
    )
    result = {}
    for match in pat.finditer(raw):
        name, body = match.groups()
        if name in result:
            raise ValueError("Duplicate theorem audit")
        values = (
            [] if body is None else [x.strip() for x in body.split(",") if x.strip()]
        )
        if set(values) - APPROVED_AXIOMS:
            raise ValueError("Unapproved theorem axiom")
        result[name] = values
    if set(result) != set(expected) or pat.sub("", raw).strip():
        raise ValueError("Incomplete or unexpected theorem audit")
    return result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def critical_sources():
    sources = source_inventory()
    sources.update({str(p.relative_to(ROOT)): digest(p) for p in RESEARCH.glob("*.py")})
    sources.update(
        {
            str(p.relative_to(ROOT)): digest(p)
            for pattern in ("*.lean", "*.py", "tests/*.py")
            for p in HERE.glob(pattern)
        }
    )
    return sources


class Kernel:
    def __init__(self, output, *, build=True):
        self.output = Path(output).absolute()
        self.output.mkdir(mode=0o700, exist_ok=False)
        self.lean = shutil.which("lean")
        if self.lean is None:
            raise RuntimeError("Lean 4.28.0 is required")
        p = subprocess.run(
            [self.lean, "--version"], capture_output=True, text=True, check=True
        )
        self.version = p.stdout.strip()
        if not self.version.startswith("Lean (version 4.28.0,"):
            raise RuntimeError("Wrong Lean toolchain")
        self.sources = critical_sources()
        self.env = dict(
            os.environ,
            LEAN_PATH=str(self.output)
            + os.pathsep
            + str(ROOT / "formal/.lake/build/lib/lean"),
        )
        if build:
            p = subprocess.run(
                [
                    str(Path(self.lean).with_name("lake")),
                    "build",
                    "PCS.V2.ProofGatedSelfImprovement",
                ],
                cwd=ROOT / "formal",
                capture_output=True,
                text=True,
                timeout=120,
            )
            (self.output / "dependency-build.log").write_text(p.stdout + p.stderr)
            if p.returncode:
                raise RuntimeError("Frozen Lean dependency build failed")
        for name in ("IntegerAffine", "CertificateClaims", "PGSI1Bridge", "Controls"):
            self.run(HERE / (name + ".lean"), self.output / (name + ".olean"))
        audit_text = self.run(HERE / "Audit.lean")
        expected = set(
            re.findall(
                r"^#print axioms ([A-Za-z0-9_.]+)$",
                (HERE / "Audit.lean").read_text(),
                re.M,
            )
        )
        declared = set()
        for filename, namespace in (
            ("IntegerAffine", "PCS.Research.IntegerAffine"),
            ("CertificateClaims", "PCS.Research.IntegerAffine"),
            ("PGSI1Bridge", "PCS.Research.PGSI1Bridge"),
            ("Controls", "PCS.Research.KernelControls"),
        ):
            declared.update(
                namespace + "." + name
                for name in re.findall(
                    r"^theorem ([A-Za-z0-9_]+)",
                    (HERE / (filename + ".lean")).read_text(),
                    re.M,
                )
            )
        if expected != declared:
            raise ValueError("Audit does not cover every isolated theorem")
        self.axioms = audit(audit_text, expected)
        (self.output / "AXIOM_AUDIT.log").write_text(audit_text)
        (self.output / "FORMAL_AUDIT.json").write_bytes(canonical(self.axioms) + b"\n")
        self.olean_pins = {p: digest(p) for p in self.output.glob("*.olean")}
        self.count = 0

    def check_sources(self):
        if critical_sources() != self.sources:
            raise RuntimeError("Proof source changed during replay")
        if any(
            digest(p) != expected
            for p, expected in getattr(self, "olean_pins", {}).items()
        ):
            raise RuntimeError("Compiled checker changed during replay")

    def run(self, path, olean=None):
        self.check_sources()
        args = [self.lean, "-M4096", "--root=" + str(HERE)]
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
                "Kernel check rejected or failed:\n" + (p.stdout + p.stderr)[-6000:]
            )
        return p.stdout

    def replay(self, expressions, name):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            raise ValueError("Invalid receiver output name")
        path = self.output / (name + ".lean")
        raw = module(expressions)
        with path.open("x") as f:
            f.write(raw)
        start = time.perf_counter()
        expected_sha = hashlib.sha256(raw.encode()).hexdigest()
        if digest(path) != expected_sha:
            raise RuntimeError("Generated proof bytes changed before replay")
        log = self.run(path)
        if digest(path) != expected_sha:
            raise RuntimeError("Generated proof bytes changed during replay")
        records = audit(log, {"PCS.Research.Replayed.claims_sound"})
        (self.output / (name + ".log")).write_text(log)
        self.count += len(expressions)
        return {
            "file": path.name,
            "sha256": expected_sha,
            "claims": len(expressions),
            "elapsed_seconds": time.perf_counter() - start,
            "axioms": records,
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    request_raw = _read_regular(args.request, 4 * 1024 * 1024)
    request = strict_json(request_raw)
    if type(request) is not dict or set(request) != {
        "property",
        "models",
        "certificate",
        "interval",
        "witness",
    }:
        raise ValueError("Expected receiver request schema")
    if type(request["models"]) is not list:
        raise ValueError("Expected receiver model list")
    ns = tuple(net(x) for x in request["models"])
    interval = None if request["interval"] is None else tuple(request["interval"])
    expr = expression(
        request["certificate"], ns, request["property"], interval, request["witness"]
    )
    k = Kernel(args.output)
    record = k.replay([expr], "Received")
    receipt = {
        "format": "pgsi-affine-kernel-replay-v1",
        "lean_version": k.version,
        "sources": k.sources,
        "request_sha256": hashlib.sha256(request_raw).hexdigest(),
        "proof": record,
        "kernel_checked_encoded_mathematical_claim": True,
        "native_execution_refinement_proved": False,
        "pcs_promotion_authority": False,
        "external_scientific_validation": False,
    }
    (k.output / "RECEIPT.json").write_bytes(canonical(receipt) + b"\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
