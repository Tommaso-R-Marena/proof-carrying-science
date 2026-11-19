"""Audit of every file the ClaimCheck branch adds to the core repository (owner decision C1).

    python -m research.claimcheck_v1_1.governance.audit_admission --out docs/integration/claimcheck

Read-only.  For the files added between `origin/main` and HEAD it checks: that nothing outside the
admitted roots is added and nothing existing is changed; file modes; credentials (the values
configured for this project's model providers are compared in-process and never printed, plus
generic key formats); generated or unnecessary files; duplicates by digest; sizes; licences of the
bundled third-party documents; the frozen v1 digests; that protected control files equal `main`.
Every added file is also given a provenance class by an explicit path rule (an unclassified file is
a finding), and the third-party attribution index THIRD_PARTY_ATTRIBUTION.md is generated from the
recorded acquisition metadata and checked to be current: the bundled article texts are CC BY, which
requires attribution and an indication of changes (plain-text extraction; the deliberately altered
"mutated" and "injected" copies).
Writes ADMISSION_AUDIT.json and THIRD_PARTY_ATTRIBUTION.md and prints a summary.  A finding is
reported, never "fixed" here.
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


# Provenance: where each added file comes from, by an explicit rule.  First match wins; no match is a finding.
PROVENANCE = [
    (r"research/claimcheck_v1/benchmark/(dev|heldout)/[^/]+/article\.xml$",
     "third-party: article full text (JATS XML) as published, retrieved from Europe PMC; CC BY; source URL and SHA-256 in acquisition.json"),
    (r"research/claimcheck_v1/benchmark/(dev|heldout)/[^/]+/article\.txt$",
     "third-party, transformed: plain text extracted from article.xml by acquire.jats_to_text (tables, formulas and references omitted); CC BY"),
    (r"research/claimcheck_v1/benchmark/(dev|heldout)/[^/]+/article\.(mutated|injected)\.txt$",
     "third-party, deliberately altered by PCS (mutate.py: planted numeric errors; inject.py: appended hostile paragraphs) for adversarial testing; CC BY; not the authors' text"),
    (r"research/claimcheck_v1/benchmark/(dev|heldout)/[^/]+/[^/]+\.csv$",
     "third-party: data file as published on Zenodo/Dryad; CC0; source URL, SHA-256 and Zenodo MD5 in acquisition.json"),
    (r"research/claimcheck_v1/benchmark/(dev|heldout)/[^/]+/(document|acquisition|manifest)\.json$",
     "PCS record: acquisition metadata (citation, licences, URLs, digests, retrieval time)"),
    (r"research/claimcheck_v1/benchmark/(dev|heldout)/[^/]+/gold(\.mutated|\.injected)?\.json$",
     "PCS record: reference labels written before the run (frozen)"),
    (r"research/claimcheck_v1/benchmark/(dev|heldout)/SCREENING\.json$", "PCS record: document screening log"),
    (r"research/claimcheck_v1/benchmark/results/heldout/model_responses/",
     "generated by external model APIs during the frozen run (untrusted proposals; recorded with the request ledger in prefetch_ledger*.json)"),
    (r"research/claimcheck_v1/benchmark/results/dev/model_responses/",
     "generated by external model APIs during development (untrusted proposals; see docs/integration/claimcheck/MODEL_OUTPUT_LICENSING.md)"),
    (r"research/claimcheck_v1/benchmark/results/bundles/[^/]+/source\.txt$",
     "third-party copy inside a replay bundle: the article text the bundle was checked against (CC BY; see the document's attribution)"),
    (r"research/claimcheck_v1/benchmark/results/bundles/[^/]+/data\.csv$",
     "third-party copy inside a replay bundle: the data file the bundle was checked against (CC0)"),
    (r"research/claimcheck_v1/benchmark/results/bundles/[^/]+/ClaimCheck\.lean$",
     "PCS code: copy of the frozen Lean checker inside a replay bundle"),
    (r"research/claimcheck_v1/benchmark/results/",
     "generated by PCS: outputs of the frozen run, Lean kernel receipts, analyses and replay records (reproducible from the inputs and code)"),
    (r"research/claimcheck_v1_1/dev/results/", "generated by PCS: v1.1 development results (reproducible from the inputs and code)"),
    (r"research/claimcheck_v1/formal/ClaimCheck\.lean\.sha256$", "PCS record: SHA-256 of the frozen Lean checker"),
    (r"research/claimcheck_v1/formal/lean-toolchain$", "PCS configuration: pins the Lean version (leanprover/lean4, Apache-2.0, installed at build time)"),
    (r"research/claimcheck_v1/formal/lake-manifest\.json$",
     "PCS configuration: pins the Lean toolchain and Mathlib revisions (Mathlib, Apache-2.0, is fetched at build time, not vendored)"),
    (r"\.(py|lean|toml|yml|mjs|sh|html|css)$", "PCS code written for this project"),
    (r"\.(md|txt)$", "PCS documentation written for this project"),
    (r"\.(json|jsonl|csv|patch|diff|tsv)$", "PCS record or generated evidence (reproducible; see the producing script named in the file or its directory README)"),
]
LICENCE_DEEDS = {"cc by": "https://creativecommons.org/licenses/by/4.0/", "cc-zero": "https://creativecommons.org/publicdomain/zero/1.0/",
                 "cc0": "https://creativecommons.org/publicdomain/zero/1.0/"}


def provenance(path: str) -> str | None:
    for pattern, what in PROVENANCE:
        if re.search(pattern, path):
            return what
    return None


def attribution(head: str, added: list[str]) -> tuple[str, list[dict]]:
    """THIRD_PARTY_ATTRIBUTION.md from document.json and acquisition.json; and any missing attribution field."""
    rows, problems = [], []
    docs = sorted(p for p in added if re.fullmatch(r"research/claimcheck_v1/benchmark/[^/]+/[^/]+/document\.json", p))
    lines = ["# Third-party material in the ClaimCheck research sidecar", "",
             "Generated by `python -m research.claimcheck_v1_1.governance.audit_admission` from the acquisition records; "
             "do not edit by hand. The audit fails if this file is out of date.", "",
             "Each benchmark document is a published open-access article whose XML states CC BY 4.0, with its published data (CC0 1.0). "
             "The article text is used for research on checking reported statistics against data. Under CC BY the authors "
             "are credited below, the licence is linked, and changes are indicated:", "",
             "* `article.xml` is the article as retrieved from Europe PMC (unchanged). No figures or images are included.",
             "* `article.txt` and the `source.txt` copies in the replay bundles are a plain-text extraction "
             "(`acquire.jats_to_text`: title, abstract, body paragraphs and captions; tables, formula markup and references omitted).",
             "* `article.mutated.txt` and `article.injected.txt` are **deliberately altered by PCS** for adversarial testing "
             "(planted numeric errors; appended hostile paragraphs). They are not the authors' text and must not be cited as such.",
             "* The data files are copies of the published files (byte-identical; SHA-256 recorded). CC0 requires no attribution; "
             "the source is credited anyway.", "",
             "No endorsement by the authors or publishers is implied. The PCS code and records are not covered by these licences.", ""]
    for doc in docs:
        meta = json.loads(blob(head, doc))
        acq_path = doc.replace("document.json", "acquisition.json")
        acq = json.loads(blob(head, acq_path)) if acq_path in added else {}
        art, data = acq.get("article", {}), acq.get("dataset", {})
        xml_path = doc.replace("document.json", "article.xml")
        xml = blob(head, xml_path).decode("utf-8") if xml_path in added else ""
        licence_block = re.search(r"<license\b.*?</license>", xml, re.S)
        licence_urls = re.findall(r"https?://creativecommons\.org/licenses/[a-z-]+/[0-9.]+/", licence_block.group(0) if licence_block else "")
        stated = sorted({u.replace("http://", "https://") for u in licence_urls})
        copyright_line = re.search(r"<copyright-statement>(.*?)</copyright-statement>", xml, re.S)
        copyright_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", copyright_line.group(1))).replace("&amp;", "&").strip() if copyright_line else ""
        need = {"citation": meta.get("citation"), "article_doi": meta.get("article_doi"), "pmcid": meta.get("pmcid"),
                "article_license": meta.get("article_license"), "xml_url": art.get("xml_url"), "xml_sha256": art.get("xml_sha256"),
                "text_transformation": art.get("text_transformation"), "data_doi": data.get("doi"), "data_license": data.get("license"),
                "data_files": data.get("files"), "retrieved_utc": acq.get("retrieved_utc")}
        missing = [k for k, v in need.items() if not v]
        if stated != ["https://creativecommons.org/licenses/by/4.0/"]:
            missing.append("article.xml licence element stating exactly CC BY 4.0 (found: %s)" % (stated or "none"))
        if missing or str(meta.get("article_license")).lower() not in LICENCE_DEEDS or str(data.get("license")).lower() not in LICENCE_DEEDS:
            problems.append({"document": doc, "missing": missing})
            continue
        slug = doc.split("/")[-2]
        lines += [f"## {slug}", "",
                  f"* **Article:** {meta['citation']}",
                  f"* **DOI:** https://doi.org/{meta['article_doi']} · **PMCID:** {meta['pmcid']}",
                  f"* **Licence:** CC BY 4.0, {stated[0]} (as stated in the article's licence element)",
                  f"* **Copyright:** {copyright_text}" if copyright_text else "* **Copyright:** no copyright statement in the published XML; credit as cited above",
                  f"* **Retrieved:** {acq['retrieved_utc']} from {art['xml_url']} (SHA-256 `{art['xml_sha256']}`)",
                  f"* **Data:** {data.get('title', '')}, https://doi.org/{data['doi']} (Zenodo record {meta.get('zenodo_record', '')}); "
                  f"licence CC0 1.0, {LICENCE_DEEDS[str(data['license']).lower()]}",
                  "* **Files used:** " + ", ".join(f"`{f['stored_as']}`" for f in data["files"] if f.get("stored_as")), ""]
        rows.append({"document": slug, "doi": meta["article_doi"]})
    return "\n".join(lines).rstrip("\n") + "\n", problems


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

    unclassified = [p for p in added if provenance(p) is None]
    by_provenance = collections.Counter(provenance(p) for p in added if provenance(p))
    attribution_text, attribution_problems = attribution(head, added)
    out = ROOT / args.out
    attribution_file = "docs/integration/claimcheck/THIRD_PARTY_ATTRIBUTION.md"
    committed = subprocess.run(["git", "-C", str(ROOT), "show", f"{head}:{attribution_file}"], capture_output=True).stdout.decode("utf-8", "replace")
    attribution_current = committed == attribution_text
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
        "provenance": {"classes": dict(by_provenance.most_common()), "unclassified": unclassified,
                       "note": "an explicit path rule per class (PROVENANCE in this script); first match wins"},
        "attribution": {"file": attribution_file, "documents": len(re.findall(r"^## ", attribution_text, re.M)),
                        "problems": attribution_problems, "committed_file_is_current": attribution_current,
                        "third_party_software_vendored": "none found; Mathlib (Apache-2.0) is pinned in lake-manifest.json and fetched at build time"},
        "frozen_v1": {"freeze_check_exit": freeze.returncode, "output": freeze.stdout.strip()[-300:]},
        "protected_paths_changed": [p for p in protected_changed if p != ".github/workflows"],
        "workflow_changes": wf_changes,
    }
    report["all_clear"] = (not not_added and not outside and not exact_hits and not pattern_hits and not sensitive_names
                           and not generated and not report["modes"]["symlinks"] and not report["modes"]["submodules"]
                           and not licence_problems and freeze.returncode == 0 and not report["protected_paths_changed"]
                           and wf_changes == [".github/workflows/pcs-claimcheck-v1.yml"]
                           and not unclassified and not attribution_problems and attribution_current)
    out.mkdir(parents=True, exist_ok=True)
    (out / "THIRD_PARTY_ATTRIBUTION.md").write_text(attribution_text, encoding="utf-8")
    (out / "ADMISSION_AUDIT.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("head", "all_clear")} | {
        "added": len(added), "outside": len(outside), "changed": len(not_added), "configured_values_checked": len(secrets),
        "credential_hits": len(exact_hits), "pattern_hits": len(pattern_hits), "generated": len(generated),
        "duplicate_groups": len(dup_groups), "redundant_bytes": redundant, "large": len(large), "licence_problems": len(licence_problems),
        "executables": len(executables), "freeze_ok": freeze.returncode == 0, "protected_changed": report["protected_paths_changed"],
        "unclassified_provenance": len(unclassified), "attribution_problems": len(attribution_problems),
        "attribution_file_current": attribution_current}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
