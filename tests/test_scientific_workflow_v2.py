from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.scientific_workflow_v2 import (
    ScientificWorkflowError, build_bundle, verify_bundle, load_contract,
    numerical_reference, evaluate, make_plan, _provenance, _sum,
)
from pcs.scientific_obligations_v1 import resolve_plan, topological_order
from pcs.scientific_contracts_v1 import ScientificResourceLimit
from pcs.signing import generate_keypair

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/scientific_workflow_v2"


def inputs():
    return ((EXAMPLE / "contract.json").read_bytes(), (EXAMPLE / "penguins.csv").read_bytes(),
            (EXAMPLE / "result.json").read_bytes())


def test_real_measurements_independent_exact_replay_and_accounting():
    contract, data, result = inputs()
    report = evaluate(contract, data, result)
    assert report["outcome"] == "PASS"
    assert report["reference"]["total_rows"] == 344
    assert report["reference"]["complete_rows"] == 342
    assert report["reference"]["excluded_rows"] == [4, 272]
    assert report["reference"]["slope_kg_per_m"] == "1145743050/23059877"
    assert report["pcs_authority"] is False


@pytest.mark.parametrize("name,value", [
    ("total_rows", 344.0), ("complete_rows", True), ("excluded_rows", [272, 4]),
    ("excluded_rows", [4, 4]), ("excluded_rows", [4.0, 272]),
    ("residual_sum_zero", 1), ("residual_predictor_inner_product_zero", "true"),
    ("slope_kg_per_m", 49.686), ("slope_kg_per_m", "1/0"),
])
def test_reported_values_cannot_exploit_python_numeric_equality(name, value):
    contract, data, result = inputs()
    reported = json.loads(result)
    reported[name] = value
    with pytest.raises(ValueError):
        evaluate(contract, data, json.dumps(reported).encode())


def test_validly_typed_but_false_slope_fails_bounded_contract():
    contract, data, result = inputs()
    reported = json.loads(result)
    reported["slope_kg_per_m"] = "0"
    assert evaluate(contract, data, canonicalize_jcs_bytes(reported))["outcome"] == "FAIL"


@pytest.mark.parametrize("field,value", [
    ("scale", "1/100"), ("source_unit", "cm"), ("target_unit", "kg"),
])
def test_exact_scale_and_measurement_types_are_enforced(field, value):
    contract = json.loads(inputs()[0])
    contract["x"][field] = value
    with pytest.raises(ScientificWorkflowError):
        load_contract(canonicalize_jcs_bytes(contract))


@pytest.mark.parametrize("path", [".", "../penguins.csv", "/penguins.csv", "foo//bar", "foo\\bar", "pcs-workflow-v2/data.csv", "contract.json"])
def test_contract_paths_cannot_escape_or_replace_reserved_artifacts(path):
    contract = json.loads(inputs()[0])
    contract["data_path"] = path
    with pytest.raises(ScientificWorkflowError):
        load_contract(canonicalize_jcs_bytes(contract))


@pytest.mark.parametrize("data", [
    b"flipper_length_mm,body_mass_g\n180,NA\nNA,4000\n",
    b"flipper_length_mm,body_mass_g\n180,3000\n180,4000\n",
    b"flipper_length_mm,body_mass_g\n-180,3000\n190,4000\n",
    b"flipper_length_mm,body_mass_g\n180,nan\n190,4000\n",
    b"flipper_length_mm,body_mass_g\nnot-a-number,NA\n190,4000\n",
    b"flipper_length_mm,body_mass_g\n-180,NA\n190,4000\n",
    b"flipper_length_mm,body_mass_g,body_mass_g\n180,3000,3000\n190,4000,4000\n",
    b"flipper_length_mm,body_mass_g\n180,3000,extra\n190,4000\n",
])
def test_invalid_data_abstains_without_relabeling_it_as_a_fit(data):
    with pytest.raises(ValueError):
        numerical_reference(load_contract(inputs()[0]), data)


def test_large_csv_and_aggregate_fraction_bounds():
    contract = load_contract(inputs()[0])
    data = b"flipper_length_mm,body_mass_g\n" + b"180,3000\n" * 4097
    with pytest.raises(ScientificWorkflowError, match="row limit"):
        numerical_reference(contract, data)
    from fractions import Fraction
    with pytest.raises(ScientificResourceLimit):
        _sum([Fraction(2**4095), Fraction(2**4095)])


