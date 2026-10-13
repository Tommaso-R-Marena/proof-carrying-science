#!/usr/bin/env python3
"""Bounded intake, fresh replay and frozen transport computation experiment."""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from fractions import Fraction
import hashlib
import io
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
from pcs.attest_v06 import build_attestation_directory_v06
from pcs.bundle_v06 import create_verified_bundle_v06
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.check_registry_v06 import predicate_from_manifest_check_v06
from pcs.scientific_workflow_v3 import build_bundle, verify_bundle, evaluate, load_contract, make_plan, resolve, reference
from pcs.signing import generate_keypair


def write(path, value):
    if path.exists():
        raise RuntimeError("refusing to replace existing evidence")
    path.write_bytes(canonicalize_jcs_bytes(value))


def receive(bundle, public, fingerprint, output):
    process = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--replay", str(bundle),
        "--public-key", str(public), "--fingerprint", fingerprint, "--output", str(output)],
        cwd=ROOT, capture_output=True, timeout=120)
    if process.returncode:
        raise RuntimeError("fresh receiving process failed: " + process.stderr.decode()[-2000:])
    return json.loads(output.read_bytes())


def changed_last_row(raw, change):
    rows = list(csv.reader(io.StringIO(raw.decode())))
    rows[-1] = change(rows[-1])
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(rows)
    return stream.getvalue().encode()


