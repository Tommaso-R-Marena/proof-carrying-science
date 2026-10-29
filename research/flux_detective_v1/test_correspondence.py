"""Independent Fraction/matrix oracle, export attacks, and actual Lean replay."""
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from pcs import scientific_workflow_v3 as workflow
from pcs.transport_trace_kernel_v1 import prepare
from research.portable_transport_v2 import replay as authority
from .check import capture, MAX_BYTES

ROOT = Path(__file__).resolve().parents[2]


def fixtures(seeds):
    return json.loads(subprocess.check_output(["node", str(Path(__file__).with_name("fixtures.mjs")), *map(str, seeds)], cwd=ROOT))


@pytest.fixture(scope="module")
def cases():
    # Fixed edge seeds plus 64 preregistered sequential seeds, not all 2^32 seeds.
    return fixtures([0, 1, 4294967295, 20261021, *range(1000, 1064)])


def test_1224_exports_against_independent_fraction_matrix_oracle(cases):
    assert len(cases) == 1224
    accepted = 0
    for item in cases:
        contract, csv = capture(json.dumps(item["bundle"]).encode())
        data = prepare(contract, csv)
        c = workflow.load_contract(contract)
        matrix = workflow.transition_matrix(c)
        rows = [[F(x) for x in row] for row in data["states"]]
        v = [F(cell["volume"]) for cell in c["cells"]]
        lo, hi = min(rows[0]), max(rows[0])
        amounts = [sum(x*w for x, w in zip(row, v)) for row in rows]
        energies = [sum(x*x*w for x, w in zip(row, v)) for row in rows]
        assert all(x == amounts[0] for x in amounts)
        assert all(lo <= x <= hi for row in rows for x in row)
        assert all(a >= b for a, b in zip(energies, energies[1:]))
        assert energies[-1] < energies[0]
        fault = None
        for k in range(c["steps"]):
            for i, row in enumerate(matrix):
                expected = sum(p*x for p, x in zip(row, rows[k]))
                if fault is None and expected != rows[k+1][i]:
                    observed = rows[k+1][i]
                    fault = dict(kind="recurrence", step=k, cell=i, observed=str(observed), expected=str(expected), residual=str(observed-expected))
        assert item["analysis"] == dict(mass=True, bounds=True, energy=True, energies=list(map(str, energies)), amount=str(amounts[0]), fault=fault)
        accepted += fault is None
    assert accepted == 408  # The remaining 816 have attractive but insufficient summaries.


@pytest.mark.parametrize("field,value", [("seed", True), ("seed", -1), ("seed", 4294967296), ("level", 6), ("choice", 3), ("trajectory", []), ("contract", []), ("format", "unknown")])
def test_malformed_metadata_rejected(cases, field, value):
    bundle = deepcopy(cases[0]["bundle"]); bundle[field] = value
    with pytest.raises(ValueError): capture(json.dumps(bundle).encode())


@pytest.mark.parametrize("raw", [b"\xff", b"[]", b"{}", b'{"format":"x","format":"y"}', b" "*(MAX_BYTES+1), bytearray(b"{}")])
def test_malformed_bytes_rejected(raw):
    with pytest.raises((ValueError, UnicodeError)): capture(raw)


def test_excessive_json_nesting_is_a_refusal():
    with pytest.raises(ValueError): capture(b"[" * 2000 + b"0" + b"]" * 2000)


def test_extra_verdict_and_path_injection_rejected(cases):
    for name, value in [("kernel_supported", True), ("proof", "by sorry"), ("verifier", "/bin/true"), ("out", "../escape")]:
        bundle = deepcopy(cases[0]["bundle"]); bundle[name] = value
        with pytest.raises(ValueError): capture(json.dumps(bundle).encode())


def test_csv_and_contract_corruption_rejected(cases):
    original = cases[0]["bundle"]
    for key, value in [("trajectory", original["trajectory"] + "trailing\n"), ("trajectory", original["trajectory"].replace("time_s", "time"))]:
        bundle = deepcopy(original); bundle[key] = value
        with pytest.raises(ValueError): capture(json.dumps(bundle).encode())
    bundle = deepcopy(original); bundle["contract"]["data_path"] = "../escape.csv"
    with pytest.raises(ValueError): capture(json.dumps(bundle).encode())


def test_seed_metadata_never_controls_actual_trace_verdict(cases):
    bundle = deepcopy(cases[0]["bundle"])
    before = capture(json.dumps(bundle).encode()); bundle["seed"] = 37; bundle["choice"] = 2
    assert capture(json.dumps(bundle).encode()) == before


def test_cli_refuses_malformed_input_and_existing_output_without_lean(tmp_path):
    bundle = tmp_path / "bad.json"; bundle.write_bytes(b"{}")
    out = tmp_path / "evidence"
    cmd = [sys.executable, "-m", "research.flux_detective_v1.check", str(bundle), str(out)]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 20 and not out.exists()
    assert json.loads(result.stdout)["status"] == "REFUSED"
    out.mkdir(); (out / "sentinel").write_text("preserve")
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 20 and (out / "sentinel").read_text() == "preserve"


@pytest.mark.parametrize("item", fixtures([20261021]), ids=lambda x: f"level-{x['bundle']['level']}-choice-{x['bundle']['choice']}")
def test_actual_lean_supports_or_refutes_all_18_default_choices(item, tmp_path):
    # Never skip for a missing toolchain and never substitute an affirmative verifier.
    contract, csv = capture(json.dumps(item["bundle"]).encode())
    result = authority.replay(contract, csv)
    good = item["analysis"]["fault"] is None
    assert result["kernel_supported"] == good, result
    assert result["negative_kernel_checked"] == (not good), result
    assert result["all_time_model_kernel_supported"] and result["sources_stable"]
    assert not result["pcs_authority"] and not result["scientific_acceptance"]
    assert result.get("fault") == item["analysis"]["fault"]
    assert all(set(a) <= authority.model.APPROVED_AXIOMS for a in result["axiom_closures"].values())
    authority.export(tmp_path / "evidence", result, contract, csv)
    retained = __import__("os").environ.get("PCS_FLUX_EVIDENCE_DIR")
    if retained:
        out = Path(retained) / f"level-{item['bundle']['level']}-choice-{item['bundle']['choice']}"
        authority.export(out, result, contract, csv)


@pytest.mark.parametrize("good", [True, False])
def test_real_cli_exit_status_and_independent_evidence_replay(good, tmp_path):
    item = next(x for x in fixtures([20261021]) if (x["analysis"]["fault"] is None) == good)
    bundle = tmp_path / "case.json"; bundle.write_text(json.dumps(item["bundle"]))
    out = tmp_path / "evidence"
    result = subprocess.run([sys.executable, "-m", "research.flux_detective_v1.check", str(bundle), str(out)], cwd=ROOT, text=True, capture_output=True, timeout=150)
    assert result.returncode == (0 if good else 10), result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["kernel_supported"] == good and summary["negative_kernel_checked"] == (not good)
    # Tampering with the stored verdict cannot control a separate replay.
    stored_path = out / "result.json"
    stored = json.loads(stored_path.read_text())
    stored["kernel_supported"], stored["negative_kernel_checked"] = not good, good
    stored_path.write_text(json.dumps(stored))
    inventory_path = out / "SHA256.json"
    inventory = json.loads(inventory_path.read_text())
    inventory["result.json"] = hashlib.sha256(stored_path.read_bytes()).hexdigest()
    inventory_path.write_text(json.dumps(inventory))
    replayed = authority.verify_export(out)
    assert replayed["kernel_supported"] == good and replayed["negative_kernel_checked"] == (not good)