def test_premise_changes_and_source_changes_invalidate_dependent_results():
    contract, data, result = inputs()
    report = evaluate(contract, data, result)
    plan = make_plan(load_contract(contract), hashlib.sha256(contract).hexdigest(), hashlib.sha256(data).hexdigest())
    initial = resolve_plan(plan, report)
    assert next(x for x in initial["nodes"] if x["id"] == "population_or_causal_validity")["status"] == "OPEN"
    revised = deepcopy(plan)
    revised["nodes"][0]["statement"] = "Now assume the records mean centimetres."
    changed = resolve_plan(revised, report, previous=initial)
    assert next(x for x in changed["nodes"] if x["id"] == "workflow")["status"] == "INVALIDATED"
    report["contract_sha256"] = "0" * 64
    assert all(x["invalidated"] for x in resolve_plan(plan, report)["nodes"])
    revised["nodes"][0]["dependencies"] = ["workflow"]
    with pytest.raises(ValueError, match="cycle"):
        topological_order(revised)


def test_changed_dataset_invalidates_cached_numerical_obligations():
    contract, data, result = inputs()
    report = evaluate(contract, data, result)
    typed = load_contract(contract)
    plan = make_plan(typed, hashlib.sha256(contract).hexdigest(), hashlib.sha256(data).hexdigest())
    old = resolve_plan(plan, report)
    updated_data = data.replace(b",181,3750,", b",181,3751,", 1)
    new_report = evaluate(contract, updated_data, result)
    revised = make_plan(typed, hashlib.sha256(contract).hexdigest(), hashlib.sha256(updated_data).hexdigest())
    changed = resolve_plan(revised, new_report, previous=old)
    states = {x["id"]: x for x in changed["nodes"]}
    assert states["data_binding"]["status"] == "INVALIDATED"
    assert states["least_squares_replay"]["status"] == "INVALIDATED"
    assert states["workflow"]["status"] == "INVALIDATED"


def test_real_source_and_cc0_artifacts_have_exact_pinned_provenance():
    sources = {p.name: p.read_bytes() for p in EXAMPLE.iterdir() if p.is_file()}
    provenance = _provenance(sources["provenance.json"], sources, "penguins.csv")
    assert provenance["source_revision"] == "8957207b78d6ccd1b4654a9dd9c9041b657478ab"
    assert "CC0 1.0 Universal" in sources["UPSTREAM_LICENSE.md"].decode()
    sources["penguins.csv"] += b"\n"
    with pytest.raises(ScientificWorkflowError, match="digest mismatch"):
        _provenance(sources["provenance.json"], sources, "penguins.csv")


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    directory = tmp_path_factory.mktemp("scientific-workflow-v2")
    project = directory / "source"
    shutil.copytree(EXAMPLE, project)
    (project / "DANGER.py").write_text("raise RuntimeError('submitted source must not execute')\n")
    private, public = directory / "private.pem", directory / "public.pem"
    fingerprint = generate_keypair(private, public)["fingerprint"]
    bundle = directory / "positive.pcs.zip"
    built = build_bundle(project, directory / "work", bundle, private, public,
        expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
    return {"directory": directory, "project": project, "private": private, "public": public,
            "fingerprint": fingerprint, "bundle": bundle, "built": built}


def test_existing_compiled_pcs_authority_and_fresh_workflow_receiver(package):
    result = verify_bundle(package["bundle"], package["public"], expected_fingerprint=package["fingerprint"])
    assert result["pcs_package_valid"] and result["independent_replay_consistent"]
    assert result["bounded_contract_satisfied"]
    assert result["pcs_verification"]["lean_authority"]["accepted"] is True
    decisions = {x["claim_id"]: x["decision"] for x in result["pcs_verification"]["claims"]}
    assert decisions["C_NUMERICAL"] == decisions["C_EMPIRICAL"] == "OPEN"
    assert decisions["C_slope_dimensions"] == "COMPUTATIONALLY_SUPPORTED"
    assert not result["scientific_acceptance"] and not result["user_code_executed"]


def test_wrong_pin_and_modified_bundle_are_rejected(package):
    wrong = verify_bundle(package["bundle"], package["public"], expected_fingerprint="0" * 64)
    assert not wrong["pcs_package_valid"]
    from pcs.canonical_zip_v06 import canonical_zip_bytes_v06
    from pcs.verifier_zip_v06 import load_package_zip_v06
    loaded = load_package_zip_v06(package["bundle"])
    import zipfile
    with zipfile.ZipFile(package["bundle"]) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    certificate = json.loads(loaded["certificate_bytes"])
    artifact = next(x for x in certificate["artifacts"] if x["source_path"] == "penguins.csv")
    files[artifact["path"]] += b"\n"
    modified = package["directory"] / "tampered.pcs.zip"
    modified.write_bytes(canonical_zip_bytes_v06(files))
    assert not verify_bundle(modified, package["public"], expected_fingerprint=package["fingerprint"])["pcs_package_valid"]


def test_re_signed_false_numerical_report_rejected_despite_valid_package(package):
    from pcs.attest_v06 import build_attestation_directory_v06
    from pcs.bundle_v06 import create_verified_bundle_v06
    directory = package["directory"]
    source = directory / "false-report-source"
    shutil.copytree(directory / "work/project", source)
    report_file = source / "pcs-workflow-v2/report.json"
    report = json.loads(report_file.read_bytes())
    report["reference"]["slope_kg_per_m"] = "0"
    report_file.write_bytes(canonicalize_jcs_bytes(report))
    manifest_file = source / "manifest.confirmed.json"
    manifest = json.loads(manifest_file.read_bytes())
    for artifact in manifest["artifacts"]:
        raw = (source / artifact["path"]).read_bytes()
        artifact["metadata"]["pcs_discovery_sha256"] = hashlib.sha256(raw).hexdigest()
        artifact["metadata"]["pcs_discovery_size"] = len(raw)
    manifest_file.write_bytes(canonicalize_jcs_bytes(manifest))
    build_attestation_directory_v06(manifest_file, directory / "false-report-package", package["private"], package["public"],
        expected_fingerprint=package["fingerprint"], generated_at="2026-10-13T00:00:00+00:00")
    bundle = directory / "false-report.pcs.zip"
    create_verified_bundle_v06(directory / "false-report-package", bundle, package["public"], expected_fingerprint=package["fingerprint"])
    receipt = verify_bundle(bundle, package["public"], expected_fingerprint=package["fingerprint"])
    assert receipt["pcs_package_valid"] and not receipt["independent_replay_consistent"]
    assert "fresh independent replay" in receipt["errors"][0]


def test_explicit_confirmation_and_new_output_paths_required(package):
    with pytest.raises(ScientificWorkflowError, match="confirmation"):
        build_bundle(package["project"], package["directory"] / "unconfirmed", package["directory"] / "unconfirmed.zip",
            package["private"], package["public"], expected_fingerprint=package["fingerprint"])
    with pytest.raises(ScientificWorkflowError, match="new output"):
        build_bundle(package["project"], package["directory"] / "work", package["bundle"], package["private"], package["public"],
            expected_fingerprint=package["fingerprint"], confirm_reviewed_draft=True)


def test_external_workflow_cli_and_separate_receiving_process(package):
    import subprocess
    import sys
    directory = package["directory"]
    bundle = directory / "cli-workflow.pcs.zip"
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/run_scientific_workflow_v2.py"),
        "--project", str(package["project"]), "--output", str(bundle),
        "--work-directory", str(directory / "cli-work"), "--private-key", str(package["private"]),
        "--public-key", str(package["public"]), "--fingerprint", package["fingerprint"],
        "--confirm-reviewed-draft"], cwd=ROOT, capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode()
    assert json.loads(proc.stdout)["bounded_contract_satisfied"]
    receipt_file = directory / "cli-fresh-receipt.json"
    received = subprocess.run([sys.executable, str(ROOT / "scripts/run_scientific_workflow_v2.py"),
        "--replay", str(bundle), "--output", str(receipt_file), "--public-key", str(package["public"]),
        "--fingerprint", package["fingerprint"]], cwd=ROOT, capture_output=True, timeout=60)
    assert received.returncode == 0, received.stderr.decode()
    receipt = json.loads(receipt_file.read_bytes())
    assert receipt["bounded_contract_satisfied"] and not receipt["user_code_executed"]


