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
MANIFEST = "docs/integration/2026-10-29/RECONCILIATION_V20.json"
MANIFEST_SHA256 = '30d74b87c9bedb598af2cd6ab0c5d9014a99fe50cd6382bc6baf76663c380833'
API = "https://api.github.com/repos/Tommaso-R-Marena/proof-carrying-science/pulls?state=open&per_page=100"
# Exact reviewed source references for reconciling the held research branch.
# This adds a source rollback check; it does not release PR117 or grant authority.
PR117_RESEARCH_HEAD = "db1cacf5c750ee108c9d946f5ee0839a53be25f6"
PR117_PROTECTED_HEAD = "42bc851288b44cc72150e5251a19ec259b943e1f"
PR117_CONFLICT_PATHS = frozenset({
    ".github/workflows/pcs-proof-gated-research.yml",
    "formal/PCS/V2/ProofGatedArtifacts.lean",
    "formal/PCS/V2/ProofGatedAudit.lean",
    "formal/PCS/V2/ProofGatedInference.lean",
})
# One exact test-only successor: Linux /proc may raise ESRCH after child exit.
# The original V20 manifest/evidence stays frozen. Neither authority code nor
# arbitrary replacements are admitted by this narrowly pinned repair.
RECEIVER_CLEANUP_TEST = "research/scientific_receiver_v1/tests/test_host.py"
RECEIVER_CLEANUP_OLD = "46916b52b9bfa2443a71ea106fd8fe891c626a1df5318eb347a65b6e1aa25a8a"
RECEIVER_CLEANUP_NEW = "1952bd78f5f9a787a5fd1617e45dd2c75fe9d4188e87535e017e2e72317b4aba"

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


