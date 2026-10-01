from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_lake() -> str | None:
    found = shutil.which("lake")
    if found:
        return found
    name = "lake.exe" if sys.platform == "win32" else "lake"
    candidates = [
        Path.home() / ".elan" / "bin" / name,
        Path(os.environ.get("USERPROFILE", "")) / ".elan" / "bin" / name
        if os.environ.get("USERPROFILE")
        else None,
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return str(candidate)
    return None


def _build_lean_authority() -> Path:
    lake = _find_lake()
    if lake is None:
        raise SystemExit(
            "Lean authority is mandatory for the standalone verifier; install Lean/Lake first"
        )
    formal = ROOT / "formal"
    proc = subprocess.run(
        [lake, "build", "pcs-lean-authority"],
        cwd=formal,
        check=False,
    )
    if proc.returncode:
        raise SystemExit(proc.returncode)
    name = "pcs-lean-authority.exe" if sys.platform == "win32" else "pcs-lean-authority"
    built = formal / ".lake" / "build" / "bin" / name
    if not built.is_file():
        raise SystemExit(f"expected Lean authority executable not found: {built}")
    return built


def main() -> int:
    p = argparse.ArgumentParser(description="Build a single-file PCS v0.6 reviewer verifier with PyInstaller.")
    p.add_argument("-o", "--output", default="dist/pcs-verifier-v06")
    args = p.parse_args()
    if importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit("PyInstaller is required: python -m pip install -e '.[standalone]'")
    authority = _build_lean_authority()
    target = Path(args.output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    name = target.name
    work = ROOT / "build" / "pcs-verifier-v06"
    work.mkdir(parents=True, exist_ok=True)
    dist = target.parent
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--onefile", "--name", name,
        "--distpath", str(dist),
        "--workpath", str(work),
        "--specpath", str(work),
        "--collect-data", "pcs.schemas",
        "--add-binary", f"{authority}{os.pathsep}.",
        str(ROOT / "scripts" / "verifier_launcher.py"),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode:
        return proc.returncode
    built = dist / (name + (".exe" if sys.platform == "win32" else ""))
    if not built.exists():
        raise SystemExit(f"expected verifier artifact not found: {built}")
    manifest = {
        "format": "pcs-verifier-artifact-v1",
        "artifact": built.name,
        "sha256": sha256(built),
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "entrypoint": "pcs.verifier_entrypoint:main",
        "lean_authority_embedded": True,
        "lean_authority_sha256": sha256(authority),
        "lean_authority_protocol": "pcs-lean-authority-observations-v1",
    }
    manifest_path = built.with_name(built.name + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
