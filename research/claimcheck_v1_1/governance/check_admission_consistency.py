"""Check that the committed admission evidence is mutually consistent.  Read-only; creates no ref.

    python -m research.claimcheck_v1_1.governance.check_admission_consistency [--evidence docs/integration/claimcheck]

The dry run (`prepare_core_admission`), the census and the audit are generated at one source commit
S and committed in a following commit that changes only them.  This program checks, independently of
the scripts that wrote them:

  1. the dry run, the census and the audit name the same commit S, and all report success;
  2. every file in the census has, at S, exactly the identity (SHA-256, mode) the census records, and
     the census adds exactly the files that are in S's tree and not in V22 (no more, no fewer);
  3. the patch applies cleanly to S's three control files and yields exactly the digests the dry run
     records for the proposed control commit;
  4. the patched gate pins the proposed V23 digest; the patched retained-source entry names the
     retained commit and the proposed tag; the patched gate test pins V22 and its commit;
  5. the retained commit recorded in the dry run is reproducible from S (same tree, same parents,
     fixed identity, date and messages, in the design the dry run records: H1-b `clean` or H1-a
     `development`), using `git commit-tree`, which writes objects but no ref;
  6. HEAD is S, or differs from S only in the evidence files.

It does not regenerate V23 (4.7 MB): `prepare_core_admission --emit DIR` does, and its digest must equal
the one recorded.  Not an approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EDITED = ("research/integration_v2/reconcile.py", "research/integration_v2/test_reconcile.py", "scripts/check_reconciled_prs.py")
V22 = "docs/integration/2026-11-05/RECONCILIATION_V22.json"
V23 = "docs/integration/2026-11-14/RECONCILIATION_V23.json"


def git(*args, raw=False, env=None):
    out = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=True, env={**os.environ, **(env or {})}).stdout
    return out if raw else out.decode().strip()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--evidence", default="docs/integration/claimcheck")
    args = ap.parse_args(argv)
    ev = ROOT / args.evidence
    dry = json.loads((ev / "dry-run.json").read_text(encoding="utf-8"))
    census = json.loads((ev / "ADMISSION_CENSUS.json").read_text(encoding="utf-8"))
    audit = json.loads((ev / "ADMISSION_AUDIT.json").read_text(encoding="utf-8"))
    from research.claimcheck_v1_1.governance import prepare_core_admission as prep
    s = dry["generated_from_commit"]
    checks = {}
    # 1
    checks["same_commit"] = s == census["generated_from_commit"] == audit["head"]
    checks["all_reported_success"] = dry.get("all_as_expected") is True and audit.get("all_clear") is True
    # 2
    files = census["files"]
    tree = {}
    for row in git("ls-tree", "-r", "-z", s, raw=True).split(b"\0"):
        if row:
            meta, path = row.split(b"\t", 1)
            tree[path.decode()] = meta.decode().split()
    wrong = [n for n, ident in files.items()
             if n not in tree or tree[n][0] != ident["mode"] or sha(git("cat-file", "blob", tree[n][2], raw=True)) != ident["sha256"]]
    v22 = json.loads(git("show", f"{s}:{V22}", raw=True))
    expected_added = sorted(set(tree) - set(v22["snapshot"]) - set(v22["control_paths"]))
    checks["census_identities_match_the_commit"] = not wrong
    checks["census_is_exactly_the_added_files"] = sorted(files) == expected_added and dry["files_added"] == len(files) == audit["census"]["added"]
    # 3 and 4
    proposal = dry["proposal"]["control_commit_files"]
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        subprocess.run(["git", "init", "-q", str(t)], check=True)
        for name in EDITED:
            (t / name).parent.mkdir(parents=True, exist_ok=True)
            (t / name).write_bytes(git("show", f"{s}:{name}", raw=True))
        applied = subprocess.run(["git", "-C", str(t), "apply", str(ev / "proposed-control-changes.patch")], capture_output=True, text=True)
        checks["patch_applies_to_the_commit"] = applied.returncode == 0
        patched = {name: (t / name).read_bytes() for name in EDITED}
    checks["patched_files_have_the_proposed_digests"] = all(sha(patched[n]) == proposal[n]["sha256"] for n in EDITED)
    retained = dry["proposed_retained_source_commit"]
    gate_text, gate_test, retained_text = (patched[n].decode() for n in EDITED)
    checks["gate_pins_the_proposed_v23_digest"] = (f"MANIFEST_SHA256 = '{dry['proposal']['successor_manifest']['sha256']}'" in gate_text
                                                   and f'MANIFEST = "{V23}"' in gate_text
                                                   and proposal[V23]["sha256"] == dry["proposal"]["successor_manifest"]["sha256"])
    checks["retained_entry_names_the_retained_commit_and_tag"] = f"('{retained['commit']}','{retained['proposed_tag']}')" in retained_text
    checks["gate_test_pins_v22_and_its_commit"] = (prep.V22_SHA256 in gate_test and prep.V22_COMMIT in gate_test
                                                   and "def test_v23_keeps_v22_and_only_adds_the_claimcheck_sidecar" in gate_test)
    # 5
    again = prep.retained_commit(ROOT, s, retained.get("history", "development"))
    checks["retained_commit_reproducible"] = (again["commit"] == retained["commit"] and again["parents"] == retained["parents"]
                                              and retained["tree"] == git("rev-parse", f"{s}^{{tree}}") and retained.get("tag_created") is False
                                              and again.get("snapshot") == retained.get("snapshot"))
    # 6
    head = git("rev-parse", "HEAD")
    since = sorted(set(git("diff", "--name-only", s, head).splitlines()) - {""})
    checks["head_is_the_commit_or_differs_only_in_evidence"] = head == s or set(since) <= prep.EVIDENCE
    report = {"source_commit": s, "head": head, "files_since_source_commit": since, "census_files": len(files),
              "v23_sha256": dry["proposal"]["successor_manifest"]["sha256"], "retained_commit": retained["commit"],
              "retained_history": retained.get("history", "development"),
              "proposed_tag": retained["proposed_tag"], "checks": checks, "consistent": all(checks.values())}
    if wrong:
        report["census_files_that_differ"] = wrong[:20]
    print(json.dumps(report, indent=1))
    return 0 if report["consistent"] else 1


if __name__ == "__main__":
    sys.exit(main())
