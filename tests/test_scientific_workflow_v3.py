from copy import deepcopy
import csv
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.scientific_workflow_v3 import (TransportWorkflowError, build_bundle, verify_bundle,
    evaluate, load_contract, transition_matrix, make_plan, resolve, reference)
from pcs.signing import generate_keypair

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/scientific_workflow_v3"


def inputs():
    return (EXAMPLE/"contract.json").read_bytes(), (EXAMPLE/"trajectory.csv").read_bytes()


def alter_last(raw, change):
    rows = list(csv.reader(io.StringIO(raw.decode())))
    rows[-1] = change(rows[-1])
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(rows)
    return stream.getvalue().encode()


def test_actual_flux_producer_equals_matrix_receiver_and_all_bounded_invariants():
    report = evaluate(*inputs())
    assert report["outcome"] == "PASS"
    assert len(report["checks"]) == 10
    assert len(report["trajectory"]) == 17
    assert report["statistics"]["initial_amount_mol"] == report["statistics"]["final_amount_mol"] == "7/4"
    assert report["data_origin"] == "synthetic_numerical_computation_not_empirical"
    assert not report["scientific_acceptance"] and not report["quadratic_functional_is_thermodynamic_energy"]


def test_volume_weighted_transition_not_unweighted_amount_is_the_conserved_quantity():
    contract = load_contract(inputs()[0])
    matrix = transition_matrix(contract)
    volumes = [Fraction(c["volume"]) for c in contract["cells"]]
    for row in matrix:
        assert sum(row) == 1 and min(row) >= 0
    for j in range(len(matrix)):
        assert sum(volumes[i]*matrix[i][j] for i in range(len(matrix))) == volumes[j]
    assert any(sum(matrix[i][j] for i in range(len(matrix))) != 1 for j in range(len(matrix)))


def test_amount_leak_has_a_real_failure_witness():
    contract, raw = inputs()
    bad = alter_last(raw, lambda row: [row[0], str(Fraction(row[1])+1), *row[2:]])
    result = evaluate(contract, bad)
    checks = {c["id"]: c for c in result["checks"]}
    assert result["outcome"] == "FAIL"
    assert checks["amount_conservation"]["outcome"] == "FAIL"
    assert checks["amount_conservation"]["witness"]["row"] == 16


def test_conservation_alone_does_not_certify_the_model_trajectory():
    contract, raw = inputs()
    wrong = alter_last(raw, lambda row: [row[0], *("7/32" for _ in range(5))])
    result = evaluate(contract, wrong)
    checks = {c["id"]: c["outcome"] for c in result["checks"]}
    assert checks["amount_conservation"] == checks["maximum_principle"] == checks["quadratic_dissipation"] == "PASS"
    assert checks["step_replay"] == "FAIL" and result["outcome"] == "FAIL"


@pytest.mark.parametrize("update", [
    {"time_step":"2"}, {"steps":True}, {"steps":0}, {"steps":65},
    {"data_origin":"real_empirical_observation"}, {"license":"unknown"},
    {"data_path":"../trajectory.csv"}, {"data_path":"."}, {"data_path":"/trajectory.csv"},
    {"data_path":"pcs-transport-v3/report.json"}, {"data_path":"contract.json"},
    {"time_step":"nan"}, {"time_step":0.25},
])
def test_unsupported_unstable_or_implicitly_typed_contracts_are_rejected(update):
    contract = json.loads(inputs()[0]);contract.update(update)
    with pytest.raises(ValueError):load_contract(canonicalize_jcs_bytes(contract))


@pytest.mark.parametrize("case", ["unknown-cell", "self-loop", "reverse-duplicate", "zero-conductance", "zero-volume", "negative-initial", "duplicate-cell", "duplicate-assumption", "wrong-units"])
def test_typed_topology_and_physical_parameters_are_checked(case):
    c = json.loads(inputs()[0])
    if case == "unknown-cell":c["edges"][0]["left"] = "Other"
    if case == "self-loop":c["edges"][0]["left"] = c["edges"][0]["right"]
    if case == "reverse-duplicate":c["edges"].append({"left":"CellB","right":"CellA","conductance":"1/2"})
    if case == "zero-conductance":c["edges"][0]["conductance"] = "0"
    if case == "zero-volume":c["cells"][0]["volume"] = "0"
    if case == "negative-initial":c["cells"][0]["initial_concentration"] = "-1"
    if case == "duplicate-cell":c["cells"][1]["id"] = "CellA"
    if case == "duplicate-assumption":c["assumptions"].append(c["assumptions"][0])
    if case == "wrong-units":c["units"]["conductance"] = "m^2/s"
    with pytest.raises(ValueError):load_contract(canonicalize_jcs_bytes(c))


