"""Compile and axiom-audit AssuranceMirage.lean with pinned Lean 4.28.0."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
FORMAL = HERE / "formal"
SOURCE = FORMAL / "AssuranceMirage.lean"
THEOREMS = [
    "AssuranceMirage.admit_unique",
    "AssuranceMirage.step_proposal_independent",
    "AssuranceMirage.tool_trace_independent",
    "AssuranceMirage.channel1_score_independent",
    "AssuranceMirage.constructive_mirage",
    "AssuranceMirage.single_channel_blind",
    "AssuranceMirage.joint_detects_constructive_mirage",
    "AssuranceMirage.completion_not_competence",
    "AssuranceMirage.guard_erases_divergence",
    "AssuranceMirage.unguarded_diverges",
    "AssuranceMirage.guard_completion_independent_unguarded_not",
]
PERMITTED = {"propext", "Quot.sound"}


def digest(b: bytes) -> str:
    return sha256(b).hexdigest()


def _parse_axioms(log: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for th in THEOREMS:
        # lean prints: 'Name' depends on axioms: [a, b]  OR  'Name' does not depend on any axioms
        pat = re.compile(
            rf"'{re.escape(th)}' (depends on axioms: \[(.*?)\]|does not depend on any axioms)"
        )
        m = pat.search(log)
        if not m:
            raise ValueError(f"Missing axiom inventory for {th}")
        if m.group(1).startswith("does not"):
            out[th] = []
        else:
            raw = m.group(2).strip()
            out[th] = [] if not raw else [x.strip() for x in raw.split(",")]
    return out


def check_formal(out: Path) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    lean = shutil.which("lean")
    leanchecker = shutil.which("leanchecker")
    if lean is None or leanchecker is None:
        raise ValueError("Lean 4.28.0 must be activated (lean and leanchecker on PATH)")
    src = SOURCE.read_bytes()
    staged = out / "AssuranceMirage.lean"
    audited = src + ("\n" + "\n".join(f"#print axioms {t}" for t in THEOREMS) + "\n").encode()
    staged.write_bytes(audited)
    lean_bin = Path(lean).resolve().parent
    env = {
        "PATH": f"{lean_bin}:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LEAN_PATH": str(out),
    }
    start = time.monotonic()
    proc = subprocess.run(
        [
            lean,
            "-j1",
            "-M2048",
            "-D",
            "Elab.async=false",
            "--root=" + str(out),
            "-o",
            "AssuranceMirage.olean",
            "AssuranceMirage.lean",
        ],
        cwd=out,
        capture_output=True,
        text=True,
        env=env,
        timeout=240,
        check=False,
    )
    log = (proc.stdout or "") + (proc.stderr or "")
    (out / "lean.log").write_text(log)
    if proc.returncode != 0:
        raise ValueError(f"Lean build failed:\n{log[-2000:]}")
    axioms = _parse_axioms(log)
    for th, axs in axioms.items():
        bad = set(axs) - PERMITTED
        if bad:
            raise ValueError(f"Unexpected axioms for {th}: {sorted(bad)}")
    # Fresh kernel check of the compiled module.
    chk = subprocess.run(
        [leanchecker, "--fresh", "AssuranceMirage"],
        cwd=out,
        capture_output=True,
        text=True,
        env=env,
        timeout=240,
        check=False,
    )
    (out / "leanchecker.log").write_text((chk.stdout or "") + (chk.stderr or ""))
    if chk.returncode != 0:
        raise ValueError("leanchecker --fresh failed")
    manifest = {
        "format": "pcs-assurance-mirage-formal-v1",
        "source_sha256": digest(src),
        "staged_sha256": digest(audited),
        "olean_sha256": digest((out / "AssuranceMirage.olean").read_bytes()),
        "lean_path": lean,
        "leanchecker_path": leanchecker,
        "theorems": THEOREMS,
        "axiom_closures": axioms,
        "permitted_axioms": sorted(PERMITTED),
        "kernel_checked": True,
        "native_decide": False,
        "sorry": False,
        "production_authority": False,
        "seconds": round(time.monotonic() - start, 6),
    }
    (out / "formal.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