def _current_expected(name, recorded):
    """Bind the reviewed test repair without changing historical classifications."""
    if name != RECEIVER_CLEANUP_TEST:
        return recorded
    if recorded != {"sha256": RECEIVER_CLEANUP_OLD, "mode": "100644"}:
        raise ValueError("receiver cleanup repair predecessor identity differs")
    return {"sha256": RECEIVER_CLEANUP_NEW, "mode": "100644"}


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
    if manifest["format"] not in {"pcs-source-reconciliation-v12", "pcs-source-reconciliation-v13", "pcs-source-reconciliation-v14", "pcs-source-reconciliation-v15", "pcs-source-reconciliation-v16", "pcs-source-reconciliation-v17", "pcs-source-reconciliation-v18", "pcs-source-reconciliation-v19", "pcs-source-reconciliation-v20"}:
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
            if target not in tracked or _identity(root, target) != _current_expected(target, item["candidate"]):
                raise ValueError(f"reviewed source identity differs: {target}")
            equal = item["historical"] == item["candidate"]
            if equal != (item["relation"] == "EXACT"):
                raise ValueError("source equality classification differs")
            if not equal and pr["disposition"] not in {"REVIEWED_ADAPTATION", "HELD"}:
                raise ValueError("unreviewed adaptation")
            counts[item["relation"]] += 1
    return {"format": "pcs-source-reconciliation-check-v20", "source_review_complete": True,
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
        if _identity(root, name) != _current_expected(name, identity):
            raise ValueError("combined source bytes or mode differ: " + name)
    for name in controls:
        _identity(root, name)


def workflow_successor(raw, *, update_python=False, update_codeql=False, pytest_context=False, combined_source=False, transport_dependencies=False):
    """Only fixed dependency, source-contract and bootstrap transformations may vary."""
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
    if combined_source:
        needle = "      - name: Exercise disclosure-audit unit tests\n"
        if text.count(needle) != 1:
            raise ValueError("exact public CI source-step insertion point required")
        text = text.replace(needle, "      - name: Exact reviewed combined-source contract\n        run: python -m research.integration_v2.reconcile --require-committed\n" + needle)
    if transport_dependencies:
        needle = "          bash scripts/core_ci_cloudflare.sh\n"
        if text.count(needle) != 1:
            raise ValueError("exact full-core dependency insertion point required")
        text = text.replace(needle, "          source scripts/activate_lean_428.sh\n"
                            "          lake exe cache get\n"
                            "          PCS_REQUIRE_TRANSPORT_KERNEL=1 PCS_REQUIRE_TRANSPORT_TRACE_KERNEL=1 bash scripts/core_ci_cloudflare.sh\n")
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
        allowed = {workflow_successor(old, update_python=p, update_codeql=c, pytest_context=t, combined_source=extra, transport_dependencies=deps)
                   for p in (False, True) for c in (False, True)
                   for t in ((False, True) if contextual else (False,))
                   for extra in ((False, True) if name == ".github/workflows/pcs-public-full-verification.yml" else (False,))
                   for deps in ((False, True) if name == ".github/workflows/pcs-public-full-verification.yml" else (False,))}
        if (root / _path(name)).read_bytes() not in allowed:
            raise ValueError("workflow changes outside explicit source/pin replacements: " + name)


def _pr117_family(name):
    return (name.startswith("research/proof-gated-self-improvement-v1/")
            or (name.startswith("formal/PCS/V2/ProofGated") and name.endswith(".lean"))
            or name in PR117_CONFLICT_PATHS)


def _pr117_resolution(root, *, protected=PR117_PROTECTED_HEAD, research=PR117_RESEARCH_HEAD):
    """Reject stale conflict choices using real Git objects and the active files.

    The CLI fixes both refs above. Tests use real disposable Git histories, not
    mathematical/verifier verdicts. Existing full-tree and workflow checks still
    run; no historical receipt, manifest digest or source exception is changed.
    """
    if not all(re.fullmatch("[0-9a-f]{40}", ref) for ref in (protected, research)):
        raise ValueError("PR117 exact reference identities required")
    base = _git(root, "merge-base", protected, research).decode().strip()
    original = set(_git(root, "diff", "--name-only", base + "..." + research).decode().splitlines())
    if len(original) != 25:
        raise ValueError("PR117 original changed-path census differs")
    names = set(_git(root, "ls-tree", "-rz", "--name-only", protected).decode().split("\0")) - {""}
    family = original | {name for name in names if _pr117_family(name)}
    if not family <= names:
        raise ValueError("PR117 source missing from protected reference")
    tracked = set(_git(root, "ls-files", "-z").decode().split("\0")) - {""}
    if {name for name in tracked if _pr117_family(name)} != {name for name in names if _pr117_family(name)}:
        raise ValueError("PR117 proof/research family census differs")
    identities = _historical_identities(root, [
        dict(head=protected, files=[dict(path=name) for name in sorted(family)]),
        dict(head=research, files=[dict(path=name) for name in sorted(original)]),
    ])
    successors = {name for name in original
                  if identities[protected, name] != identities[research, name]}
    if successors != PR117_CONFLICT_PATHS:
        raise ValueError("PR117 reviewed successor census differs")
    for name in sorted(family):
        if name not in tracked or _identity(root, name) != identities[protected, name]:
            raise ValueError("PR117 protected source rollback or substitution: " + name)
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", protected, "HEAD"],
                              cwd=root, capture_output=True)
    if ancestor.returncode != 0:
        raise ValueError("PR117 integration must retain protected main ancestry")
    legacy = subprocess.run(["git", "merge-base", "--is-ancestor", research, "HEAD"],
                            cwd=root, capture_output=True)
    if legacy.returncode not in {0, 1}:
        raise ValueError("PR117 research ancestry cannot be checked")
    return dict(protected_reference=protected, original_research_reference=research,
                original_paths_checked=len(original), unchanged_original_paths=21,
                reviewed_successors=sorted(successors), proof_family_files_checked=len(family),
                protected_main_ancestry=True, original_research_ancestry=legacy.returncode == 0,
                release_ready=False, pcs_authority=False,
                scope="EXACT_PROTECTED_SOURCE_PRESERVATION_NOT_SEMANTIC_OR_HOST_SECURITY_PROOF")


def check(*, require_committed=False, live=False):
    raw = (ROOT / MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("reconciliation manifest differs from fixed reviewed digest")
    manifest = _json(raw)
    if manifest["format"] != "pcs-source-reconciliation-v20":
        raise ValueError("current combined admission requires explicit V20 format")
    result = _verify(ROOT, manifest)
    _snapshot(ROOT, manifest)
    _workflows(ROOT, manifest)
    pr117 = _pr117_resolution(ROOT)
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
                manifest_sha256=MANIFEST_SHA256, whole_tree_files_checked=len(manifest["snapshot"]),
                pr117_integration=pr117,
                relations_scope="FROZEN_V20_REVIEW_BEFORE_EXPLICIT_TEST_SUCCESSOR",
                reviewed_test_successor=dict(path=RECEIVER_CLEANUP_TEST,
                    old_sha256=RECEIVER_CLEANUP_OLD, new_sha256=RECEIVER_CLEANUP_NEW,
                    mode="100644", authority_code_changed=False,
                    reason="Accept ENOENT or ESRCH when a real child exits during /proc read"))


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
