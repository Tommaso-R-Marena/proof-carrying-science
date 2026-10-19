"""Three preregistered synthetic cases with explicitly separate evidence scopes.

The only Lean-positive path is unchanged bytes sent to the actual compiled CLI.
Prior PK and finite-SCM components remain imported at their original paths.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import importlib
from itertools import product
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any

from .differential import executable_identity, query_lean, response_issues
from . import reference

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _module_identity(module) -> dict[str, str]:
    path = Path(module.__file__).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": _sha(path.read_bytes())}


def exact_case(checker: Path, checker_args: tuple[str, ...] = (), checker_cwd: Path | None = None) -> dict[str, Any]:
    raw = (HERE / "fixtures/multi-step-nonsingleton.wire").read_bytes()
    decision = reference.assess(raw)
    response = query_lean(checker, [raw], checker_args=checker_args, checker_cwd=checker_cwd)[0]
    issues = response_issues(raw, response, decision)
    if not decision.accepted or response.get("accepted") is not True or issues:
        raise RuntimeError(f"exact case failed actual compiled Lean receiving: {issues}; {response}")
    return {"id": "exact-discrete-a-to-b", "synthetic": True,
            "category": "compiled_lean_receiver_accepted",
            "raw_sha256": _sha(raw), "raw_hex": raw.hex(),
            "actual_lean_response": response, "independent_reference": decision.result,
            "scope": "Exact declared rational A→B schedule, conserved total, final-coordinate binding and enclosure; the receiving theorem is checked separately in Lean. This process exercises compiled byte receiving, whose compiler/IO/OS and protected-root obligations remain open.",
            "empirical_validity": "unverified", "scientific_acceptance": False,
            "production_authority": False}


def pk_case(out: Path) -> dict[str, Any]:
    module = importlib.import_module("pcs.adapters.pkpd")
    spec = {"model_type": "one_compartment_iv_bolus",
            "dose": {"value":100,"unit":"mg"}, "volume":{"value":10,"unit":"L"},
            "clearance":{"value":1,"unit":"L/h"}, "time_unit":"h", "concentration_unit":"mg/L"}
    times = (0, 1, 2, 4)
    with localcontext() as ctx:
        ctx.prec = 60
        # Independent reconstruction from the declared quantities, in mg/L and h.
        concentrations = [Decimal(10) * (-Decimal(t)/Decimal(10)).exp() for t in times]
        clean = "time,concentration\n" + "".join(f"{t},{c}\n" for t,c in zip(times,concentrations,strict=True))
        bad_values = list(concentrations)
        bad_values[-1] *= Decimal("1.1")
        tampered = "time,concentration\n" + "".join(f"{t},{c}\n" for t,c in zip(times,bad_values,strict=True))
    clean_path = out / "synthetic-pk.csv"
    bad_path = out / "synthetic-pk-tampered.csv"
    clean_path.write_text(clean)
    bad_path.write_text(tampered)
    accepted, details = module.verify_one_compartment_iv_output(spec, clean_path)
    bad_accepted, bad_details = module.verify_one_compartment_iv_output(spec, bad_path)
    if not accepted or bad_accepted:
        raise RuntimeError("prior PK component failed clean/tampered sampled analytic replay")
    return {"id":"transparent-one-compartment-pk", "synthetic":True,
            "category":"computationally_reproduced", "component":_module_identity(module),
            "specification":spec, "sample_times_h":list(times),
            "concentration_mg_per_L":[str(value) for value in concentrations],
            "input_sha256":_sha(clean.encode()), "tampered_input_sha256":_sha(tampered.encode()),
            "replay_accepted":accepted,"replay":details,
            "tampered_replay_accepted":bad_accepted,"tampered_replay":bad_details,
            "scope":"Four synthetic sample values reconstructed under the restricted analytic IV-bolus equation, using the original PK adapter. Computational replay only; no fitted data, physiology, clinical safety, continuum-error theorem or Lean proof of this PK calculation.",
            "lean_acceptance":"unverified", "empirical_validity":"unverified",
            "scientific_acceptance":False,"production_authority":False}


def _table(distribution) -> list[dict[str, Any]]:
    names = tuple(distribution.variables)
    rows = []
    for values in product(*(distribution.domains[name] for name in names)):
        assignment = tuple(sorted(zip(names,values,strict=True)))
        probability = distribution.mass.get(assignment, 0)
        rows.append({"assignment":dict(assignment),
                     "probability":f"{probability.numerator}/{probability.denominator}"})
    return rows


def scm_case() -> dict[str, Any]:
    from research.integration_v1.scoped_evidence import component
    component("pcs_causal")
    search = importlib.import_module("pcs_causal.nonident.witness_search")
    verifier = importlib.import_module("pcs_causal.nonident.witness_verifier")
    witness = search.classic_confounding_witness()
    result = verifier.verify_witness(witness)
    invalid = verifier.verify_witness(replace(witness,model_b=witness.model_a))
    if not result.accepted or result.status.value != "NOT_IDENTIFIABLE" or invalid.accepted:
        raise RuntimeError("finite SCM witness did not replay with equal-model negative control")
    return {"id":"finite-scm-nonidentifiability", "synthetic":True,
            "category":"computationally_reproduced_negative",
            "components":[_module_identity(search),_module_identity(verifier)],
            "witness_label":witness.label, "query":f"P({witness.outcome}|do({witness.treatment}={witness.treatment_value}))",
            "observational_a":_table(witness.observational_a()),
            "observational_b":_table(witness.observational_b()),
            "interventional_a":_table(witness.interventional_a()),
            "interventional_b":_table(witness.interventional_b()),
            "verdict":result.to_dict(),"equal_models_negative_control":invalid.to_dict(),
            "scope":"Exact finite witness: equal permitted observational distributions, differing intervention distributions. Nonidentifiability is conditional on this finite model class and information set; it grants no causal-effect support or theorem for every causal formalism.",
            "lean_acceptance":"unverified", "empirical_validity":"unverified",
            "causal_effect_supported":False,"scientific_acceptance":False,"production_authority":False}


def run(checker: Path, out: Path, *, checker_args: tuple[str, ...] = (), checker_cwd: Path | None = None) -> dict[str, Any]:
    identity = executable_identity(checker, checker_args, checker_cwd)
    out.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    cases = [exact_case(checker,checker_args,checker_cwd), pk_case(out), scm_case()]
    report = {"format":"pcs-scientific-receiver-pilot-v1", "started_utc":started,
              "finished_utc":datetime.now(timezone.utc).isoformat(),
              "wall_seconds":time.perf_counter()-clock,
              "preregistration_sha256":_sha((HERE / "preregistration.json").read_bytes()),
              "checker":identity,"python":sys.version,"platform":platform.platform(),
              "source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
              "cases":cases,"synthetic_only":True,
              "open_obligations":["Python-to-Lean refinement outside the byte receiver theorem",
                  "Compiler/IO/OS correspondence and independent execution root",
                  "Empirical adequacy of any chemical or pharmacological model",
                  "Measurement, continuum and discretization error",
                  "Cryptographic provenance and production deployment authority"],
              "scientific_acceptance":False,"production_authority":False}
    (out / "pilot.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    rows = ["# Preregistered synthetic scientific receiver pilot", "",
            f"Actual compiled Lean CLI SHA256: `{identity['sha256']}`.", "",
            "| Case | Observed evidence | Scope |", "|---|---|---|",
            "| Exact discrete A→B | Actual compiled Lean byte receiving accepted; independent exact replay agreed | Conditional final A=13/2, B=7/2, total=10, B enclosure [2,5] |",
            "| Four sampled PK values | Prior PK adapter reproduced reconstructed values and rejected a 10% tamper | Computational restricted-model replay; empirical/Lean validity unverified |",
            "| Finite SCM witness | Observational TV=0; intervention TV=1/2; equal-model control rejected | Computational finite nonidentifiability witness; no causal-effect support |", "",
            "The categories remain separate. No broad scientific acceptance, Python refinement, compiler/IO/OS correspondence, protected execution root, physiology, clinical safety or production authority follows from these observations.", ""]
    (out / "pilot.md").write_text("\n".join(rows))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checker",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--checker-arg",action="append",default=[])
    parser.add_argument("--checker-cwd",type=Path)
    args=parser.parse_args()
    report=run(args.checker,args.out,checker_args=tuple(args.checker_arg),checker_cwd=args.checker_cwd)
    print(json.dumps({"case_count":len(report["cases"]),"out":str(args.out.resolve()),
                      "scientific_acceptance":False,"production_authority":False}))


if __name__ == "__main__":
    main()
