"""Independently check Aristotle source identity, source windows and kernel axioms.

Foreign runtime files are checked against receiver-selected checkouts when supplied.
Otherwise their committed snapshots are checked: that mode does not establish the
identity of a current website or CertiForge checkout. No uploaded log authorizes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_lean_source import audit
from verify_omega_dd_formal import check_inventory

EVIDENCE = ROOT / "research/aristotle-runtime-refinement-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_window(snapshot: bytes, actual: bytes, start: int, stop: int):
    """Exact inclusive one-based lines; changes outside the certified window are allowed."""
    left, right = snapshot.split(b"\n"), actual.split(b"\n")
    if not 1 <= start <= stop <= min(len(left), len(right)):
        raise ValueError("source window outside file")
    if left[start - 1:stop] != right[start - 1:stop]:
        raise ValueError(f"source extraction window changed: lines {start}–{stop}")
    return hashlib.sha256(b"\n".join(right[start - 1:stop])).hexdigest()


def check_sources(components):
    manifest = json.loads((EVIDENCE / "imported-sources.json").read_text())
    for item in manifest["files"]:
        if sha(ROOT / item["path"]) != item["sha256"]:
            raise ValueError("imported proof/reference source changed: " + item["path"])
    binding = json.loads((EVIDENCE / "runtime-bindings.json").read_text())
    for path, expected in binding["local_sources"].items():
        if sha(ROOT / path) != expected:
            raise ValueError("local formal environment or parser identity changed: " + path)
    windows = []
    for item in binding["source_windows"]:
        snapshot = ROOT / item["snapshot"]
        component = components.get(item["component"])
        actual = component / item["source"] if component else snapshot
        for start, stop in item["windows"]:
            windows.append({"component": item["component"], "source": item["source"],
                            "lines": [start, stop], "sha256": check_window(snapshot.read_bytes(), actual.read_bytes(), start, stop),
                            "current_checkout_checked": component is not None})
    return windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path)
    parser.add_argument("--certiforge", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    windows = check_sources({"proof-carrying-science": ROOT,
                             "proof-carrying-science-site": args.site, "certiforge": args.certiforge})
    manifest = json.loads((EVIDENCE / "imported-sources.json").read_text())
    paths = [ROOT / f["path"] for f in manifest["files"] if f["path"].endswith(".lean")]
    findings = audit(paths)
    if findings:
        raise ValueError("\n".join(findings))
    driver = ROOT / "formal/tools/PrintPrincipalAxioms.lean"
    names = re.findall(r"^#print axioms (\S+)$", driver.read_text(), re.M)
    proc = subprocess.run(["lake", "env", "lean", str(driver)], cwd=ROOT / "formal",
                          text=True, capture_output=True, timeout=600)
    if proc.returncode:
        raise RuntimeError(proc.stdout + proc.stderr)
    axioms = check_inventory(proc.stdout, names)
    report = {"format": "pcs-runtime-refinement-integration-v1", "proof_sources": len(paths),
              "kernel_checked_inventory": axioms, "source_windows": windows,
              "conditional_runtime_refinements_proved": False, "parser_source_refinement_proved": False,
              "rust_top_level_eval_extracted": False, "pcs_scientific_authority": False}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"theorems": len(axioms), "source_windows": len(windows), "passed": True,
                      "all_foreign_windows_checked": all(x["current_checkout_checked"] for x in windows),
                      "pcs_scientific_authority": False}))


if __name__ == "__main__":
    main()
