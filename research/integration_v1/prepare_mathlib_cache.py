"""Share this checkout's verified dependency cache between isolated Lake projects.

This is a build optimization, not executable attestation or an immutable root.
Every dependency must have the exact committed revision and clean tracked source.
"""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def prepare(project: Path):
    project = project.resolve()
    project.relative_to(ROOT)  # Only this checkout's projects.
    pins = json.loads((ROOT / "lake-manifest.json").read_text())
    expected = {p["name"]: p["rev"] for p in pins["packages"] if p["type"] == "git"}
    local = json.loads((project / "lake-manifest.json").read_text())
    for dependency in local["packages"]:
        if dependency["type"] == "git" and expected.get(dependency["name"]) != dependency["rev"]:
            raise RuntimeError("isolated project dependency differs from root pin")
    cache = ROOT / ".lake/packages"
    for name, revision in expected.items():
        directory = cache / name
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"],
                                        cwd=directory, text=True).strip()
        if actual != revision or dirty:
            raise RuntimeError("dependency source mismatch: " + name)
    destination = project / ".lake/packages"
    destination.parent.mkdir(exist_ok=True)
    if destination.exists() or destination.is_symlink():
        if destination.resolve() != cache.resolve():
            raise RuntimeError("existing isolated cache differs; refusing to overwrite")
    else:
        destination.symlink_to(cache, target_is_directory=True)
    return {"project": project.relative_to(ROOT).as_posix(), "exact_dependency_revisions": expected,
            "build_cache_only": True, "immutable_trust_root": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    print(json.dumps(prepare(parser.parse_args().project), indent=2))
