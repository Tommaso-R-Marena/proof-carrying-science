"""Real Lean integration tests. Opt in explicitly; no simulated positive verdicts."""

import copy
import os
from pathlib import Path
import pytest
from .authority import Authority, digest
from .verifier import verify, replay, RISK_DESCRIPTOR
from . import parsing
from . import emission

pytestmark = pytest.mark.skipif(
    os.environ.get("PCS_SCIENTIFIC_REAL_LEAN") != "1",
    reason="Requires pinned Lean and Mathlib dependency cache",
)
HERE = Path(__file__).parent


@pytest.fixture(scope="module")
def authority(tmp_path_factory):
    return Authority(tmp_path_factory.mktemp("scientific") / "authority")


@pytest.fixture(scope="module")
def packages(authority):
    fixtures = [
        (
            "prism",
            (HERE / "vendor/prism/examples/biochemical/problem.json").read_bytes(),
        ),
        (
            "aion",
            (HERE / "vendor/aion/certificates/A_birth_death_N10.json").read_bytes(),
        ),
        ("risk-demo", parsing.encode(RISK_DESCRIPTOR)),
    ]
    return [
        verify(kind, raw, authority, out=authority.out / (kind + "-evidence.json"))
        for kind, raw in fixtures
    ]


@pytest.mark.parametrize("index", range(3))
def test_real_kernel_admission_and_replay(authority, packages, index):
    d = packages[index]
    assert d["proof"]["kernel_checked"] and not d["production_authority"]
    fresh = replay(
        parsing.encode(d), authority, out=authority.out / f"replay-{index}.json"
    )
    assert fresh["claim"] == d["claim"]
    assert all(
        set(a) <= {"propext", "Classical.choice", "Quot.sound"}
        for a in fresh["proof"]["axiom_closures"].values()
    )


def test_actual_false_lean_theorem_rejected(authority):
    with pytest.raises(ValueError, match="Actual Lean rejected"):
        authority._prove(
            "import Mathlib\ntheorem pcs_false : (0 : Nat) = 1 := by decide +kernel\n",
            ["pcs_false"],
            "negative_false_theorem",
        )


def test_rehashed_forged_scientific_claim_fails_replay(authority, packages):
    d = copy.deepcopy(packages[2])
    d["claim"]["optimal_worst_case_cost"] = "0"
    d["receipt_sha256"] = digest(
        parsing.encode({k: v for k, v in d.items() if k != "receipt_sha256"})
    )
    with pytest.raises(ValueError, match="Independent replay differs"):
        replay(parsing.encode(d), authority, out=authority.out / "forged-replay.json")
    assert not (authority.out / "forged-replay.json").exists()


def test_corrupt_receipt_refused(authority, packages):
    d = copy.deepcopy(packages[0])
    d["receipt_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Receipt changed"):
        replay(parsing.encode(d), authority, out=authority.out / "corrupt-replay.json")


def test_compiled_library_mutation_refused(authority):
    p = authority.out / "PCSScientific/RiskDemo.olean"
    original = p.read_bytes()
    try:
        p.write_bytes(original + b"corruption")
        with pytest.raises(ValueError, match="compiled library changed"):
            authority.check()
    finally:
        p.write_bytes(original)
    authority.check()


def test_caller_verifier_substitution_refused(authority):
    class Fake:
        def _prove(self, *a):
            return dict(kernel_checked=True)

    with pytest.raises(ValueError, match="Fixed real Lean authority"):
        verify(
            "risk-demo",
            parsing.encode(RISK_DESCRIPTOR),
            Fake(),
            out=authority.out / "fake.json",
        )


def test_zero_experiment_impossibility_is_really_checked(authority):
    raw = parsing.encode(
        dict(
            schema="prism-problem/1",
            name="no_assay",
            models=[dict(id="m0", q="0", obs={}), dict(id="m1", q="1", obs={})],
            experiments=[],
            query=dict(id="q"),
        )
    )
    result = verify("prism", raw, authority, out=authority.out / "no-assay.json")
    assert (
        result["claim"]["status"] == "UNIDENTIFIABLE"
        and result["proof"]["kernel_checked"]
    )


def test_historical_evidence_not_overwritten(authority, packages):
    p = authority.out / "risk-demo-evidence.json"
    original = p.read_bytes()
    with pytest.raises(ValueError, match="historical evidence overwrite"):
        verify("risk-demo", parsing.encode(RISK_DESCRIPTOR), authority, out=p)
    assert p.read_bytes() == original


def test_actual_false_aion_certificate_rejected_by_lean(authority):
    d = parsing.aion(
        (HERE / "vendor/aion/certificates/A_birth_death_N10.json").read_bytes()
    )
    d["upper"]["table"]["1"] = "0"
    with pytest.raises(ValueError, match="Actual Lean rejected"):
        authority._prove(
            emission.aion(d),
            ["AION.Examples.PCSReplay.upper_ok"],
            "negative_false_aion_certificate",
        )


def test_replay_rebuilds_from_fresh_process(authority, packages):
    import subprocess
    import sys

    p = authority.out / "risk-demo-evidence.json"
    out = authority.out.parent / "fresh-process-replay"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "research.scientific_engines_v1",
            "replay",
            str(p),
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=900,
    )
    fresh = parsing.load((out / "evidence.json").read_bytes(), evidence=True)
    assert fresh["claim"] == packages[2]["claim"] and fresh["proof"]["kernel_checked"]
