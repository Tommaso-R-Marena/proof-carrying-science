"""Validate committed dependency pins and source inputs before using build caches.

This detects mismatched revisions/dirty tracked source, not forged build objects.
The compiler, Git implementation and downloaded/preexisting oleans remain trusted.
"""

import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib


REPOSITORY = Path(__file__).resolve().parents[2]
MATHLIB_REVISION = "8f9d9cff6bd728b17a24e163c9402775d9e6a365"


def dependency_pins(project: Path) -> dict:
    local = json.loads((project / "lake-manifest.json").read_text())
    root = json.loads((REPOSITORY / "lake-manifest.json").read_text())
    expected = {package["name"]: package for package in root["packages"] if package["type"] == "git"}
    packages = local["packages"]
    if (len(packages) != len(expected) or any(package["type"] != "git" for package in packages)
            or {package["name"] for package in packages} != set(expected)):
        raise RuntimeError("Standalone dependency set differs from committed root manifest")
    for package in packages:
        baseline = expected[package["name"]]
        if (not re.fullmatch("[0-9a-f]{40}", package["rev"])
                or any(package[field] != baseline[field] for field in (
                    "rev", "url", "subDir", "configFile", "scope", "manifestFile", "inherited"))
                or package["inputRev"] != (MATHLIB_REVISION if package["name"] == "mathlib" else baseline["inputRev"])):
            raise RuntimeError("Standalone dependency differs from root pin: " + package["name"])
    config = tomllib.loads((project / "lakefile.toml").read_text())
    if (local["packagesDir"] != ".lake/packages" or local["lakeDir"] != ".lake"
            or local["name"] != config["name"]):
        raise RuntimeError("Unexpected standalone manifest identity or cache paths")
    require = config["require"]
    if (len(require) != 1 or require[0]["name"] != "mathlib"
            or require[0]["rev"] != MATHLIB_REVISION
            or expected["mathlib"]["rev"] != MATHLIB_REVISION
            or require[0]["git"] != expected["mathlib"]["url"]):
        raise RuntimeError("Exact Mathlib revision must be pinned in project and both manifests")
    return {package["name"]: package["rev"] for package in packages}


def verify_cache(cache_root: Path, pins: dict) -> list[Path]:
    libraries = []
    for name, revision in sorted(pins.items()):
        directory = cache_root.resolve() / ".lake" / "packages" / name
        top = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=directory, text=True).strip()
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"],
                                        cwd=directory, text=True).strip()
        flags = subprocess.check_output(["git", "ls-files", "-v"], cwd=directory, text=True).splitlines()
        if (Path(top).resolve() != directory.resolve() or actual != revision or dirty
                or any(line[0].islower() or line.startswith("S ") for line in flags)):
            raise RuntimeError("Dependency revision/source mismatch: " + name)
        library = directory / ".lake" / "build" / "lib" / "lean"
        if library.is_dir():
            libraries.append(library)
        # A pinned package need not be imported by this library (e.g. Cli).
        # Lean itself rejects any actually needed missing import artifact.
        print(f"verified_cache_source {name} {revision}", flush=True)
    return libraries


def audit_project_sources(project: Path) -> list[Path]:
    # Reuse the existing parser, without changing its authority/source gate.
    sys.path.insert(0, str(REPOSITORY))
    from scripts.audit_lean_source import audit

    names = subprocess.check_output(["git", "ls-files", "-z", "--", "*.lean"], cwd=project).decode().split("\0")
    sources = [project / name for name in names if name]
    if not sources or any(not source.is_file() or source.is_symlink() for source in sources):
        raise RuntimeError("Tracked regular Lean sources required")
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all", "--", "*.lean"],
                                    cwd=project, text=True).strip()
    flags = subprocess.check_output(["git", "ls-files", "-v", "--", "*.lean"], cwd=project, text=True).splitlines()
    if dirty or any(line[0].islower() or line.startswith("S ") for line in flags):
        raise RuntimeError("Project Lean sources are dirty or untracked")
    findings = audit(sources)
    if findings:
        raise RuntimeError("Project source admission audit failed:\n" + "\n".join(findings))
    print(f"tracked_clean_admission_free_project_sources {len(sources)}", flush=True)
    return sources
