"""Compile and axiom-audit EvolvingSafetyGate.lean with pinned Lean 4.28.0."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "formal" / "EvolvingSafetyGate.lean"
THEOREMS = [
    "EvolvingSafetyGate.channel1_never_admissible",
    "EvolvingSafetyGate.correcting_alone_never_admissible",
    "EvolvingSafetyGate.joint_channel_admissible",
    "EvolvingSafetyGate.joint_detecting_guard_admissible",
    "EvolvingSafetyGate.ensemble_probe_admissible",
    "EvolvingSafetyGate.composed_stack_admissible",
    "EvolvingSafetyGate.joint_detecting_dominates_channel1",
    "EvolvingSafetyGate.joint_detecting_dominates_correcting",
    "EvolvingSafetyGate.joint_channel_dominates_channel1",
    "EvolvingSafetyGate.ensemble_dominates_joint_detecting",
    "EvolvingSafetyGate.ensemble_dominates_channel1",
    "EvolvingSafetyGate.composed_dominates_ensemble",
    "EvolvingSafetyGate.composed_dominates_channel1",
    "EvolvingSafetyGate.retain_joint_over_channel1",
    "EvolvingSafetyGate.retain_ensemble_over_joint",
    "EvolvingSafetyGate.retain_composed_over_ensemble",
    "EvolvingSafetyGate.never_retain_channel1_over_joint",
    "EvolvingSafetyGate.admissible_iff_pos_rank",
    "EvolvingSafetyGate.retained_stays_admissible",
    "EvolvingSafetyGate.nonadmissible_never_dominates_admissible",
    "EvolvingSafetyGate.catalog_exhaustive",
]
PERMITTED = {"propext", "Quot.sound"}


def digest(b: bytes) -> str:
    return sha256(b).hexdigest()


def _parse_axioms(log: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for th in THEOREMS:
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
    audited = src + ("\n" + "\n".join(f"#print axioms {t}" for t in THEOREMS) + "\n").encode()
    (out / "EvolvingSafetyGate.lean").write_bytes(audited)
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
            "EvolvingSafetyGate.olean",
            "EvolvingSafetyGate.lean",
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
    chk = subprocess.run(
        [leanchecker, "--fresh", "EvolvingSafetyGate"],
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
        "format": "pcs-evolving-safety-gate-formal-v1",
        "source_sha256": digest(src),
        "staged_sha256": digest(audited),
        "olean_sha256": digest((out / "EvolvingSafetyGate.olean").read_bytes()),
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
