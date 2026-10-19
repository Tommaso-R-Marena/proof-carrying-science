"""Freshly check the isolated scientific/history join; never write import caches.

Default mode uses Lake. Explicit direct mode uses operator-supplied source-identical
prebuilt imports. Git, Lean/compiler/runtime, qualification evidence and cached
object-to-source correspondence remain trusted; hashes are not authentication.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parent / "formal"
ALLOWED = {"propext", "Classical.choice", "Quot.sound"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", type=Path, required=True)
    parser.add_argument("--dependency-checkout", type=Path)
    parser.add_argument("--receiver-qualification", type=Path)
    parser.add_argument("--history-checkout", type=Path)
    args = parser.parse_args()
    direct = [args.dependency_checkout, args.receiver_qualification, args.history_checkout]
    if any(direct) and not all(direct):
        parser.error("direct mode requires all three cache/checkout arguments")
    lean = args.lean.absolute()
    version = subprocess.check_output([str(lean), "--version"], text=True, cwd=PROJECT)
    if "version 4.28.0," not in version:
        raise RuntimeError("Lean 4.28.0 required")
    sys.path.insert(0, str(ROOT))
    from scripts.audit_lean_source import audit
    sources = sorted(PROJECT.rglob("*.lean"))
    sources = [p for p in sources if ".lake" not in p.relative_to(PROJECT).parts]
    findings = audit(sources)
    if findings:
        raise RuntimeError("forbidden formal source: " + repr(findings))
    manifests = [json.loads((p / "lake-manifest.json").read_text()) for p in
                 (ROOT, PROJECT, ROOT / "research/scientific_receiver_v1/formal",
                  ROOT / "research/authorization_history_v1/formal")]
    pinsets = [{p["name"]: p["rev"] for p in m["packages"] if p["type"] == "git"}
               for m in manifests]
    git_counts = [sum(p["type"] == "git" for p in m["packages"]) for m in manifests]
    if git_counts != [9] * 4 or len(pinsets[0]) != 9 or any(pins != pinsets[0] for pins in pinsets[1:]):
        raise RuntimeError("all four manifests must agree on the nine Git revisions")
    pinned = [*sources, PROJECT / "lakefile.toml", PROJECT / "lake-manifest.json",
              PROJECT / "lean-toolchain", Path(__file__)]
    before = {str(p.relative_to(ROOT)): sha(p) for p in pinned}
    output = PROJECT / ".lake/build/lib/lean"
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    evidence = {"mode": "Lake build", "fresh_dependency_rebuild_claimed": False}
    if all(direct):
        from research.authorization_history_v1.formal_inputs import verify_cache
        base = args.dependency_checkout.resolve()
        libraries = verify_cache(base, pinsets[0])
        scopes = ("formal", "research/integration_v1/formal",
                  "incubation/pcs_certified_numerics_v1", "incubation/pcs_conservation_algebra_v1")
        for name in subprocess.check_output(["git", "ls-files", "--", *scopes], cwd=ROOT,
                                            text=True).splitlines():
            if sha(ROOT / name) != sha(base / name):
                raise RuntimeError("baseline import source differs: " + name)
        history = args.history_checkout.resolve() / "research/authorization_history_v1/formal"
        for path in (ROOT / "research/authorization_history_v1/formal").rglob("*.lean"):
            relative = path.relative_to(ROOT / "research/authorization_history_v1/formal")
            if ".lake" not in relative.parts and sha(path) != sha(history / relative):
                raise RuntimeError("history import source differs: " + str(relative))
        qualification = args.receiver_qualification.resolve()
        q = json.loads((qualification / "qualification.json").read_text())
        for name, expected in q["source_sha256"].items():
            if name.startswith("research/scientific_receiver_v1/formal/") and sha(ROOT / name) != expected:
                raise RuntimeError("qualified receiver source differs: " + name)
        manifest = qualification / "module-artifacts.json"
        if sha(manifest) != q["module_artifacts_sha256"]:
            raise RuntimeError("receiver artifact manifest differs")
        artifacts = json.loads(manifest.read_text())["artifacts"]
        for artifact in artifacts:
            if artifact["module"].startswith("PCSScientificReceiver") and sha(Path(artifact["path"])) != artifact["sha256"]:
                raise RuntimeError("receiver import object differs: " + artifact["path"])
        roots = [output, qualification / "fresh-lean", history / ".lake/build/lib/lean",
                 *(base / scope / ".lake/build/lib/lean" for scope in scopes[1:]),
                 base / "formal/.lake/build/lib/lean", *libraries]
        env["LEAN_PATH"] = os.pathsep.join(map(str, roots))
        command = [str(lean)]
        for name in ("PCSScientificHistoryV1/Join", "PCSScientificHistoryV1/Fixtures", "PCSScientificHistoryV1"):
            target = output / (name + ".olean")
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([*command, "-o", str(target), name + ".lean"], cwd=PROJECT, env=env, check=True)
        evidence = {"mode": "fresh join with read-only prebuilt imports",
                    "fresh_dependency_rebuild_claimed": False,
                    "receiver_qualification_sha256": sha(qualification / "qualification.json"),
                    "source_identity_checked": True}
    else:
        subprocess.run(["lake", "build", "PCSScientificHistoryV1"], cwd=PROJECT, env=env, check=True)
        command = ["lake", "env", "lean"]
    result = subprocess.run([*command, str(PROJECT / "Audit.lean")], cwd=PROJECT, env=env,
                            capture_output=True, text=True, check=True)
    text = result.stdout + result.stderr
    (output / "statements-and-axioms.log").write_text(text)
    closures = {n: sorted(set(re.findall(r"[A-Za-z_.]+", a))) for n, a in
                re.findall(r"'([^']+)' depends on axioms: \[([^]]*)\]", text, re.S)}
    closures.update({n: [] for n in re.findall(r"'([^']+)' does not depend on any axioms", text)})
    expected = {"PCSScientificHistoryV1." + name for p in sources for name in
                re.findall(r"^theorem (\w+)", p.read_text(), re.M)}
    authored = len(expected)
    if not expected <= closures.keys() or any(set(a) - ALLOWED for a in closures.values()):
        raise RuntimeError("incomplete or unapproved theorem axiom audit")
    if before != {str(p.relative_to(ROOT)): sha(p) for p in pinned}:
        raise RuntimeError("new source changed during checking")
    report = {"format": "pcs-scientific-history-formal-v1", "lean_version": version.strip(),
              "lean_sha256": sha(lean), "sources": before, "dependency_revisions": pinsets[0],
              "imports": evidence, "axiom_closures": dict(sorted(closures.items())),
              "authored_theorems": authored, "theorems_including_generated": len(closures),
              "scientific_acceptance": False, "production_authority": False}
    (output / "formal-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"authored_theorems": authored, "audited": len(closures), "status": "PASS"}))


if __name__ == "__main__":
    main()