def test_legitimately_signed_falsified_dimension_never_counts_as_satisfied(package):
    from pcs.attest_v06 import build_attestation_directory_v06
    from pcs.bundle_v06 import create_verified_bundle_v06
    from pcs.check_registry_v06 import predicate_from_manifest_check_v06
    source = package["directory"] / "false-dimension-source"
    shutil.copytree(package["directory"] / "work/project", source)
    manifest_file = source / "manifest.confirmed.json"
    manifest = json.loads(manifest_file.read_bytes())
    bad_check = next(x for x in manifest["checks"] if x["id"] == "E_slope_dimensions")
    bad_check["left_unit"] = "kg/m*m"
    next(x for x in manifest["claims"] if x["id"] == "C_slope_dimensions")["predicate"] = predicate_from_manifest_check_v06(bad_check)
    manifest_file.write_bytes(canonicalize_jcs_bytes(manifest))
    built = package["directory"] / "false-dimension-package"
    build_attestation_directory_v06(manifest_file, built, package["private"], package["public"],
        expected_fingerprint=package["fingerprint"], generated_at="2026-10-13T00:00:00+00:00")
    bundle = package["directory"] / "false-dimension.pcs.zip"
    create_verified_bundle_v06(built, bundle, package["public"], expected_fingerprint=package["fingerprint"])
    result = verify_bundle(bundle, package["public"], expected_fingerprint=package["fingerprint"])
    assert result["pcs_package_valid"]
    decisions = {x["claim_id"]: x["decision"] for x in result["pcs_verification"]["claims"]}
    assert decisions["C_slope_dimensions"] == "FALSIFIED_OR_CHECK_FAILED"
    assert not result["bounded_contract_satisfied"]
    assert not result["independent_replay_consistent"]
