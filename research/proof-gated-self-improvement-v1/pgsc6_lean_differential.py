"""Empirically compare *actual Lean V6* PGSC6 byte checker with independent Python.

The pinned mathematical policy is compiled in the Lean adapter as specWide;
the reference policy is independently constructed below, not read from the
untrusted witness. Generation/active are test input, not secured storage.
This is a differential test, NOT a Lean proof of the Python implementation.
"""
from __future__ import annotations
import json
from pathlib import Path
import random
import subprocess
import tempfile

from pgsc6_reference import (
    Policy, decode_certificate, reference_certificate_passes,
)
from pgsi2_wide_runtime import Arch, decode as decode_wide

HERE = Path(__file__).resolve().parent
FORMAL = HERE.parents[1] / "formal"
CERTS = FORMAL / "fixtures" / "proof_gated" / "v6_certs"
ORACLE = HERE / "pgsc6_actual_lean_oracle.lean"
TARGET_BYTES = b"PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2"

PINNED_ARCH = Arch(8, 32)
PINNED_POLICY = Policy(
    PINNED_ARCH,
    decode_wide(TARGET_BYTES, PINNED_ARCH),
    tuple(range(-4, 5)),
    -10**9, 10**9,
)


def invoke(raw: bytes, generation: int, active: bytes,
           working: Path) -> bool:
    af = working / "active.pgsi2"
    cf = working / "candidate.pgsc6"
    af.write_bytes(active)
    cf.write_bytes(raw)
    done = subprocess.run(
        ["lake", "env", "lean", "--run", str(ORACLE),
         "check", str(generation), str(af), str(cf)],
        cwd=FORMAL, text=True, capture_output=True, check=False, timeout=120,
    )
    if done.stderr.strip():
        raise AssertionError("Lean oracle emitted errors: " + done.stderr[:500])
    if done.returncode == 0:
        if done.stdout != "ACCEPT_PGSC6\n":
            raise AssertionError("positive Lean verdict had wrong output")
        return True
    if done.returncode != 1 or done.stdout != "REJECT:certificate_not_authorized\n":
        raise AssertionError(
            "invalid Lean rejection; expected predicate rejection, got " +
            repr((done.returncode, done.stdout[:300], done.stderr[:300]))
        )
    return False


def main() -> dict:
    valid = [(CERTS / f"step{i}.pgsc6").read_bytes() for i in (1, 2, 3)]
    if tuple(map(len, valid)) != (225, 248, 285):
        raise AssertionError("V6 exact fixture sizes changed")
    positive = negative = 0
    with tempfile.TemporaryDirectory(prefix="pgsc6-actual-") as tmp:
        work = Path(tmp)

        def compare(raw: bytes, g: int, active: bytes, expected: bool):
            nonlocal positive, negative
            python = reference_certificate_passes(
                raw, PINNED_POLICY, g, active
            )
            if python != expected:
                raise AssertionError("Independent Python reference deviated")
            lean = invoke(raw, g, active, work)
            if lean != python:
                raise AssertionError("actual Lean/independent Python mismatch")
            if lean:
                positive += 1
            else:
                negative += 1

        for g, raw in enumerate(valid):
            cert = decode_certificate(raw)
            if cert.generation != g:
                raise AssertionError("fixture generation mismatch")
            compare(raw, g, cert.incumbent, True)
            compare(raw, g+1, cert.incumbent, False)
            compare(raw, g, cert.candidate, False)

        # Completely invalid PGSC6 syntax and a parameterized policy change.
        first = decode_certificate(valid[0])
        for raw in (
            b"", valid[0] + b"\n", b"\xef\xbb\xbf" + valid[0],
            valid[0]+b"\x00", valid[0]+b"|1",
            valid[0].replace(b"|-1000000000|1000000000|",
                             b"|-1000000000|1000000001|", 1),
            valid[0].replace(b"|8|32|", b"|8|31|", 1),
        ):
            compare(raw, 0, first.incumbent, False)

        rng = random.Random(20261017)
        replacements = b"01|+-X"
        seen = set()
        while len(seen) < 24:
            idx = rng.randrange(len(valid[0]))
            replacement = rng.choice(replacements)
            if replacement == valid[0][idx] or (idx, replacement) in seen:
                continue
            seen.add((idx, replacement))
            raw = valid[0][:idx] + bytes([replacement]) + valid[0][idx+1:]
            compare(raw, 0, first.incumbent, False)

    summary = {
        "result": "PASS",
        "lean": "actual Lean 4.28.0 V6 checkCertBytes, not a mock",
        "policy": "specWide fixed on Lean checker side",
        "positive": positive,
        "negative": negative,
        "checked": positive + negative,
        "verified_external_io_security": False,
        "verified_external_python_equivalence_theorem": False,
        "trusted_monotonic_generation_store": False,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()