def test_cfl_boundary_allows_nonincreasing_not_strictly_decreasing_functional():
    c = json.loads(inputs()[0]);c["cells"] = [{"id":"A","volume":"1","initial_concentration":"1"},{"id":"B","volume":"1","initial_concentration":"0"}]
    c["edges"] = [{"left":"A","right":"B","conductance":"1"}];c["time_step"] = "1";c["steps"] = 2
    typed = load_contract(canonicalize_jcs_bytes(c))
    assert reference(typed) == [[Fraction(1),Fraction(0)],[Fraction(0),Fraction(1)],[Fraction(1),Fraction(0)]]
    assert evaluate(canonicalize_jcs_bytes(c),b"time_s,A,B\n0,1,0\n1,0,1\n2,1,0\n")["outcome"] == "PASS"


@pytest.mark.parametrize("change", ["header", "missing-row", "extra-row", "ragged", "non-numeric"])
def test_malformed_trajectory_is_not_silently_repaired(change):
    contract, data = inputs()
    if change == "header":data = data.replace(b"CellA",b"Other",1)
    if change == "missing-row":data = b"\n".join(data.splitlines()[:-1])+b"\n"
    if change == "extra-row":data += data.splitlines()[-1]+b"\n"
    if change == "ragged":data = alter_last(data,lambda row:row[:-1])
    if change == "non-numeric":data = alter_last(data,lambda row:[row[0],"nan",*row[2:]])
    with pytest.raises(ValueError):evaluate(contract,data)


def test_wrong_grid_and_negative_concentration_are_explicit_property_failures():
    contract, data = inputs()
    for changed, ident in [(alter_last(data,lambda row:["100",*row[1:]]),"time_grid"),
                           (alter_last(data,lambda row:[row[0],"-1",*row[2:]]),"nonnegative")]:
        result = evaluate(contract,changed)
        assert next(x for x in result["checks"] if x["id"] == ident)["outcome"] == "FAIL"


def test_data_and_premise_changes_invalidate_dependents_and_mismatched_report_rejects():
    contract_raw, data = inputs();c = load_contract(contract_raw)
    report = evaluate(contract_raw,data)
    plan = make_plan(c,hashlib.sha256(contract_raw).hexdigest(),hashlib.sha256(data).hexdigest())
    old = resolve(plan,report)
    assert next(x for x in old["nodes"] if x["id"] == "continuum_and_empirical_adequacy")["status"] == "OPEN"
    changed = deepcopy(plan);changed["nodes"][0]["statement"] = "An unmodeled external source now exists."
    assert next(x for x in resolve(changed,report,old)["nodes"] if x["id"] == "workflow")["status"] == "INVALIDATED"
    changed_data = alter_last(data,lambda row:[row[0],str(Fraction(row[1])+1),*row[2:]])
    changed_plan = make_plan(c,hashlib.sha256(contract_raw).hexdigest(),hashlib.sha256(changed_data).hexdigest())
    with pytest.raises(TransportWorkflowError,match="different trajectory"):resolve(changed_plan,report,old)
    result = resolve(changed_plan,evaluate(contract_raw,changed_data),old)
    assert next(x for x in result["nodes"] if x["id"] == "workflow")["status"] == "INVALIDATED"


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    directory = tmp_path_factory.mktemp("transport-v3")
    project = directory/"source";shutil.copytree(EXAMPLE,project)
    (project/"DO_NOT_RUN.py").write_text("raise RuntimeError('submitted source must not execute')\n")
    private, public = directory/"private.pem",directory/"public.pem"
    fingerprint = generate_keypair(private,public)["fingerprint"]
    bundle = directory/"positive.pcs.zip"
    build_bundle(project,directory/"work",bundle,private,public,expected_fingerprint=fingerprint,confirm_reviewed_draft=True)
    return {"directory":directory,"project":project,"private":private,"public":public,"fingerprint":fingerprint,"bundle":bundle}


def test_compiled_dimensions_pass_with_all_numerical_and_scientific_claims_open(package):
    result = verify_bundle(package["bundle"],package["public"],expected_fingerprint=package["fingerprint"])
    assert result["pcs_package_valid"] and result["independent_replay_consistent"] and result["bounded_contract_satisfied"]
    decisions = {x["claim_id"]:x["decision"] for x in result["pcs_verification"]["claims"]}
    assert all(decisions[cid] == "OPEN" for cid in ("C_NUMERICAL","C_CONTINUUM","C_EMPIRICAL"))
    assert sum(x == "COMPUTATIONALLY_SUPPORTED" for x in decisions.values()) == 3
    assert not result["scientific_acceptance"] and not result["user_code_executed"]


