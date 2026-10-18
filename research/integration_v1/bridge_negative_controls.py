"""Real Lean rejects false claims about the composed scientific fixture."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "research/integration_v1/formal"
HEADER = """import PCSIntegration
open PCSIntegration CertNum CertNum.Expr CertNum.Certificate
"""
CASES = {
    "false_enclosure_acceptance": """example : checkIntervalEnclosure { sampleCertificate with claimed := .empty } = true := by
  norm_num [checkIntervalEnclosure, sampleCertificate, Expr.evalInterval,
            Enclosure.ok, Interval.singleton]
""",
    "false_transfer_value": """example : PCCA.Stoich.evolve transfer (fun _ _ => (1 / 3 : ℚ))
    (fun s => if s = 0 then 1 else 0) 1 1 = 0 := by
  norm_num [PCCA.Stoich.evolve, PCCA.Stoich.fire, transfer, Fin.sum_univ_one]
""",
}


def run():
    results = []
    with tempfile.TemporaryDirectory(prefix="pcs-bridge-falsification-") as folder:
        for label, proposition in CASES.items():
            source = HEADER + proposition
            path = Path(folder) / (label + ".lean")
            path.write_text(source)
            process = subprocess.run(["lake", "env", "lean", str(path)], cwd=PROJECT,
                                     capture_output=True, text=True, timeout=90)
            log = process.stdout + process.stderr
            rejected = process.returncode != 0 and "unsolved goals" in log and "False" in log
            if not rejected:
                raise RuntimeError(f"negative control did not reach the expected false goal: {label}\n{log}")
            results.append({"case": label, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                            "actual_lean_exit_code": process.returncode,
                            "expected_false_goal_rejected": True,
                            "output_sha256": hashlib.sha256(log.encode()).hexdigest()})
    return {"format": "pcs-bridge-kernel-negative-controls-v1", "cases": results,
            "mock_verifier": False, "production_authority": False}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
