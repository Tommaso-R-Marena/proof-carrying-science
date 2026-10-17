"""Owner-side native research authority build. Never called by proposal requests."""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FORMAL = ROOT / "formal"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_inventory():
    fence = json.loads((HERE / "ARISTOTLE_INTEGRATION_BOUNDARY.json").read_text())
    for name, expected in fence["formal_sources"].items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise ValueError(
                "Aristotle boundary changed; explicit requalification required: " + name
            )
    paths = [ROOT / name for name in fence["formal_sources"]] + [
        HERE / "authority/Bridge.lean",
        HERE / "authority/driver.c",
    ]
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}


def build(output):
    sources = source_inventory()
    version = subprocess.check_output(["lean", "--version"], text=True).strip()
    if not version.startswith("Lean (version 4.28.0,"):
        raise ValueError("Exact Lean 4.28.0 required")
    bwrap = Path("/usr/bin/bwrap")
    if not bwrap.is_file():
        raise ValueError("Bubblewrap required; no unisolated fallback")
    output = Path(output).resolve()
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    modules = [
        "ProofGatedSelfImprovement",
        "ProofGatedArtifacts",
        "ProofGatedPromotion",
        "ProofGatedInference",
    ]
    subprocess.run(
        ["lake", "build", *[f"PCS.V2.{m}" for m in modules]], cwd=FORMAL, check=True
    )
    with tempfile.TemporaryDirectory(prefix="pgsi-native-build-") as temp:
        temp = Path(temp)
        c = temp / "Bridge.c"
        obj = temp / "Artifacts.o"
        subprocess.run(
            [
                "lake",
                "env",
                "lean",
                "--root=" + str(HERE / "authority"),
                "-c",
                str(c),
                str(HERE / "authority/Bridge.lean"),
            ],
            cwd=FORMAL,
            check=True,
        )
        ir = FORMAL / ".lake/build/ir/PCS/V2"
        # Rename only the old CLI's C entry point; no formal declaration changes.
        subprocess.run(
            [
                "lake",
                "env",
                "leanc",
                "-O2",
                "-Dmain=pgsi_legacy_main",
                "-c",
                str(ir / "ProofGatedArtifacts.c"),
                "-o",
                str(obj),
            ],
            cwd=FORMAL,
            check=True,
        )
        prefix = Path(
            subprocess.check_output(["lean", "--print-prefix"], text=True).strip()
        )
        driver = temp / "Driver.o"
        subprocess.run(
            [
                "/usr/bin/cc",
                "-O2",
                "-I" + str(prefix / "include"),
                "-c",
                str(HERE / "authority/driver.c"),
                "-o",
                str(driver),
            ],
            check=True,
        )
        subprocess.run(
            [
                "lake",
                "env",
                "leanc",
                "-O2",
                str(c),
                str(driver),
                str(obj),
                *[str(ir / (m + ".c")) for m in modules if m != "ProofGatedArtifacts"],
                "-o",
                str(output / "pgsi-authority"),
            ],
            cwd=FORMAL,
            check=True,
        )
        generated = sha(c.read_bytes())
    subprocess.run(
        ["strip", "--strip-unneeded", str(output / "pgsi-authority")], check=True
    )
    if sources != source_inventory():
        raise ValueError("Source changed during build")
    manifest = {
        "format": "pgsi-native-authority-manifest-v1",
        "wire_version": "PGSI1",
        "binary_sha256": sha((output / "pgsi-authority").read_bytes()),
        "bwrap_sha256": sha(bwrap.read_bytes()),
        "lean_version": version,
        "sources": sources,
        "generated_bridge_c_sha256": generated,
        "kernel_proved_native_execution_correspondence": False,
    }
    raw = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    (output / "manifest.json").write_bytes(raw)
    return {
        "manifest_sha256": sha(raw),
        "binary_sha256": manifest["binary_sha256"],
        "lean_version": version,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    print(json.dumps(build(p.parse_args().output), sort_keys=True))
