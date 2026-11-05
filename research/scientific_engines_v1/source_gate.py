"""Verify original archives, exact reviewable vendor patches and Lean admission tokens."""

import hashlib
import json
import tarfile
from pathlib import Path
from scripts.audit_lean_source import audit

HERE = Path(__file__).resolve().parent
ARCHIVES = {
    "prism": (
        "fadaaafa-ee52-4e4a-a694-a495af3a4d2d-aristotle.tar.gz",
        "ff9e943a46bc028b4c703c2ffb6241e8c260be3998f54edf4b22057a80e5ec65",
    ),
    "aion": (
        "734e0164-a4ae-43e4-bdc1-8b15a2be55d3-aristotle.tar.gz",
        "acc9faee21a28d256b03703f970f441c1c25ec1ce0d6678752833a66ee27656b",
    ),
}


def check():
    report = {}
    for engine, (name, sha) in ARCHIVES.items():
        p = HERE / "provenance" / name
        if hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            raise ValueError("Original archive changed")
        expected = {}
        with tarfile.open(p, "r:gz") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                path = Path(member.name)
                roots = (
                    {"PRISM", "python", "tests", "docs", "examples"}
                    if engine == "prism"
                    else {"RequestProject", "python", "tests", "docs", "certificates"}
                )
                if path.parts[0] not in roots and str(path) not in {
                    "README.md",
                    "lean-toolchain",
                    "lakefile.toml",
                    "lake-manifest.json",
                    "ARISTOTLE_SUMMARY.md",
                }:
                    continue
                data = archive.extractfile(member).read()
                if engine == "prism" and str(path) == "python/prism/lean_export.py":
                    data = data.replace(
                        b"max(len(o) for o in P.outcomes)",
                        b"max([1] + [len(o) for o in P.outcomes])",
                    )
                if engine == "aion" and str(path) in {
                    "RequestProject/AION/Examples/" + n + ".lean"
                    for n in ["BDcert", "GeneCert", "XYsmall", "XYmain"]
                }:
                    data = data.replace(b"by native_decide", b"by\n  decide +kernel")
                if engine == "aion" and str(path) == "python/aion/emit_lean.py":
                    data = data.replace(b"native_decide", b"decide +kernel")
                expected[path.as_posix()] = hashlib.sha256(data).hexdigest()
        root = HERE / "vendor" / engine
        actual = {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and ".lake" not in p.parts
        }
        if actual != expected:
            differences = sorted(
                k
                for k in actual.keys() | expected.keys()
                if actual.get(k) != expected.get(k)
            )
            raise ValueError("Unreviewed vendor delta: " + repr(differences))
        report[engine] = dict(archive_sha256=sha, vendor_files=len(actual))
    errors = audit(
        [
            HERE / "vendor/prism/PRISM",
            HERE / "vendor/aion/RequestProject",
            HERE / "formal",
        ]
    )
    if errors:
        raise ValueError("\n".join(errors))
    return dict(passed=True, archives=report, active_lean_escape_hatches=0)


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