def test_generic_external_intake_and_separate_receiving_cli_execute(package):
    directory = package["directory"];artifact = directory/"cli.pcs.zip"
    command = [sys.executable,str(ROOT/"scripts/run_scientific_workflow_v3.py")]
    build = subprocess.run([*command,"--project",str(package["project"]),"--work-directory",str(directory/"cli-work"),"--output",str(artifact),
        "--private-key",str(package["private"]),"--public-key",str(package["public"]),"--fingerprint",package["fingerprint"],"--confirm-reviewed-draft"],cwd=ROOT,capture_output=True,timeout=60)
    assert build.returncode == 0,build.stderr.decode()
    assert json.loads(build.stdout)["bounded_contract_satisfied"]
    receipt = directory/"fresh-cli.json"
    replay = subprocess.run([*command,"--replay",str(artifact),"--output",str(receipt),"--public-key",str(package["public"]),"--fingerprint",package["fingerprint"]],cwd=ROOT,capture_output=True,timeout=60)
    assert replay.returncode == 0,replay.stderr.decode()
    assert json.loads(receipt.read_bytes())["bounded_contract_satisfied"]


@pytest.mark.parametrize("forgery", ["false-value", "bool-numeric-confusion", "falsified-dimension"])
def test_legitimately_re_signed_evidence_is_independently_rejected(package,forgery):
    from pcs.attest_v06 import build_attestation_directory_v06
    from pcs.bundle_v06 import create_verified_bundle_v06
    from pcs.check_registry_v06 import predicate_from_manifest_check_v06
    directory = package["directory"];stage = directory/(forgery+"-source")
    shutil.copytree(directory/"work/project",stage)
    manifest_file = stage/"manifest.confirmed.json";manifest = json.loads(manifest_file.read_bytes())
    if forgery == "falsified-dimension":
        check = next(x for x in manifest["checks"] if x["id"] == "E_step_dimensions")
        check["left_unit"] = "s*m^3/s"
        next(x for x in manifest["claims"] if x["id"] == "C_step_dimensions")["predicate"] = predicate_from_manifest_check_v06(check)
    else:
        report_file = stage/"pcs-transport-v3/report.json";report = json.loads(report_file.read_bytes())
        if forgery == "false-value":report["statistics"]["final_amount_mol"] = "0"
        else:report["pcs_authority"] = 0
        report_file.write_bytes(canonicalize_jcs_bytes(report))
        for item in manifest["artifacts"]:
            raw = (stage/item["path"]).read_bytes();item["metadata"]["pcs_discovery_sha256"] = hashlib.sha256(raw).hexdigest();item["metadata"]["pcs_discovery_size"] = len(raw)
    manifest_file.write_bytes(canonicalize_jcs_bytes(manifest))
    package_path, artifact = directory/(forgery+"-package"),directory/(forgery+".pcs.zip")
    build_attestation_directory_v06(manifest_file,package_path,package["private"],package["public"],expected_fingerprint=package["fingerprint"],generated_at="2026-10-13T00:00:00+00:00")
    create_verified_bundle_v06(package_path,artifact,package["public"],expected_fingerprint=package["fingerprint"])
    result = verify_bundle(artifact,package["public"],expected_fingerprint=package["fingerprint"])
    assert result["pcs_package_valid"] and not result["independent_replay_consistent"] and not result["bounded_contract_satisfied"]
    if forgery == "falsified-dimension":
        assert next(x["decision"] for x in result["pcs_verification"]["claims"] if x["claim_id"] == "C_step_dimensions") == "FALSIFIED_OR_CHECK_FAILED"


def test_wrong_pin_confirmation_and_existing_paths_are_rejected(package):
    assert not verify_bundle(package["bundle"],package["public"],expected_fingerprint="0"*64)["pcs_package_valid"]
    with pytest.raises(TransportWorkflowError,match="confirmation"):
        build_bundle(package["project"],package["directory"]/"unconfirmed",package["directory"]/"unconfirmed.zip",package["private"],package["public"],expected_fingerprint=package["fingerprint"])
    with pytest.raises(TransportWorkflowError,match="new work"):
        build_bundle(package["project"],package["directory"]/"work",package["bundle"],package["private"],package["public"],expected_fingerprint=package["fingerprint"],confirm_reviewed_draft=True)
