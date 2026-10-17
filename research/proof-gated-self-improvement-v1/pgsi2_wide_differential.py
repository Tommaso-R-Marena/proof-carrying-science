"""Executable cross-language PGSI2-WIDE differential experiment.

Independent Python decoder and inference are compared with the REAL Lean
decoder and evaluator under identical wire bytes, architecture limits, and
integer inputs. Strong gate positive/negative decisions are made by Lean only.

This is empirical refinement evidence, not a mathematical proof of
Python/Lean byte-to-IO correspondence and not a protected execution root.
Run with the Lean 4.28.0 toolchain:
  python pgsi2_wide_differential.py
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import subprocess
import tempfile

from pgsi2_wide_runtime import (
    Arch, Unit, Wide, WireReject, decode, encode
)

RESEARCH = Path(__file__).resolve().parent
REPO = RESEARCH.parent.parent
FORMAL = REPO / "formal"
FIXTURES = FORMAL / "fixtures" / "proof_gated"
LEAN_SOURCE = RESEARCH / "pgsi2_wide_lean_oracle.lean"
ARCH = Arch(8, 32)
XS = [-10**12, -10001, -100, -33, -32, -4, -3, -2, -1, 0,
      1, 2, 3, 4, 32, 33, 100, 10001, 10**12]


def invoke(*args: str, allow_runtime_error: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["lake", "env", "lean", "--run", str(LEAN_SOURCE), *args],
        cwd=FORMAL, text=True, capture_output=True, timeout=120, check=False,
    )
    if proc.stderr.strip() and not allow_runtime_error:
        raise RuntimeError("Lean produced stderr: " + proc.stderr[:2000])
    return proc


def save(path: Path, contents: bytes) -> str:
    path.write_bytes(contents)
    return str(path)


def main() -> dict:
    if not LEAN_SOURCE.is_file() or not FIXTURES.is_dir():
        raise RuntimeError("need checked-in Lean oracle and V5 fixture tree")
    rng = random.Random(812723)
    canonical = (FIXTURES / "pgsi2_wide_canonical.txt").read_bytes().splitlines()
    if len(canonical) != 8:
        raise AssertionError("PGSI2 golden vector inventory changed")
    models: list[bytes] = list(canonical)
    for _ in range(32):
        width = rng.randrange(0, 7)
        model = Wide(tuple(Unit(*[rng.randrange(-32, 33) for _ in range(3)])
                           for _ in range(width)), rng.randrange(-32, 33))
        models.append(encode(model))

    prediction_pairs = 0
    rejection_checks = 0
    strong_checks = 0
    with tempfile.TemporaryDirectory(prefix="pgsi2-diff-") as tmp:
        directory = Path(tmp)
        model_file = directory / "model.pgsi2"
        for idx, raw in enumerate(models):
            parsed = decode(raw, ARCH)
            if encode(parsed) != raw:
                raise AssertionError("reference canonical roundtrip failed")
            path = save(model_file, raw)
            done = invoke("infer", path, str(ARCH.max_width), str(ARCH.bound),
                          ",".join(str(x) for x in XS))
            if done.returncode != 0 or not done.stdout.startswith("PREDICT:"):
                raise AssertionError(f"Lean rejected canonical model {idx}: {done}")
            result = done.stdout.strip()
            outputs = [int(s) for s in result.removeprefix("PREDICT:").split(",")]
            expected = [parsed.predict(x) for x in XS]
            if outputs != expected:
                raise AssertionError(f"Lean/Python semantic divergence model {idx}")
            prediction_pairs += len(XS)

        negative_files = sorted((FIXTURES / "pgsi2_wide_negative").glob("neg_*.txt"))
        if len(negative_files) != 10:
            raise AssertionError("PGSI2 negative-vector inventory changed")
        for invalid in negative_files:
            raw = invalid.read_bytes()
            try:
                decode(raw, ARCH)
            except WireReject:
                pass
            else:
                raise AssertionError(f"Python accepted malformed {invalid}")
            done = invoke("infer", save(model_file, raw), "8", "32", "0")
            if done.returncode == 0 or "REJECT:invalid_artifact" not in done.stdout:
                raise AssertionError(f"Lean accepted malformed {invalid}")
            rejection_checks += 1

        # Explicit additional byte-oriented adversaries beyond Lean's 10 fixtures.
        for raw in (b"PGSI2-WIDE|0\n", b"PGSI2-WIDE|0\x00",
                    b"\xef\xbb\xbfPGSI2-WIDE|0", b"PGSI2-WIDE|0|1|1|1|"):
            try:
                decode(raw, ARCH)
            except WireReject:
                pass
            else:
                raise AssertionError(f"Python accepted adversarial bytes {raw!r}")
            done = invoke("infer", save(model_file, raw), "8", "32", "0")
            if done.returncode == 0:
                raise AssertionError(f"Lean accepted adversarial bytes {raw!r}")
            rejection_checks += 1

        old = save(directory / "old.pgsi2", b"PGSI2-WIDE|0")
        candidate = save(directory / "candidate.pgsi2", b"PGSI2-WIDE|0|2|1|1")
        target = save(directory / "target.pgsi2",
                      b"PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2")
        corpus = "-4,-3,-2,-1,0,1,2,3,4"
        for low, high, permitted in [(-4, 4, True), (-50, 50, False)]:
            done = invoke("strong", old, candidate, target, "8", "32",
                          str(low), str(high), corpus)
            if permitted:
                if done.returncode != 0 or done.stdout != "ACCEPT_STRONG\n":
                    raise AssertionError(f"Lean strong gate rejected valid chain {done}")
            else:
                if done.returncode == 0 or "REJECT:strong_gate_negative" not in done.stdout:
                    raise AssertionError(f"Lean strong gate admitted robust regression {done}")
            strong_checks += 1

        # The exact canonical model must be pinned to the configured bound.
        for bound in ("0", "1"):
            done = invoke("infer", target, "8", bound, "0")
            if done.returncode == 0:
                raise AssertionError("architecture bound was not enforced")
            strong_checks += 1
        # Absent/altered artifact refuses to execute.
        done = invoke("infer", str(directory / "missing.pgsi2"), "8", "32", "0",
                      allow_runtime_error=True)
        if done.returncode == 0:
            raise AssertionError("missing file was accepted")
        rejection_checks += 1

    summary = {
        "result": "PASS",
        "authority": "actual Lean 4.28.0 CLI, not mock",
        "golden_canonical": 8,
        "seeded_canonical": 32,
        "model_input_prediction_pairs": prediction_pairs,
        "malformed_and_missing_cases": rejection_checks,
        "strong_gate_and_bound_cases": strong_checks,
        "lean_kernel_proof_of_host_refinement": False,
        "production_trusted_root": False,
    }
    print(json.dumps(summary, sort_keys=True, indent=2))
    return summary


if __name__ == "__main__":
    main()
