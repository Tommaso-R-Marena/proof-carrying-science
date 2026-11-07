"""Create an authored walkthrough from real v3 checks and a fresh Lean run.

Only the development NIST fixture is read. This is an automated demonstration,
not a human usability study or held-out evaluation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from research.scientific_semantics_v3.semantics import interpret_project
from research.scientific_semantics_v3.checks import execute
from research.scientific_semantics_v3.assurance import verify
from research.scientific_review_v4.review import render


def build(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    development = Path(__file__).resolve().parents[2] / "scientific_semantics_v3/fixtures/development/nist_hahn1/Hahn1.dat"
    raw = development.read_bytes()
    artifacts = {
        "Hahn1.dat": raw,
        "Hahn1-altered.dat": raw.replace(b".591E0", b"99.591E0", 1),
        "model.sbml": b'<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4"><model id="example"><listOfParameters><parameter id="k" value="3" units="second"/></listOfParameters></model></sbml>',
        "review-notes.bin": b'Unresolved research context. <script>window.PCS_INJECTED=true</script><img src="https://invalid.example/pcs-leak" onerror="window.PCS_INJECTED=true">',
    }
    with tempfile.TemporaryDirectory(prefix="pcs-ui-authored-") as folder:
        for name, data in artifacts.items():
            Path(folder, name).write_bytes(data)
        interpretation = interpret_project(folder)
    # Keep the walkthrough readable while retaining actual, byte-bound results.
    interpretation["claims"] = [c for c in interpretation["claims"] if c["source"]["path"] != "Hahn1-altered.dat" and (c.get("entity") == "k" or c.get("quantity_role") in {"residual_sum_squares", "statistical_model"})]
    checks = execute(interpretation, artifacts)
    old_path = os.environ.get("PATH", "")
    lean_bin = Path("/workspace/.onboarding/tools/lean-4.28.0-linux/bin")
    if lean_bin.exists():
        os.environ["PATH"] = str(lean_bin) + os.pathsep + old_path
    try:
        receipt = verify()
    finally:
        os.environ["PATH"] = old_path
    if receipt.get("status") != "KERNEL_CHECKED_ABSTRACT_PARTIAL_SEMANTICS":
        raise RuntimeError("Fresh actual Lean replay required for the authored walkthrough: " + json.dumps(receipt))
    checks.append(receipt)
    summary = {
        "authority": False, "scientific_meanings_certified": 0,
        "source_download_prefix": "parent/intake/objects/",
        "study_overview": "Authored walkthrough using the NIST Hahn1 benchmark and a small SBML declaration. These are separate examples of evidence scope. The altered data file tests whether a mismatch is detected; the Lean theorem concerns abstract partial expressions.",
        "missing_assets": ["A scientific protocol connecting these independent examples; no empirical study is claimed."],
        "next_checks": ["Inspect the altered Hahn1 result and compare it with the original data.", "Check the model parameter's units and intended scientific interpretation.", "Read the Lean receipt's theorem scope; Python refinement and empirical validity remain open."],
    }
    (output / "review.html").write_text(render(interpretation, checks, artifacts, summary))
    objects = output / summary["source_download_prefix"]
    objects.mkdir(parents=True)
    for data in artifacts.values():
        (objects / hashlib.sha256(data).hexdigest()).write_bytes(data)
    (output / "fixture.json").write_text(json.dumps({"interpretation": interpretation, "checks": checks, "summary": summary}, indent=2, sort_keys=True))
    source = interpretation["claims"][0]["source"]
    manifest = {"authored": True, "human_usability_study": False, "heldout_data_read": False,
                "fresh_lean_status": receipt["status"], "source_path": source["path"],
                "download_sha256": source["sha256"], "download_path": summary["source_download_prefix"] + source["sha256"],
                "check_statuses": sorted({r["status"] for r in checks}),
                "review_sha256": hashlib.sha256((output / "review.html").read_bytes()).hexdigest()}
    (output / "demo-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    print(json.dumps(build(parser.parse_args().output), indent=2, sort_keys=True))
