from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(argv, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(
            f"command failed ({p.returncode}): {argv!r}\n"
            f"stdout={p.stdout[-8000:]}\nstderr={p.stderr[-8000:]}"
        )
    return p


def resolve(root: Path) -> tuple[list[Path], str]:
    wheelhouse = root / "wheelhouse"
    wheelhouse.mkdir(parents=True, exist_ok=True)
    run([
        "python","-m","pip","download","--disable-pip-version-check",
        "--only-binary=:all:","--no-deps","--dest",str(wheelhouse),
        "--platform","manylinux2014_x86_64","--implementation","cp",
        "--python-version","312","--abi","cp312","orjson>=3.10,<4",
    ])
    x86 = sorted(wheelhouse.glob("orjson-*-x86_64*.whl"))
    if len(x86) != 1:
        raise RuntimeError(f"expected one x86 wheel, got {[x.name for x in x86]}")
    m = re.match(r"(?i)^orjson-([0-9][^-]*)-", x86[0].name)
    if not m:
        raise RuntimeError(f"cannot parse version from {x86[0].name}")
    version = m.group(1)
    run([
        "python","-m","pip","download","--disable-pip-version-check",
        "--only-binary=:all:","--no-deps","--dest",str(wheelhouse),
        "--platform","manylinux2014_aarch64","--implementation","cp",
        "--python-version","312","--abi","cp312",f"orjson=={version}",
    ])
    wheels = sorted(wheelhouse.glob("orjson-*.whl"))
    if len(wheels) != 2:
        raise RuntimeError(f"expected two wheels, got {[x.name for x in wheels]}")
    return wheels, version


def write_lock(root: Path, wheels: list[Path], version: str) -> Path:
    lines = [f"orjson=={version} \\"]
    for index, wheel in enumerate(wheels):
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        suffix = " \\" if index < len(wheels) - 1 else ""
        lines.append(f"    --hash=sha256:{digest}{suffix}")
    path = root / "requirements.lock"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def image_digest(tag: str) -> str:
    run(["docker","pull",tag])
    p = run(["docker","buildx","imagetools","inspect",tag])
    m = re.search(r"(?m)^Digest:\s+(sha256:[0-9a-f]{64})\s*$", p.stdout)
    if not m:
        raise RuntimeError("no digest from imagetools")
    return m.group(1)


def build(root: Path) -> dict[str, str]:
    wheels, version = resolve(root)
    write_lock(root, wheels, version)
    digest = image_digest("docker.io/library/python:3.12-slim-bookworm")
    ref = f"docker.io/library/python@{digest}"
    run(["docker","pull",ref])
    (root / "Dockerfile").write_text(
        f"FROM {ref}\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1\n"
        "COPY wheelhouse /wheelhouse\n"
        "COPY requirements.lock /requirements.lock\n"
        "RUN python -m pip install --no-compile --no-index "
        "--find-links=/wheelhouse --require-hashes -r /requirements.lock\n",
        encoding="utf-8",
    )
    run([
        "docker","build","--network=none","--no-cache","--pull=false",
        "--provenance=false","--sbom=false","-t","pcs-wheel-probe",str(root),
    ])
    observed = run([
        "docker","run","--rm","--network=none","pcs-wheel-probe",
        "python","-c","import orjson; print(orjson.__version__)",
    ]).stdout.strip()
    if observed != version:
        raise RuntimeError(f"installed {observed}, expected {version}")
    return {"version": version, "digest": digest}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["resolve", "build"])
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pcs-wheel-probe-") as td:
        root = Path(td)
        if args.stage == "resolve":
            wheels, version = resolve(root)
            print({"version": version, "wheels": [x.name for x in wheels]})
        else:
            print(build(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
