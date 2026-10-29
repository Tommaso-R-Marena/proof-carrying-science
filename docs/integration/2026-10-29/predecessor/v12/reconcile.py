"""Check the frozen PR census and reviewed byte/mode bindings without regenerating them.

The checked-in program and manifest are trusted review configuration. This does
not prove semantic equivalence, external validation, or immutable host storage.
Historical preservation gates remain unchanged and retain their original scope.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "docs/integration/2026-10-28/RECONCILIATION_V12.json"
MANIFEST_SHA256 = '28249984d163b54a48a0eb2e9edd5de0fc2844243c8140b7af9c28b39802b716'
API = "https://api.github.com/repos/Tommaso-R-Marena/proof-carrying-science/pulls?state=open&per_page=100"
WORKFLOW_PREDECESSOR_TREE = "1fdf12112394c1ad7438e2add4460fba8fd34da0"


def _json(raw):
    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("duplicate JSON key")
            result[name] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def _path(name):
    if (type(name) is not str or not name or "\\" in name or "\0" in name
            or PurePosixPath(name).is_absolute()
            or any(part in {"", ".", ".."} for part in name.split("/"))):
        raise ValueError("unsafe source path")
    return name


def _git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE)


def _identity(root, name):
    path = root
    for part in _path(name).split("/"):
        path /= part
        if path.is_symlink():
            raise ValueError("symlink source or source parent")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("regular source required")
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mode": "100755" if info.st_mode & 0o111 else "100644"}


def _historical_identities(root, prs):
    """Read immutable object IDs in one batch, avoiding thousands of processes."""
    trees, wanted = {}, {}
    for pr in prs:
        head = pr["head"]
        if not re.fullmatch("[0-9a-f]{40}", head):
            raise ValueError("exact commit identity required")
        if head not in trees:
            tree = {}
            for row in _git(root, "ls-tree", "-rz", head).split(b"\0"):
                if row:
                    meta, path = row.split(b"\t", 1)
                    mode, kind, oid = meta.decode().split()
                    tree[path.decode()] = mode, kind, oid
            trees[head] = tree
        for item in pr["files"]:
            name = _path(item["path"])
            mode, kind, oid = trees[head][name]
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise ValueError("historical regular source required")
            wanted[head, name] = mode, oid
    objects = sorted({oid for mode, oid in wanted.values()})
    process = subprocess.run(["git", "cat-file", "--batch"], cwd=root,
                             input=("\n".join(objects) + "\n").encode(),
                             capture_output=True, check=True)
    stream, hashes = io.BytesIO(process.stdout), {}
    for oid in objects:
        header = stream.readline().decode().strip().split()
        if len(header) != 3 or header[:2] != [oid, "blob"]:
            raise ValueError("historical Git object unavailable")
        size = int(header[2])
        raw = stream.read(size)
        if len(raw) != size or stream.read(1) != b"\n":
            raise ValueError("incomplete historical Git object")
        hashes[oid] = hashlib.sha256(raw).hexdigest()
    if stream.read(1):
        raise ValueError("unexpected historical Git output")
    return {key: {"mode": mode, "sha256": hashes[oid]} for key, (mode, oid) in wanted.items()}


def _verify(root, manifest):
    """Internal checker; the CLI accepts only the compiled-in manifest digest."""
    if manifest["format"] != "pcs-source-reconciliation-v12":
        raise ValueError("unsupported reconciliation")
    prs = manifest["prs"]
    numbers = [p["number"] for p in prs]
    if len(numbers) != len(set(numbers)) or len(prs) != 70:
        raise ValueError("incomplete or duplicate PR census")
    if [p["number"] for p in prs if p["disposition"] == "HELD"] != [117]:
        raise ValueError("explicit PR117 hold must remain")
    counts = Counter()
    tracked = set(_git(root, "ls-files", "-z").decode().split("\0"))
    historical_identities = _historical_identities(root, prs)
    differences = {}
    for pr in prs:
        if not all(re.fullmatch("[0-9a-f]{40}", pr[k]) for k in ("head", "base")):
            raise ValueError("exact commit identities required")
        pair = pr["base"], pr["head"]
        if pair not in differences:
            differences[pair] = set(_git(root, "diff", "--name-only", pair[0] + "..." + pair[1]).decode().splitlines())
        expected = differences[pair]
        entries = pr["files"]
        if {f["path"] for f in entries} != expected or len(entries) != len(expected):
            raise ValueError(f"PR{pr['number']} changed-path census differs")
        if pr["disposition"] == "REVIEWED_ADAPTATION" and not pr["review"]:
            raise ValueError("adaptation has no explicit review")
        for item in entries:
            source, target = _path(item["path"]), _path(item["location"])
            if historical_identities[pr["head"], source] != item["historical"]:
                raise ValueError("historical source identity differs")
            if target not in tracked or _identity(root, target) != item["candidate"]:
                raise ValueError(f"reviewed source identity differs: {target}")
            equal = item["historical"] == item["candidate"]
            if equal != (item["relation"] == "EXACT"):
                raise ValueError("source equality classification differs")
            if not equal and pr["disposition"] not in {"REVIEWED_ADAPTATION", "HELD"}:
                raise ValueError("unreviewed adaptation")
            counts[item["relation"]] += 1
    return {"format": "pcs-source-reconciliation-check-v12", "source_review_complete": True,
            "prs_checked": len(prs), "source_bindings_checked": sum(counts.values()),
            "relations": dict(counts), "dispositions": dict(Counter(p["disposition"] for p in prs)),
            "held_prs": [117], "release_ready": False, "pcs_authority": False,
            "semantic_equivalence_proved": False, "hosted_qualification": "NOT_ESTABLISHED_BY_THIS_CHECK"}


def _snapshot(root, manifest):
    """Pin the whole combined source tree, not just files touched by old PRs.

    Control sources are trusted checked-in configuration (as are workflow and
    verifier programs generally). They must be regular files identical to HEAD.
    No claim of protection against a host able to replace Git/programs is made.
    """
    controls = set(manifest["control_paths"])
    expected_controls = {
        MANIFEST, "research/integration_v2/__init__.py", "research/integration_v2/reconcile.py",
        "research/integration_v2/boundary.py", "research/integration_v2/test_reconcile.py",
    }
    if controls != expected_controls:
        raise ValueError("source control configuration allowlist differs")
    tracked = set(_git(root, "ls-files", "-z").decode().split("\0")) - {""}
    if tracked != set(manifest["snapshot"]) | controls:
        raise ValueError("combined tracked file census differs")
    for name, identity in manifest["snapshot"].items():
        if _identity(root, name) != identity:
            raise ValueError("combined source bytes or mode differ: " + name)
    for name in controls:
        _identity(root, name)


def workflow_successor(raw, *, update_python=False, update_codeql=False, pytest_context=False):
    """Only fixed dependency pins and named source-contract selection may vary."""
    from .boundary import PROFILES
    text = raw.decode("utf-8")
    if update_python:
        text = text.replace("actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
                        "actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0")
    if update_codeql:
        text = text.replace("6f2ac81f5cd81fe351a197ba0b00d91d03cd2aee",
                        "9b3254085494b55a0f7c4c2b3d2d52cc712ce370")
    def boundary(match):
        if match[1] not in PROFILES:
            raise ValueError("unknown predecessor preservation profile")
        return "python -m research.integration_v2.boundary " + match[1]
    text = re.sub(r"python -m (research\.[A-Za-z0-9_.]+\.preservation)\b", boundary, text)
    if pytest_context:
        text = text.replace("python -m pytest ", "python -m pytest -p research.integration_v2.pytest_phase_context ")
    return text.encode()


def _workflows(root, manifest):
    if manifest["workflow_predecessor_tree"] != WORKFLOW_PREDECESSOR_TREE:
        raise ValueError("workflow predecessor identity differs")
    for name, expected in manifest["workflow_adaptations"].items():
        if not name.startswith(".github/workflows/") or not name.endswith(".yml"):
            raise ValueError("unexpected workflow source")
        preserved = "docs/integration/2026-10-28/predecessor/workflows/" + name.rsplit("/", 1)[1]
        old = (root / preserved).read_bytes()
        if hashlib.sha256(old).hexdigest() != expected:
            raise ValueError("preserved predecessor workflow differs")
        contextual = name in {".github/workflows/pcs-" + profile + "-v1.yml" for profile in
                              ("local-weights", "causal-firewall", "relational-release", "compositional-disclosure")}
        allowed = {workflow_successor(old, update_python=p, update_codeql=c, pytest_context=t)
                   for p in (False, True) for c in (False, True)
                   for t in ((False, True) if contextual else (False,))}
        if (root / _path(name)).read_bytes() not in allowed:
            raise ValueError("workflow changes outside explicit source/pin replacements: " + name)


def check(*, require_committed=False, live=False):
    raw = (ROOT / MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("reconciliation manifest differs from fixed reviewed digest")
    manifest = _json(raw)
    result = _verify(ROOT, manifest)
    _snapshot(ROOT, manifest)
    _workflows(ROOT, manifest)
    if require_committed:
        if _git(ROOT, "diff", "--name-only", "HEAD").strip():
            raise ValueError("committed source required; staged/working changes remain")
        if _git(ROOT, "show", "HEAD:" + MANIFEST) != raw:
            raise ValueError("manifest must match committed HEAD")
        for name in manifest["control_paths"]:
            if _git(ROOT, "show", "HEAD:" + name) != (ROOT / name).read_bytes():
                raise ValueError("control source must match committed HEAD")
    if live:
        request = urllib.request.Request(API, headers={"User-Agent": "PCS-source-reconciliation"})
        with urllib.request.urlopen(request, timeout=30) as response:
            actual = _json(response.read(8 * 1024 * 1024 + 1))
            if response.headers.get("Link") and 'rel="next"' in response.headers["Link"]:
                raise ValueError("PR pagination exceeds frozen census")
        if {p["number"]: p["head"]["sha"] for p in actual} != {p["number"]: p["head"] for p in manifest["prs"]}:
            raise ValueError("live PR census changed; a new explicit review is required")
    return dict(result, committed_source_required=require_committed, live_heads_checked=live,
                manifest_sha256=MANIFEST_SHA256, whole_tree_files_checked=len(manifest["snapshot"]))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--require-committed", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(check(require_committed=args.require_committed, live=args.live), indent=2))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"source_review_complete": False, "release_ready": False,
                          "pcs_authority": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
