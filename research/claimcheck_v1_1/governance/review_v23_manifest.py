"""Independent check of the proposed V23 manifest against V22 and the commit to admit.  Read-only.

    python -m research.claimcheck_v1_1.governance.review_v23_manifest --emit DIR --head H

`DIR` is the directory written by `prepare_core_admission --emit DIR` at `H`.  This checks V23 with
code separate from the generator, against V22 read from the protected commit that introduced it:

  * format, and the predecessor record: V22's path, its SHA-256, and the commit that introduced it;
  * the PR census, superseded PRs, workflow adaptations, workflow predecessor tree, parent heads and
    protected-main fields are identical to V22's;
  * no V22 entry is removed, and exactly one V22 entry changes: `scripts/check_reconciled_prs.py`,
    which the control commit replaces;
  * every added entry is under an admitted root and has mode 100644, except V22 itself, now pinned as
    an ordinary file with its own digest;
  * every V23 entry equals the blob at `H`, except:
    * the gate script the control commit replaces;
    * the gate's one pinned test repair (`reconcile.py`, `RECEIVER_CLEANUP_*`);
    * if `H` carries it, G2's reviewed workflow successor. V23 keeps V22's identity for it, and the
      emitted `reconcile.py` must map exactly that identity to the new one (`SOURCE_POLICY_*`). The two
      digests are written here independently of the generator;
  * no file at `H` is missing from V23 other than the control paths.

Exits non-zero on the first violation.  Not an approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys

V22_PATH = "docs/integration/2026-11-05/RECONCILIATION_V22.json"
V22_COMMIT = "bc78660b5fac857fce3873eb6cda0445d1903da1"
V22_SHA256 = "28cc42a65a20f1d7697833d8a6ecca0f8cb37ac787f9eaeeb7ffc3686d26ce83"
V23_PATH = "docs/integration/2026-11-14/RECONCILIATION_V23.json"
ROOTS = ("research/claimcheck_v1/", "research/claimcheck_v1_1/", "docs/integration/claimcheck/", ".github/workflows/pcs-claimcheck-v1.yml")
GATE = "scripts/check_reconciled_prs.py"
REPAIR = "research/scientific_receiver_v1/tests/test_host.py"
REPAIR_OLD = "46916b52b9bfa2443a71ea106fd8fe891c626a1df5318eb347a65b6e1aa25a8a"
REPAIR_NEW = "1952bd78f5f9a787a5fd1617e45dd2c75fe9d4188e87535e017e2e72317b4aba"
UNCHANGED_FIELDS = ("prs", "superseded_closed_prs", "workflow_adaptations", "workflow_predecessor_tree", "parent_heads", "protected_main")
# G2 (owner, 2026-11-22: approved in principle, in C1): the one reviewed workflow successor
G2_WORKFLOW = ".github/workflows/pcs-public-full-verification.yml"
G2_OLD = "bb920a828812bcf3db3df4620b883a2595294db9dd9e64d11d4a0dc6b52567cf"
G2_NEW = "b4e6b4ef2aed4378557b3e44fba3dfddd872e68392844fd524f545de7e595d5a"


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--emit", required=True)
    ap.add_argument("--head", required=True)
    a = ap.parse_args(argv)
    if hashlib.sha256(git("show", f"{V22_COMMIT}:{V22_PATH}")).hexdigest() != V22_SHA256:
        raise SystemExit("V22 at its protected commit does not have the pinned digest")
    v22 = json.loads(git("show", f"{V22_COMMIT}:{V22_PATH}"))
    raw = open(f"{a.emit}/{V23_PATH}", "rb").read()
    v23 = json.loads(raw)
    report = {"v23_sha256": hashlib.sha256(raw).hexdigest(), "v23_entries": len(v23["snapshot"]), "head": git("rev-parse", a.head).decode().strip()}
    checks = {}
    checks["format_v23"] = v23.get("format") == "pcs-source-reconciliation-v23"
    checks["predecessor_is_v22_at_its_commit"] = v23.get("predecessor_manifest") == {"commit": V22_COMMIT, "path": V22_PATH, "sha256": V22_SHA256}
    checks["census_and_history_fields_unchanged"] = all(v23.get(k) == v22.get(k) for k in UNCHANGED_FIELDS)
    s22, s23 = v22["snapshot"], v23["snapshot"]
    checks["no_v22_entry_removed"] = not (set(s22) - set(s23))
    changed = sorted(k for k in s22 if s23.get(k) != s22[k])
    checks["exactly_one_v22_entry_changed_the_gate_script"] = changed == [GATE]
    added = sorted(set(s23) - set(s22))
    outside = [p for p in added if not p.startswith(ROOTS)]
    checks["added_entries_under_admitted_roots_except_v22"] = outside == [V22_PATH] and s23[V22_PATH]["sha256"] == V22_SHA256
    checks["added_entries_mode_100644"] = all(s23[p]["mode"] == "100644" for p in added)
    tree = {}
    for row in git("ls-tree", "-r", "-z", a.head).split(b"\0"):
        if row:
            meta, path = row.split(b"\t", 1)
            tree[path.decode()] = meta.decode().split()
    differ = []
    for p, e in s23.items():
        if p not in tree:
            differ.append(p)
            continue
        mode, _type, blob = tree[p]
        if mode != e["mode"] or hashlib.sha256(git("cat-file", "blob", blob)).hexdigest() != e["sha256"]:
            differ.append(p)
    g2 = hashlib.sha256(git("show", f"{a.head}:{G2_WORKFLOW}")).hexdigest() == G2_NEW
    expected_differ = sorted([GATE, REPAIR] + ([G2_WORKFLOW] if g2 else []))
    report["g2_workflow_successor_at_head"] = g2
    checks["entries_equal_head_except_gate_script_and_pinned_repair"] = (
        sorted(differ) == expected_differ and s23[REPAIR]["sha256"] == REPAIR_OLD
        and hashlib.sha256(git("show", f"{a.head}:{REPAIR}")).hexdigest() == REPAIR_NEW)
    if g2:
        emitted_gate = open(f"{a.emit}/research/integration_v2/reconcile.py", encoding="utf-8").read()
        checks["g2_successor_kept_at_v22_identity_and_bound_by_the_emitted_gate"] = (
            s23[G2_WORKFLOW] == {"sha256": G2_OLD, "mode": "100644"} and tree[G2_WORKFLOW][0] == "100644"
            and f'SOURCE_POLICY_OLD = "{G2_OLD}"' in emitted_gate and f'SOURCE_POLICY_NEW = "{G2_NEW}"' in emitted_gate)
    missing = sorted(set(tree) - set(s23) - set(v23["control_paths"]))
    checks["every_file_at_head_is_pinned_or_a_control"] = not missing
    checks["v23_is_a_control_and_v22_is_not"] = V23_PATH in v23["control_paths"] and V22_PATH not in v23["control_paths"]
    report.update({"added_entries": len(added), "control_paths": v23["control_paths"], "reviewer_field": v23.get("reviewer"),
                   "checks": checks, "consistent": all(checks.values())})
    if missing:
        report["files_at_head_not_pinned"] = missing[:20]
    if sorted(differ) != expected_differ:
        report["entries_differing_from_head"] = differ[:20]
    print(json.dumps(report, indent=1))
    return 0 if report["consistent"] else 1


if __name__ == "__main__":
    sys.exit(main())
