#!/usr/bin/env python3
"""Execute or independently receive the real-data bounded scientific workflow."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.scientific_workflow_v2 import build_bundle, verify_bundle, load_contract, make_plan, evaluate
from pcs.scientific_obligations_v1 import resolve_plan
from pcs.signing import generate_keypair


def write(path, value):
    if path.exists():
        raise RuntimeError("refusing to replace historical evidence")
    path.write_bytes(canonicalize_jcs_bytes(value))


def receive(bundle, public, fingerprint, output):
    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--replay", str(bundle),
        "--public-key", str(public), "--fingerprint", fingerprint, "--output", str(output)],
        cwd=ROOT, capture_output=True, timeout=120)
    if proc.returncode:
        raise RuntimeError("fresh receiver failed: " + proc.stderr.decode()[-2000:])
    return json.loads(output.read_bytes())


def run(output):
    if output.exists():
        raise RuntimeError("new experiment directory required")
    output.mkdir(parents=True)
    started = time.perf_counter()
    source_paths = ["pcs/scientific_workflow_v2.py", "pcs/scientific_assurance_v1.py", "pcs/scientific_contracts_v1.py", "pcs/scientific_obligations_v1.py", "pcs/checks/units.py", "scripts/run_scientific_workflow_v2.py",
        "examples/scientific_workflow_v2/run_workflow.py", "examples/scientific_workflow_v2/contract.json"]
    write(output / "PROTOCOL.json", {"format": "pcs-scientific-workflow-experiment-v2", "frozen_before_execution": True,
        "source_sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},
        "dataset": "Real CC0 Palmer Penguins field measurements; upstream revision and hashes retained",
        "positive": "Fresh-process centered-statistics replay equals producer normal equations; builtin dimensions accepted; numerical and empirical claims remain OPEN",
        "negative_controls": ["wrong slope", "unit-scale mismatch", "changed applicability premise invalidates dependencies", "changed dataset invalidates dependent computation", "valid producer signature with fabricated report", "valid producer signature with FALSIFIED compiled dimension claim"],
        "independent_numerical_baseline": {"implementation": "numpy.linalg.lstsq if installed", "absolute_coefficient_tolerance": 1e-10},
        "human_participants": 0, "new_data_collection": False, "financial_spend": 0,
        "kernel_refinement_of_statistical_adapter": False, "independent_human_review": False})
    with tempfile.TemporaryDirectory(prefix="pcs-workflow-v2-") as temporary:
        temp = Path(temporary)
        project = temp/"source"
        shutil.copytree(ROOT/"examples/scientific_workflow_v2", project)
        # Only this explicitly authored file is executed. Library discovery and
        # the independently invoked receiver never execute project source.
        producer = subprocess.run([sys.executable, "run_workflow.py"], cwd=project,
                                  check=True, capture_output=True, timeout=10)
        (output/"producer.log").write_bytes(producer.stdout + producer.stderr)
        public, private = output/"producer-public.pem", temp/"ephemeral-private.pem"
        fingerprint = generate_keypair(private, public)["fingerprint"]
        positive = output/"positive.pcs.zip"
        built = build_bundle(project, temp/"positive-work", positive, private, public,
                             expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
        replay = receive(positive, public, fingerprint, output/"positive-independent-replay.json")
        assert replay["bounded_contract_satisfied"] and replay["pcs_package_valid"]
        # A separately implemented floating-point solver is a numerical sanity
        # baseline, not scientific authority or a proof of universal correctness.
        try:
            import numpy as np
        except ImportError:
            baseline = {"available": False, "reason": "optional NumPy absent", "pcs_authority": False}
        else:
            import csv
            from fractions import Fraction
            rows = list(csv.DictReader((project/"penguins.csv").open(newline="")))
            points = [(float(row["flipper_length_mm"])/1000, float(row["body_mass_g"])/1000)
                      for row in rows if row["flipper_length_mm"] != "NA" and row["body_mass_g"] != "NA"]
            fitted = np.linalg.lstsq(np.array([[1, x] for x, y in points]), np.array([y for x, y in points]), rcond=None)[0]
            reference = replay["domain_replay"]["reference"]
            expected = [float(Fraction(reference["intercept_kg"])), float(Fraction(reference["slope_kg_per_m"]))]
            errors = [abs(float(a)-b) for a, b in zip(fitted, expected)]
            assert max(errors) < 1e-10
            baseline = {"available": True, "implementation": "numpy.linalg.lstsq", "numpy": np.__version__,
                "complete_rows": len(points), "absolute_coefficient_errors": errors,
                "predeclared_absolute_tolerance": 1e-10, "passed": True, "pcs_authority": False}
        write(output/"independent-numerical-baseline.json", baseline)
        repeated = temp/"repeated.pcs.zip"
        build_bundle(project, temp/"repeated-work", repeated, private, public,
                     expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
        assert positive.read_bytes() == repeated.read_bytes()
        wrong = temp/"wrong-slope"
        shutil.copytree(project, wrong)
        result = json.loads((wrong/"result.json").read_bytes())
        result["slope_kg_per_m"] = "0"
        (wrong/"result.json").write_bytes(canonicalize_jcs_bytes(result))
        negative = output/"wrong-slope.pcs.zip"
        build_bundle(wrong, temp/"wrong-work", negative, private, public,
                     expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
        failed = receive(negative, public, fingerprint, output/"wrong-slope-independent-replay.json")
        assert failed["pcs_package_valid"] and failed["independent_replay_consistent"] and not failed["bounded_contract_satisfied"]
        raw = (project/"contract.json").read_bytes()
        contract = load_contract(raw)
        plan = make_plan(contract, hashlib.sha256(raw).hexdigest(), replay["domain_replay"]["data_sha256"])
        old = resolve_plan(plan, replay["domain_replay"])
        changed = deepcopy(plan)
        changed["nodes"][0]["statement"] = "Measurement-unit labels may now mean centimetres instead of millimetres."
        invalidated = resolve_plan(changed, replay["domain_replay"], previous=old)
        assert next(x for x in invalidated["nodes"] if x["id"] == "workflow")["status"] == "INVALIDATED"
        write(output/"premise-invalidation.json", {"before": old, "after": invalidated})
        changed_data = (project/"penguins.csv").read_bytes().replace(b",181,3750,", b",181,3751,", 1)
        assert changed_data != (project/"penguins.csv").read_bytes()
        changed_replay = evaluate(raw, changed_data, (project/"result.json").read_bytes())
        changed_data_plan = make_plan(contract, hashlib.sha256(raw).hexdigest(), hashlib.sha256(changed_data).hexdigest())
        changed_data_results = resolve_plan(changed_data_plan, changed_replay, previous=old)
        assert next(x for x in changed_data_results["nodes"] if x["id"] == "workflow")["status"] == "INVALIDATED"
        write(output/"data-invalidation.json", {"before_data_sha256": replay["domain_replay"]["data_sha256"],
            "after_data_sha256": hashlib.sha256(changed_data).hexdigest(), "after": changed_data_results})
        altered = deepcopy(contract)
        altered["x"]["scale"] = "1/100"
        try:
            load_contract(canonicalize_jcs_bytes(altered))
        except ValueError as exc:
            scale_rejection = str(exc)
        else:
            raise AssertionError("incorrect scale accepted")
        # A false report with a valid producer signature needs a full package
        # rebuild, not merely a ZIP edit. Existing PCS authority should accept
        # the signed finite dimension checks; independent replay must reject.
        from pcs.attest_v06 import build_attestation_directory_v06
        from pcs.bundle_v06 import create_verified_bundle_v06
        forged_project = temp/"forged-project"
        shutil.copytree(temp/"positive-work/project", forged_project)
        report_file = forged_project/"pcs-workflow-v2/report.json"
        report = json.loads(report_file.read_bytes())
        report["reference"]["slope_kg_per_m"] = "0"
        report_file.write_bytes(canonicalize_jcs_bytes(report))
        manifest_file = forged_project/"manifest.confirmed.json"
        manifest = json.loads(manifest_file.read_bytes())
        for item in manifest["artifacts"]:
            bytes_ = (forged_project/item["path"]).read_bytes()
            item["metadata"]["pcs_discovery_sha256"] = hashlib.sha256(bytes_).hexdigest()
            item["metadata"]["pcs_discovery_size"] = len(bytes_)
        manifest_file.write_bytes(canonicalize_jcs_bytes(manifest))
        package = temp/"forged-package"
        build_attestation_directory_v06(manifest_file, package, private, public,
            expected_fingerprint=fingerprint, generated_at="2026-10-13T00:00:00+00:00")
        forged_bundle = output/"producer-false-report.pcs.zip"
        create_verified_bundle_v06(package, forged_bundle, public, expected_fingerprint=fingerprint)
        forged_receipt = receive(forged_bundle, public, fingerprint, output/"producer-false-report-independent-replay.json")
        assert forged_receipt["pcs_package_valid"] and not forged_receipt["independent_replay_consistent"]
        dimension_project = temp/"false-dimension-project"
        shutil.copytree(temp/"positive-work/project", dimension_project)
        manifest_file = dimension_project/"manifest.confirmed.json"
        manifest = json.loads(manifest_file.read_bytes())
        bad_check = next(x for x in manifest["checks"] if x["id"] == "E_slope_dimensions")
        bad_check["left_unit"] = "kg/m*m"
        from pcs.check_registry_v06 import predicate_from_manifest_check_v06
        next(x for x in manifest["claims"] if x["id"] == "C_slope_dimensions")["predicate"] = predicate_from_manifest_check_v06(bad_check)
        manifest_file.write_bytes(canonicalize_jcs_bytes(manifest))
        dimension_package = temp/"false-dimension-package"
        build_attestation_directory_v06(manifest_file, dimension_package, private, public,
            expected_fingerprint=fingerprint, generated_at="2026-10-13T00:00:00+00:00")
        dimension_bundle = output/"producer-falsified-dimension.pcs.zip"
        create_verified_bundle_v06(dimension_package, dimension_bundle, public, expected_fingerprint=fingerprint)
        dimension_receipt = receive(dimension_bundle, public, fingerprint, output/"producer-falsified-dimension-independent-replay.json")
        dimension_status = next(x["decision"] for x in dimension_receipt["pcs_verification"]["claims"] if x["claim_id"] == "C_slope_dimensions")
        assert dimension_receipt["pcs_package_valid"] and dimension_status == "FALSIFIED_OR_CHECK_FAILED"
        assert not dimension_receipt["bounded_contract_satisfied"]
        write(output/"negative-controls.json", {"wrong_slope_rejected": not failed["bounded_contract_satisfied"],
            "incorrect_scale_rejected": scale_rejection, "changed_premise_invalidated": True,
            "changed_dataset_invalidated": True,
            "legitimately_resigned_false_report_rejected": forged_receipt["errors"],
            "legitimately_resigned_falsified_dimension_rejected": dimension_receipt["errors"],
            "falsified_dimension_claim_status": dimension_status})
        # Private material lives only in this temporary directory and is never
        # included in the sealed evidence or source project.
    usage = resource.getrusage(resource.RUSAGE_SELF)
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    summary = {"format": "pcs-scientific-workflow-experiment-result-v2", "passed": True,
        "source_revision": built["source_revision"], "data_rows": replay["domain_replay"]["reference"]["total_rows"],
        "complete_rows": replay["domain_replay"]["reference"]["complete_rows"],
        "excluded_rows": replay["domain_replay"]["reference"]["excluded_rows"],
        "independent_receiver_processes": 4, "kernel_builtin_checks": 2,
        "deterministic_archive_reproduction": True, "private_keys_exported": False,
        "numerical_claim": "OPEN", "empirical_causal_population_claim": "OPEN",
        "scientific_acceptance": False, "training_authorization": False,
        "python": platform.python_version(), "wall_seconds": time.perf_counter()-started,
        "self_cpu_seconds": usage.ru_utime+usage.ru_stime, "child_cpu_seconds": child.ru_utime+child.ru_stime,
        "child_max_rss_kib": child.ru_maxrss}
    write(output/"SUMMARY.json", summary)
    seal = {"format": "pcs-scientific-workflow-evidence-seal-v2", "authority": "unsigned byte-integrity manifest; not external attestation",
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()}}
    write(output/"SHA256.json", seal)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--public-key", type=Path)
    parser.add_argument("--private-key", type=Path)
    parser.add_argument("--fingerprint")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--work-directory", type=Path)
    parser.add_argument("--confirm-reviewed-draft", action="store_true")
    args = parser.parse_args()
    if args.project:
        if args.replay or not all((args.public_key, args.private_key, args.fingerprint, args.work_directory)):
            parser.error("--project requires keys, --fingerprint and --work-directory; it cannot combine with --replay")
        result = build_bundle(args.project, args.work_directory, args.output, args.private_key, args.public_key,
            expected_fingerprint=args.fingerprint, confirm_reviewed_draft=args.confirm_reviewed_draft)
        print(json.dumps(result, indent=2))
    elif args.replay:
        if not args.public_key or not args.fingerprint:
            parser.error("--replay requires --public-key and --fingerprint")
        receipt = verify_bundle(args.replay, args.public_key, expected_fingerprint=args.fingerprint)
        write(args.output, receipt)
        print(json.dumps({"pcs_package_valid": receipt["pcs_package_valid"], "independent_replay_consistent": receipt["independent_replay_consistent"]}))
    else:
        print(json.dumps(run(args.output), indent=2))


if __name__ == "__main__":
    main()
