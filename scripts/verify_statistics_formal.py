"""Compile statistical gates against the exact Mathlib revision and audit their axioms."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from verify_omega_dd_formal import check_inventory
from audit_lean_source import audit

ROOT = Path(__file__).resolve().parents[1]
REVISION = "8f9d9cff6bd728b17a24e163c9402775d9e6a365"
THEOREMS = ["PCSStatistics.paired_improvement_bound", "PCSStatistics.GateSpec.adaptive_promotion_error_budget",
            "PCSStatistics.GateSpec.anytime_selection_valid"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT / ".lake/packages/mathlib", text=True).strip()
    if revision != REVISION:
        raise ValueError("Mathlib revision mismatch")
    source = ROOT / "formal/statistics/PCSStatistics/Gates.lean"
    if findings := audit([source]):
        raise ValueError("\n".join(findings))
    with tempfile.TemporaryDirectory(prefix="pcs-statistics-gate-") as folder:
        driver = Path(folder) / "StatisticsAudit.lean"
        driver.write_text(source.read_text() + "\n" + "\n".join("#print axioms " + t for t in THEOREMS) + "\n")
        proc = subprocess.run(["lake", "env", "lean", str(driver)], cwd=ROOT, text=True, capture_output=True, timeout=600)
    if proc.returncode:
        raise RuntimeError(proc.stdout + proc.stderr)
    inventory = check_inventory(proc.stdout, THEOREMS)
    report = {"mathlib_revision": revision, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "kernel_checked_inventory": inventory, "experimental_superiority_established": False,
              "scope": "Statistical bounds conditional on the declared independence, boundedness, sampling and mean assumptions; no automatic validation of real datasets."}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": len(inventory), "mathlib_revision": revision}))


if __name__ == "__main__":
    main()
