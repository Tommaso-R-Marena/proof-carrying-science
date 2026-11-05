"""One source-bound A→B fixture replayed by Python receivers and actual Lean.

Agreement here is a concrete differential observation, not general refinement.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

from .scoped_evidence import ROOT, component, digest, replay_conservation, replay_interval


def fixture():
    contract = {
        "format": "pcca-mass-action-contract-v1",
        "species": [{"id": "A", "formula": "C"}, {"id": "B", "formula": "C"}],
        "reactions": [{"id": "transfer", "reactants": [{"species": "A", "coefficient": 1}],
                       "products": [{"species": "B", "coefficient": 1}],
                       "rate_constant": "1/3", "rate_unit": "s^-1"}],
        "initial": {"A": "1", "B": "0"}, "time_step": "1", "steps": 1,
        "concentration_unit": "mol/L", "time_unit": "s",
        "assumptions": ["Declared synthetic A→B network; one exact rational firing.",
                        "No empirical chemistry or continuum accuracy is asserted."],
    }
    conservation, report = replay_conservation(contract)
    trajectory = next(c for c in report["certificates"] if c["kind"] == "trajectory_conservation")
    state = trajectory["claim"]["states"][-1]
    component("certnum")
    from certnum.expr.ast import Const, expr_to_json
    from certnum.interval.interval import Interval
    from certnum.certificate.schema import make_certificate
    numeric = make_certificate("interval_enclosure", claim={
        "expr": expr_to_json(Const(Fraction(state[0]))), "box": {},
        "enclosure": Interval.mk(Fraction(3, 5), Fraction(7, 10)).to_json()}, witness={})
    numerical = replay_interval(numeric)
    matrix = trajectory["claim"]["matrix"]
    initial = trajectory["claim"]["states"][0]
    firing = trajectory["claim"]["xis"][0][0]
    total = sum(Fraction(v) for v in initial)
    lower, upper = Fraction(3, 5), Fraction(7, 10)
    expected = "|".join(["PCSAB1", str(Fraction(matrix[0][0])), str(Fraction(matrix[1][0])),
                         *initial, firing, str(len(trajectory["claim"]["xis"])),
                         *state, str(Fraction(state[0])), str(lower), str(upper),
                         str(total - upper), str(total - lower), "true"])
    return {"contract": contract, "system_sha256": digest(contract),
            "trajectory_certificate": trajectory, "numerical_certificate": numeric,
            "scoped_observations": [o.to_dict() for o in conservation] + [numerical.to_dict()],
            "expected_lean_frame": expected, "lean_execution": "NOT_RUN",
            "python_lean_general_refinement": "OPEN", "scientific_acceptance": False}


def replay_with_lean():
    from .source_gate import check_profile
    profile = check_profile()
    if not profile["passed"]:
        raise RuntimeError(f"source identity gate rejected fixture: {profile['failures']}")
    result = fixture()
    project = ROOT / "research/integration_v1/formal"
    for command in (["lake", "build", "PCSIntegration"],
                    ["lake", "env", "lean", "--run", "BridgeFixture.lean"]):
        process = subprocess.run(command, cwd=project, capture_output=True, text=True, timeout=300)
        if process.returncode:
            raise RuntimeError("actual Lean fixture failed: " + process.stdout + process.stderr)
    if process.stdout != result["expected_lean_frame"] + "\n":
        raise RuntimeError("Python/PCCA/CertNum versus actual Lean fixture mismatch")
    if not check_profile()["passed"]:
        raise RuntimeError("source changed during fixture replay")
    return {**result, "lean_execution": "FIXED_FIXTURE_MATCH", "actual_lean_frame": process.stdout.strip(),
            "lean_fixture_source_sha256": hashlib.sha256((project / "BridgeFixture.lean").read_bytes()).hexdigest(),
            "production_authority": False, "promotion_authority": False,
            "note": "Kernel theorem audit is separate; this is one exact implementation differential."}


if __name__ == "__main__":
    print(json.dumps(replay_with_lean(), indent=2, sort_keys=True))
