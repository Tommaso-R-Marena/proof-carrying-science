"""Audit of every file the ClaimCheck branch adds to the core repository (owner decision C1).

    python -m research.claimcheck_v1_1.governance.audit_admission --out docs/integration/claimcheck

Read-only.  For the files added between `origin/main` and HEAD it checks: that nothing outside the
admitted roots is added and nothing existing is changed; file modes; credentials (the values
configured for this project's model providers are compared in-process and never printed, plus
generic key formats); generated or unnecessary files; duplicates by digest; sizes; licences of the
bundled third-party documents; the frozen v1 digests; that protected control files equal `main`.
Writes ADMISSION_AUDIT.json and prints a summary.  A finding is reported, never "fixed" here.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADMITTED_ROOTS = ("research/claimcheck_v1/", "research/claimcheck_v1_1/", "docs/integration/claimcheck/",
                  ".github/workflows/pcs-claimcheck-v1.yml")
PROTECTED = ("research/integration_v2", "scripts/check_reconciled_prs.py", "scripts/test_reconciled_prs.py",
             "docs/integration/2026-11-05", "formal", "pcs", ".github/workflows")
SECRETS_FILE = Path("/root/.pcs-secrets/providers.env")
PATTERNS = {
    "google_api_key": rb"AIza[0-9A-Za-z_\-]{35}",
    "openrouter_key": rb"sk-or-v1-[0-9a-f]{40,}",
    "anthropic_key": rb"sk-ant-[A-Za-z0-9_\-]{20,}",
    "openai_style_key": rb"\bsk-[A-Za-z0-9]{32,}\b",
    "github_token": rb"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{36}\b|github_pat_[A-Za-z0-9_]{50,}",
    "slack_token": rb"xox[abprs]-[A-Za-z0-9-]{10,}",
    "aws_access_key": rb"\bAKIA[0-9A-Z]{16}\b",
    "private_key_block": rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "bearer_header_with_value": rb"[Aa]uthorization:\s*Bearer\s+[A-Za-z0-9._\-]{20,}",
    "key_assignment_with_value": rb"(?i)\b(?:api[_-]?key|secret|token|password)\b[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-./+]{20,}[\"']",
}
GENERATED = re.compile(r"(^|/)(__pycache__|\.lake|\.pytest_cache|node_modules|\.mypy_cache)(/|$)|\.(pyc|pyo|olean|ilean|o|so|log|tmp)$|(^|/)\.DS_Store$")
SENSITIVE_NAMES = re.compile(r"(^|/)(\.env(\..*)?|\.netrc|credentials(\.json)?|id_rsa|id_ed25519|.*\.pem|.*\.key|.*\.p12)$", re.I)


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def blob(ref: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{path}"], check=True, capture_output=True).stdout


def configured_secret_values() -> dict[str, bytes]:
    out = {}
    if SECRETS_FILE.is_file():
        for line in SECRETS_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            value = value.strip().strip("'\"")
            if len(value) >= 12:
                out[name.strip().removeprefix("export ").strip()] = value.encode()
    return out


def role(path: str) -> str:
    if path.startswith("research/claimcheck_v1/benchmark/results/bundles/"):
        return "evidence bundles (replayable; receipts, data copies, obligation files)"
    if path.startswith("research/claimcheck_v1/benchmark/results/"):
        return "frozen-run results and analyses"
    if path.startswith("research/claimcheck_v1/benchmark/") and "/results/" not in path:
        return "benchmark inputs (third-party articles and data, labels, manifests)"
    if path.startswith("research/claimcheck_v1/formal/"):
        return "Lean checker and meaning theorems"
    if path.startswith("research/claimcheck_v1_1/dev/results/") or path.startswith("research/claimcheck_v1_1/adjudication/v1_discrepancies/"):
        return "v1.1 development results and prepared packages"
    if path.endswith((".py", ".lean", ".yml", ".mjs", ".sh")):
        return "code"
    return "documentation and records"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args(argv)
    head = git("rev-parse", "HEAD").strip()
    base = git("rev-parse", args.base).strip()
    changes = [line.split("\t", 1) for line in git("diff", "--name-status", "--no-renames", base, head).splitlines()]
    added = sorted(p for s, p in changes if s == "A")
    not_added = sorted(f"{s} {p}" for s, p in changes if s != "A")
    outside = [p for p in added if not p.startswith(ADMITTED_ROOTS)]
    tree = {}
    for line in git("ls-tree", "-r", head, "--", *sorted({p.split("/")[0] for p in added})).splitlines():
        meta, path = line.split("\t", 1)
        tree[path] = meta.split()
    modes = collections.Counter(tree[p][0] for p in added)
    executables = [p for p in added if tree[p][0] == "100755"]

    secrets = configured_secret_values()
    exact_hits, pattern_hits, digests, sizes = [], [], collections.defaultdict(list), {}
    by_role = collections.Counter()
    bytes_by_role = collections.Counter()
    for path in added:
        raw = blob(head, path)
        sizes[path] = len(raw)
        digests[hashlib.sha256(raw).hexdigest()].append(path)
        by_role[role(path)] += 1
        bytes_by_role[role(path)] += len(raw)
        for name, value in secrets.items():
            if value in raw:
                exact_hits.append({"path": path, "configured_variable": name})
        for name, pattern in PATTERNS.items():
            for m in re.finditer(pattern, raw):
                line_no = raw.count(b"\n", 0, m.start()) + 1
                pattern_hits.append({"path": path, "pattern": name, "line": line_no, "match_length": len(m.group(0)),
                                     "starts_with": m.group(0)[:4].decode("latin-1")})
    generated = [p for p in added if GENERATED.search(p)]
    sensitive_names = [p for p in added if SENSITIVE_NAMES.search(p)]
    dup_groups = [sorted(ps) for ps in digests.values() if len(ps) > 1]
    redundant = sum(sizes[g[0]] * (len(g) - 1) for g in dup_groups)
    dup_kinds = collections.Counter(Path(g[0]).name if all(Path(p).name == Path(g[0]).name for p in g) else "mixed names" for g in dup_groups)
    large = sorted(((p, sizes[p]) for p in added if sizes[p] > 1_000_000), key=lambda x: -x[1])

    licences, licence_problems = collections.Counter(), []
    for doc in sorted(p for p in added if re.fullmatch(r"research/claimcheck_v1/benchmark/[^/]+/[^/]+/document\.json", p)):
        meta = json.loads(blob(head, doc))
        art, dat = str(meta.get("article_license", "")).lower(), str(meta.get("data_license", "")).lower()
        licences[(art, dat)] += 1
        acq = doc.replace("document.json", "acquisition.json")
        if art not in ("cc by", "cc-by", "cc by 4.0") or dat not in ("cc-zero", "cc0", "cc by", "cc-by") or acq not in added:
            licence_problems.append({"document": doc, "article_license": art, "data_license": dat, "acquisition_record": acq in added})

    freeze = subprocess.run(["python", "-m", "research.claimcheck_v1.benchmark.freeze", "check"], cwd=ROOT, capture_output=True, text=True)
    protected_changed = [p for p in PROTECTED if subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", base, head, "--", p]).returncode != 0]
    # the one workflow this branch adds lives under .github/workflows; it must be the only change there
    wf_changes = [p for s, p in changes if p.startswith(".github/workflows/")]

    report = {
        "format": "pcs-claimcheck-admission-audit-v1", "head": head, "base": base,
        "census": {"added": len(added), "changed_or_deleted": not_added, "outside_admitted_roots": outside,
                   "by_role": dict(by_role), "bytes_by_role": dict(bytes_by_role), "bytes_total": sum(sizes.values())},
        "modes": {"counts": dict(modes), "executable_files": executables,
                  "symlinks": [p for p in added if tree[p][0] == "120000"], "submodules": [p for p in added if tree[p][0] == "160000"]},
        "credentials": {"configured_values_checked": len(secrets), "configured_value_found_in": exact_hits,
                        "generic_pattern_matches": pattern_hits, "files_with_sensitive_names": sensitive_names,
                        "note": "configured values were compared in memory; no value appears in this report"},
        "generated_or_unnecessary": generated,
        "duplicates": {"groups": len(dup_groups), "files_in_groups": sum(len(g) for g in dup_groups), "redundant_bytes": redundant,
                       "by_name": dict(dup_kinds.most_common(12))},
        "large_files_over_1MB": [{"path": p, "bytes": n} for p, n in large],
        "licences": {"documents": sum(licences.values()), "pairs": {f"{a} / {d}": n for (a, d), n in licences.items()},
                     "problems": licence_problems},
        "frozen_v1": {"freeze_check_exit": freeze.returncode, "output": freeze.stdout.strip()[-300:]},
        "protected_paths_changed": [p for p in protected_changed if p != ".github/workflows"],
        "workflow_changes": wf_changes,
    }
    report["all_clear"] = (not not_added and not outside and not exact_hits and not pattern_hits and not sensitive_names
                           and not generated and not report["modes"]["symlinks"] and not report["modes"]["submodules"]
                           and not licence_problems and freeze.returncode == 0 and not report["protected_paths_changed"]
                           and wf_changes == [".github/workflows/pcs-claimcheck-v1.yml"])
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "ADMISSION_AUDIT.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("head", "all_clear")} | {
        "added": len(added), "outside": len(outside), "changed": len(not_added), "configured_values_checked": len(secrets),
        "credential_hits": len(exact_hits), "pattern_hits": len(pattern_hits), "generated": len(generated),
        "duplicate_groups": len(dup_groups), "redundant_bytes": redundant, "large": len(large), "licence_problems": len(licence_problems),
        "executables": len(executables), "freeze_ok": freeze.returncode == 0, "protected_changed": report["protected_paths_changed"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
