from __future__ import annotations

import argparse
import hashlib
import json
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


def main() -> int:
    p = argparse.ArgumentParser(description="Build a single-file PCS v0.6 reviewer verifier with PyInstaller.")
    p.add_argument("-o", "--output", default="dist/pcs-verifier-v06")
    args = p.parse_args()
    if shutil.which("pyinstaller") is None:
        raise SystemExit("PyInstaller is required: python -m pip install -e '.[standalone]'")
    target = Path(args.output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    name = target.name
    work = ROOT / "build" / "pcs-verifier-v06"
    dist = target.parent
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--onefile", "--name", name,
        "--distpath", str(dist),
        "--workpath", str(work),
        "--specpath", str(work),
        str(ROOT / "pcs" / "verifier_entrypoint.py"),
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
    }
    manifest_path = built.with_name(built.name + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
