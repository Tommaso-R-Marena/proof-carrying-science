from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(argv, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(
            f"command failed ({p.returncode}): {argv!r}\n"
            f"stdout={p.stdout[-8000:]}\nstderr={p.stderr[-8000:]}"
        )
    return p


NUMPY_VERSION = "2.5.3"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pypi_release() -> dict:
    import json
    api = f"https://pypi.org/pypi/numpy/{NUMPY_VERSION}/json"
    with urllib.request.urlopen(api, timeout=60) as response:
        return json.load(response)


def wheel_candidate(release: dict, arch: str) -> dict:
    needle = f"manylinux_2_28_{arch}"
    candidates = [
        item
        for item in release.get("urls", [])
        if item.get("packagetype") == "bdist_wheel"
        and isinstance(item.get("filename"), str)
        and item["filename"].startswith(f"numpy-{NUMPY_VERSION}-")
        and "cp312-cp312" in item["filename"]
        and needle in item["filename"]
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected one wheel for {arch}, got {[x.get('filename') for x in candidates]}"
        )
    return candidates[0]


def download_arch_wheel(wheelhouse: Path, arch: str) -> Path:
    item = wheel_candidate(pypi_release(), arch)
    target = wheelhouse / item["filename"]
    with urllib.request.urlopen(item["url"], timeout=120) as response:
        target.write_bytes(response.read())
    expected = item.get("digests", {}).get("sha256")
    observed = _sha256(target)
    if observed != expected:
        raise RuntimeError(
            f"PyPI digest mismatch for {target.name}: expected={expected} observed={observed}"
        )
    return target


def resolve(root: Path) -> tuple[list[Path], str]:
    wheelhouse = root / "wheelhouse"
    wheelhouse.mkdir(parents=True, exist_ok=True)
    wheels = sorted(
        [
            download_arch_wheel(wheelhouse, "x86_64"),
            download_arch_wheel(wheelhouse, "aarch64"),
        ]
    )
    return wheels, NUMPY_VERSION

def write_lock(root: Path, wheels: list[Path], version: str) -> Path:
    lines = [f"numpy=={version} \\"]
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
        "python","-c","import numpy; print(numpy.__version__)",
    ]).stdout.strip()
    if observed != version:
        raise RuntimeError(f"installed {observed}, expected {version}")
    return {"version": version, "digest": digest}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["api", "x86", "arm", "resolve", "build"])
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pcs-wheel-probe-") as td:
        root = Path(td)
        if args.stage == "api":
            release = pypi_release()
            print({"urls": len(release.get("urls", []))})
        elif args.stage == "x86":
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()
            wheel = download_arch_wheel(wheelhouse, "x86_64")
            print({"wheel": wheel.name, "sha256": _sha256(wheel)})
        elif args.stage == "arm":
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()
            wheel = download_arch_wheel(wheelhouse, "aarch64")
            print({"wheel": wheel.name, "sha256": _sha256(wheel)})
        elif args.stage == "resolve":
            wheels, version = resolve(root)
            print({"version": version, "wheels": [x.name for x in wheels]})
        else:
            print(build(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
