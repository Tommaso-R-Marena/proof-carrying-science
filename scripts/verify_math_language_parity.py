"""Differential tests against the actual patched English parser; not refinement proofs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs.experimental.prover.language import DOMAINS, formalize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    fixture = ROOT / "research/aristotle-runtime-refinement-v1/language-cases.json"
    driver = ROOT / "formal/tools/RuntimeRefinementLanguageCases.lean"
    cases = json.loads(fixture.read_text())
    result = subprocess.run(["lake", "env", "lean", str(driver)], cwd=ROOT / "formal",
                            text=True, capture_output=True, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    lean = result.stdout.splitlines()
    if len(lean) != len(cases) or len(cases) != 1523:
        raise ValueError("missing or extra differential outcomes")
    domains = {v: k for k, v in DOMAINS.items()}
    failures = []
    for index, (case, expected) in enumerate(zip(cases, lean)):
        source = f"For all {domains[case['domain']]} {', '.join(case['names'])}, {case['body']}"
        actual = formalize(source)
        rendered = "U" if actual["status"] == "unsupported" else " ||| ".join(c["lean"] for c in actual["candidates"])
        if rendered != expected:
            failures.append({"index": index, "lean": expected, "python": rendered})
    report = {"format": "pcs-math-language-differential-v1", "cases": len(cases),
              "mismatches": failures, "source_sha256": hashlib.sha256((ROOT / "pcs/experimental/prover/language.py").read_bytes()).hexdigest(),
              "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
              "driver_sha256": hashlib.sha256(driver.read_bytes()).hexdigest(),
              "runtime_refinement_proved": False, "pcs_scientific_authority": False}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    if failures:
        raise ValueError(f"{len(failures)} language differential mismatches: {failures[:3]}")
    print(json.dumps({"passed": len(cases), "runtime_refinement_proved": False}))


if __name__ == "__main__":
    main()