def run(output):
    if output.exists():
        raise RuntimeError("new experiment output directory required")
    output.mkdir(parents=True)
    started = time.perf_counter()
    source_paths = ["pcs/scientific_workflow_v3.py", "scripts/run_scientific_workflow_v3.py",
        "pcs/scientific_assurance_v1.py", "pcs/scientific_contracts_v1.py", "pcs/scientific_obligations_v1.py", "pcs/checks/units.py",
        "examples/scientific_workflow_v3/contract.json", "examples/scientific_workflow_v3/run_workflow.py"]
    write(output/"PROTOCOL.json", {"format": "pcs-conservative-transport-experiment-v3", "frozen_before_execution": True,
        "source_sha256": {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in source_paths},
        "data_origin": "authored CC0 synthetic numerical computation; no empirical measurements",
        "positive": "Edge-flux producer equals fresh matrix-row receiver; conservation/positivity/maximum principle/quadratic contraction pass; compiled unit predicates pass; numerical/continuum/empirical PCS claims OPEN",
        "negative_controls": ["actual amount leak", "incorrect trajectory that preserves conservation", "legitimately signed false report", "legitimately signed FALSIFIED dimension claim", "CFL violation", "premise and trajectory change invalidate dependent obligations"],
        "baseline": {"implementation": "optional NumPy independently constructed matrix-power", "absolute_state_tolerance": 1e-12},
        "human_participants": 0, "training": False, "spend": 0, "kernel_refinement_of_numerical_adapter": False,
        "independent_human_review": False, "archive_timestamp": "2026-10-13T00:00:00+00:00 (fixed reproducibility parameter, not execution time)"})
    with tempfile.TemporaryDirectory(prefix="pcs-transport-v3-") as temporary:
        temp = Path(temporary)
        project = temp/"source"
        shutil.copytree(ROOT/"examples/scientific_workflow_v3", project)
        # Execute only this explicit authored example. Neither the library
        # intake nor the independently invoked receiver runs submitted source.
        producer = subprocess.run([sys.executable, "run_workflow.py"], cwd=project, check=True, capture_output=True, timeout=10)
        (output/"producer.log").write_bytes(producer.stdout+producer.stderr)
        raw_contract, raw_data = (project/"contract.json").read_bytes(), (project/"trajectory.csv").read_bytes()
        contract = load_contract(raw_contract)
        (output/"contract.json").write_bytes(raw_contract)
        (output/"trajectory.csv").write_bytes(raw_data)
        public, private = output/"producer-public.pem", temp/"ephemeral-private.pem"
        fingerprint = generate_keypair(private, public)["fingerprint"]
        positive = output/"positive.pcs.zip"
        build_bundle(project, temp/"positive-work", positive, private, public, expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
        good = receive(positive, public, fingerprint, output/"positive-independent-replay.json")
        assert good["bounded_contract_satisfied"] and good["pcs_package_valid"]
        repeat = temp/"repeated.pcs.zip"
        build_bundle(project, temp/"repeated-work", repeat, private, public, expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
        assert repeat.read_bytes() == positive.read_bytes()
        outcomes = {}
        for name, altered_data in (
            ("amount-leak", changed_last_row(raw_data, lambda row: [row[0], str(Fraction(row[1])+1), *row[2:]])),
            ("conservative-wrong-trajectory", changed_last_row(raw_data, lambda row: [row[0], *("7/32" for _ in contract["cells"])])),
        ):
            case = temp/name
            shutil.copytree(project, case)
            (case/"trajectory.csv").write_bytes(altered_data)
            artifact = output/(name+".pcs.zip")
            build_bundle(case, temp/(name+"-work"), artifact, private, public, expected_fingerprint=fingerprint, confirm_reviewed_draft=True)
            replay = receive(artifact, public, fingerprint, output/(name+"-independent-replay.json"))
            assert replay["pcs_package_valid"] and replay["independent_replay_consistent"] and not replay["bounded_contract_satisfied"]
            by_id = {x["id"]: x["outcome"] for x in replay["domain_replay"]["checks"]}
            if name == "amount-leak":
                assert by_id["amount_conservation"] == "FAIL"
            else:
                assert by_id["amount_conservation"] == "PASS" and by_id["maximum_principle"] == "PASS" and by_id["step_replay"] == "FAIL"
            outcomes[name] = by_id
        for name in ("producer-false-report", "producer-falsified-dimensions"):
            staged = temp/(name+"-source")
            shutil.copytree(temp/"positive-work/project", staged)
            manifest_file = staged/"manifest.confirmed.json"
            manifest = json.loads(manifest_file.read_bytes())
            if name == "producer-false-report":
                report_file = staged/"pcs-transport-v3/report.json"
                report = json.loads(report_file.read_bytes())
                report["statistics"]["final_amount_mol"] = "0"
                report_file.write_bytes(canonicalize_jcs_bytes(report))
                for item in manifest["artifacts"]:
                    raw = (staged/item["path"]).read_bytes()
                    item["metadata"]["pcs_discovery_sha256"] = hashlib.sha256(raw).hexdigest()
                    item["metadata"]["pcs_discovery_size"] = len(raw)
            else:
                check = next(x for x in manifest["checks"] if x["id"] == "E_step_dimensions")
                check["left_unit"] = "s*m^3/s"
                next(x for x in manifest["claims"] if x["id"] == "C_step_dimensions")["predicate"] = predicate_from_manifest_check_v06(check)
            manifest_file.write_bytes(canonicalize_jcs_bytes(manifest))
            package, artifact = temp/(name+"-package"), output/(name+".pcs.zip")
            build_attestation_directory_v06(manifest_file, package, private, public, expected_fingerprint=fingerprint, generated_at="2026-10-13T00:00:00+00:00")
            create_verified_bundle_v06(package, artifact, public, expected_fingerprint=fingerprint)
            replay = receive(artifact, public, fingerprint, output/(name+"-independent-replay.json"))
            assert replay["pcs_package_valid"] and not replay["independent_replay_consistent"] and not replay["bounded_contract_satisfied"]
            if name == "producer-falsified-dimensions":
                assert next(x["decision"] for x in replay["pcs_verification"]["claims"] if x["claim_id"] == "C_step_dimensions") == "FALSIFIED_OR_CHECK_FAILED"
            outcomes[name] = replay["errors"]
        plan = make_plan(contract, hashlib.sha256(raw_contract).hexdigest(), hashlib.sha256(raw_data).hexdigest())
        old = resolve(plan, good["domain_replay"])
        changed = deepcopy(plan)
        changed["nodes"][0]["statement"] = "The cells now have an unmodeled external amount source."
        invalidated = resolve(changed, good["domain_replay"], old)
        assert next(x for x in invalidated["nodes"] if x["id"] == "workflow")["status"] == "INVALIDATED"
        altered = changed_last_row(raw_data, lambda row: [row[0], str(Fraction(row[1])+1), *row[2:]])
        altered_report = evaluate(raw_contract, altered)
        altered_plan = make_plan(contract, hashlib.sha256(raw_contract).hexdigest(), hashlib.sha256(altered).hexdigest())
        data_invalidated = resolve(altered_plan, altered_report, old)
        assert next(x for x in data_invalidated["nodes"] if x["id"] == "workflow")["status"] == "INVALIDATED"
        write(output/"dependency-invalidation.json", {"premise_change": invalidated, "data_change": data_invalidated})
        unstable = deepcopy(contract)
        unstable["time_step"] = "2"
        try:
            load_contract(canonicalize_jcs_bytes(unstable))
        except ValueError as exc:
            outcomes["CFL-violation"] = str(exc)
        else:
            raise AssertionError("unstable discretization accepted")
        write(output/"negative-controls.json", outcomes)
        try:
            import numpy as np
        except ImportError:
            baseline = {"available": False, "reason": "optional NumPy absent", "pcs_authority": False}
        else:
            names = [x["id"] for x in contract["cells"]]
            volumes = np.array([float(Fraction(x["volume"])) for x in contract["cells"]])
            generator = np.zeros((len(names), len(names)))
            for edge in contract["edges"]:
                i, j = names.index(edge["left"]), names.index(edge["right"])
                for a, b in ((i, j), (j, i)):
                    coefficient = float(Fraction(edge["conductance"]))/volumes[a]
                    generator[a, b] += coefficient
                    generator[a, a] -= coefficient
            matrix = np.eye(len(names)) + float(Fraction(contract["time_step"]))*generator
            initial = np.array([float(Fraction(x["initial_concentration"])) for x in contract["cells"]])
            exact = reference(contract)
            errors = [float(np.max(np.abs(np.linalg.matrix_power(matrix, i) @ initial-np.array([float(x) for x in exact[i]])))) for i in range(len(exact))]
            assert max(errors) < 1e-12
            baseline = {"available": True, "numpy": np.__version__, "implementation": "independently constructed transition matrix + numpy.linalg.matrix_power",
                "max_state_absolute_error": max(errors), "states": len(errors), "predeclared_absolute_tolerance": 1e-12, "passed": True, "pcs_authority": False}
        write(output/"independent-baseline.json", baseline)
    usage, children = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    summary = {"format": "pcs-conservative-transport-experiment-result-v3", "passed": True,
        "data_origin": "synthetic_numerical_computation_not_empirical", "cells": 5, "edges": 6, "steps": 16, "states": 17,
        "initial_and_final_amount_mol": "7/4", "positive_bounded_checks": 10, "compiled_dimension_claims": 3,
        "independent_receiver_processes": 5, "deterministic_archive_reproduction": True,
        "numerical_claim": "OPEN", "continuum_claim": "OPEN", "empirical_claim": "OPEN", "scientific_acceptance": False,
        "private_keys_exported": False, "training": False, "human_participants": 0, "financial_spend": 0,
        "python": platform.python_version(), "wall_seconds": time.perf_counter()-started,
        "self_cpu_seconds": usage.ru_utime+usage.ru_stime, "child_cpu_seconds": children.ru_utime+children.ru_stime,
        "child_max_rss_kib": children.ru_maxrss, "producer_public_key_fingerprint": fingerprint}
    write(output/"SUMMARY.json", summary)
    write(output/"SHA256.json", {"format": "pcs-conservative-transport-evidence-seal-v3", "authority": "unsigned byte-integrity inventory; not external review",
        "files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(output.iterdir()) if path.is_file()}})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--work-directory", type=Path)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--private-key", type=Path)
    parser.add_argument("--public-key", type=Path)
    parser.add_argument("--fingerprint")
    parser.add_argument("--confirm-reviewed-draft", action="store_true")
    args = parser.parse_args()
    if args.project:
        if args.replay or not all((args.work_directory, args.private_key, args.public_key, args.fingerprint)):
            parser.error("--project requires work-directory, keys and fingerprint; cannot combine with --replay")
        result = build_bundle(args.project, args.work_directory, args.output, args.private_key, args.public_key,
            expected_fingerprint=args.fingerprint, confirm_reviewed_draft=args.confirm_reviewed_draft)
    elif args.replay:
        if not args.public_key or not args.fingerprint:
            parser.error("--replay requires public-key and fingerprint")
        result = verify_bundle(args.replay, args.public_key, expected_fingerprint=args.fingerprint)
        write(args.output, result)
    else:
        result = run(args.output)
    print(json.dumps(result if not args.replay else {k: result[k] for k in ("pcs_package_valid", "independent_replay_consistent", "bounded_contract_satisfied", "scientific_acceptance")}, indent=2))


if __name__ == "__main__":
    main()
