"""Deterministic bounded-wire / large-intermediate-rational resource probe.

Run only as an optional experiment harness. It sends data to the unchanged
actual Lean CLI; it never generates source or changes receiving authority.
Every case uses a fresh process, at most one process runs at a time, and all
launches share a wall-clock budget. No receiver outputs are used for training.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
from math import gcd
import os
from pathlib import Path
import struct
import subprocess
import time
from typing import Any

from . import producer, reference
from .differential import executable_identity, response_issues


@dataclass(frozen=True)
class StressCase:
    name: str
    family: str
    wire: bytes
    expected: bool


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def denominators(count: int) -> tuple[int, ...]:
    """Descending near-bound integers, pairwise coprime by gcd; no primality claim."""
    chosen: list[int] = []
    candidate = 10**18
    while len(chosen) < count:
        if all(gcd(candidate, previous) == 1 for previous in chosen):
            chosen.append(candidate)
        candidate -= 1
    return tuple(chosen)


def cases() -> tuple[list[StressCase], tuple[int, ...]]:
    ds = denominators(32)
    result: list[StressCase] = []
    last = None
    for n in (0, 8, 16, 32, 64):
        selected = ds[:n // 2]
        firings = (*(F(1, d) for d in selected), *(F(d-1, d) for d in selected))
        for physical in (False, True):
            witness = producer.build(F(n // 2), F(0), firings, physical=physical)
            result.append(StressCase(f"n{n:02d}-physical-{int(physical)}", "coprime-cancellation",
                                     producer.encode(witness), True))
            last = witness
    assert last is not None
    wrong = replace(last, envValue=F(1), boxLo=F(1), boxHi=F(1), lower=F(1), upper=F(1))
    result.append(StressCase("n64-wrong-bound-environment", "state-expression-binding",
                             producer.encode(wrong), False))
    for physical in (False, True):
        witness = producer.build(F(1),F(0),(F(2),F(-1)),physical=physical)
        result.append(StressCase(f"temporary-negative-physical-{int(physical)}", "physical-state-control",
                                 producer.encode(witness), not physical))
    return result, ds


def intermediate_stats(wire: bytes) -> dict[str, Any]:
    """Instrumentation only; the unchanged reference independently decides acceptance."""
    contract = reference.decode(wire)
    a, b = contract.initialA, contract.initialB
    values = [a, b]
    min_a, min_b = a, b
    for firing in contract.firings:
        a, b = a-firing, b+firing
        values.extend((a,b))
        min_a, min_b = min(min_a,a), min(min_b,b)
    return {"firings":len(contract.firings),"replayed_states":len(contract.firings)+1,
            "max_intermediate_denominator_digits":max(len(str(q.denominator)) for q in values),
            "max_intermediate_numerator_digits":max(len(str(abs(q.numerator))) for q in values),
            "minimum_A":str(min_a),"minimum_B":str(min_b),
            "computed_final_A":str(a),"computed_final_B":str(b),
            "all_submitted_rational_operands_bounded":all(
                abs(q.numerator)<=10**18 and 0<q.denominator<=10**18
                for q in (contract.initialA,contract.initialB,contract.envValue,contract.boxLo,
                          contract.boxHi,contract.lower,contract.upper,contract.declaredTotal,*contract.firings))}


def unique_json(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key,value in pairs:
        if key in result:
            raise ValueError("duplicate response key")
        result[key]=value
    return result


def run(checker: Path, checker_args: tuple[str, ...], checker_cwd: Path | None,
        environment_json: Path, out: Path, budget_seconds: float = 120) -> dict[str, Any]:
    if not 0 < budget_seconds <= 120:
        raise ValueError("probe budget must be positive and at most120seconds")
    config_raw=environment_json.read_bytes()
    config=json.loads(config_raw)
    if type(config) is not dict or set(config)!={"LEAN_PATH"} or type(config["LEAN_PATH"]) is not str:
        raise ValueError("qualified environment JSON must contain exactly a string LEAN_PATH")
    env=dict(os.environ);env.update(config)
    identity=executable_identity(checker,checker_args,checker_cwd)
    identity["lean_path"]=config["LEAN_PATH"]
    probes,ds=cases()
    source_path=Path(__file__).resolve()
    out.mkdir(parents=True,exist_ok=False)
    started=datetime.now(timezone.utc).isoformat()
    plan={"format":"pcs-scientific-receiver-resource-plan-v1","frozen_before_launch_utc":started,
          "n":[0,8,16,32,64],"m":"n/2","denominators":[str(d) for d in ds],
          "denominator_selection":"Descending from10^18; select candidate iff gcd with every prior selected denominator is1. No primality assumption.",
          "positive_schedule":"initialA=m,initialB=0; firstm firings1/d_i, nextm firings(d_i-1)/d_i; finalA=0,finalB=m; singleton final-A box/claim0; physical and algebraic modes.",
          "controls":"One wrong bounded environment with internally matching false singleton enclosure; one temporarily negative schedule under each mode.",
          "case_count":len(probes),"expected_accepts":sum(p.expected for p in probes),
          "process_concurrency":1,"max_launches":len(probes),"global_wall_budget_seconds":budget_seconds,
          "timing_scope":"Each case starts one fresh actual Lean process. Wall time includes cold startup, Main elaboration, input/output, receiving and response parsing; not isolated receiver CPU. No repetition or asymptotic claim.",
          "checker":identity,"environment_json_sha256":sha256(config_raw),
          "experiment_source_sha256":sha256(source_path.read_bytes()),
          "no_training":True,"scientific_acceptance":False,"production_authority":False}
    plan_raw=json.dumps(plan,indent=2,sort_keys=True)+"\n"
    (out/"plan.json").write_text(plan_raw)
    inputs=[{"id":p.name,"family":p.family,"expected":p.expected,"raw_hex":p.wire.hex(),
             "raw_sha256":sha256(p.wire),"raw_bytes":len(p.wire),"instrumentation":intermediate_stats(p.wire)} for p in probes]
    (out/"inputs.json").write_text(json.dumps(inputs,indent=2,sort_keys=True)+"\n")
    clock=time.perf_counter();deadline=clock+budget_seconds
    records=[];processes=[];timed_out=False
    for probe,entry in zip(probes,inputs,strict=True):
        decision=reference.assess(probe.wire)
        record={**entry,"reference_accepted":decision.accepted,"reference_reason":decision.reason,
                "reference_result":decision.result,"actual_lean_response":None,"issues":[]}
        if decision.accepted is not probe.expected:
            record["issues"].append("reference_expectation_disagreement")
        remaining=deadline-time.perf_counter()
        if remaining<=0 or timed_out:
            record.update({"status":"not_run_global_deadline","cold_process_wall_seconds":None})
            record["issues"].append("not_evaluated")
            records.append(record)
            continue
        frame=struct.pack(">I",len(probe.wire))+probe.wire
        launch=time.perf_counter();stdout=b"";stderr=b"";exit_code=None
        try:
            completed=subprocess.run([str(checker.resolve(strict=True)),*checker_args],input=frame,
                                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=checker_cwd,
                                     env=env,timeout=remaining,check=False)
            stdout,stderr,exit_code=completed.stdout,completed.stderr,completed.returncode
            if exit_code!=0:
                record["issues"].append("nonzero_lean_exit")
            else:
                lines=stdout.splitlines()
                if len(lines)!=1:
                    record["issues"].append("response_line_count")
                else:
                    try:
                        response=json.loads(lines[0],object_pairs_hook=unique_json)
                        if type(response) is not dict:
                            raise ValueError("non-object response")
                        record["actual_lean_response"]=response
                        record["issues"].extend(response_issues(probe.wire,response,decision))
                    except (ValueError,TypeError,UnicodeDecodeError) as exc:
                        record["issues"].append("response_parse_failure:"+str(exc))
            record["status"]="evaluated" if not record["issues"] else "failure"
        except subprocess.TimeoutExpired as exc:
            stdout,stderr=exc.stdout or b"",exc.stderr or b""
            timed_out=True;record["status"]="timeout";record["issues"].append("actual_lean_timeout")
        except OSError as exc:
            record["status"]="launch_failure";record["issues"].append("actual_lean_launch_failure:"+str(exc))
        record["cold_process_wall_seconds"]=time.perf_counter()-launch
        processes.append({"id":probe.name,"exit_code":exit_code,"stdout_hex":stdout.hex(),"stderr_hex":stderr.hex(),
                          "stdout_utf8":stdout.decode("utf-8",errors="replace"),"stderr_utf8":stderr.decode("utf-8",errors="replace"),
                          "status":record["status"],"cold_process_wall_seconds":record["cold_process_wall_seconds"]})
        records.append(record)
        # Preserve every completed/failed/partial actual process before launching the next.
        (out/"process-outputs.jsonl").write_text("".join(json.dumps(p,sort_keys=True)+"\n" for p in processes))
        (out/"progress.json").write_text(json.dumps({"completed_cases":len(records),"records":records},indent=2,sort_keys=True)+"\n")
    report={"format":"pcs-scientific-receiver-resource-stress-v1","started_utc":started,
            "finished_utc":datetime.now(timezone.utc).isoformat(),"plan_sha256":sha256(plan_raw.encode()),
            "total_observed_wall_seconds":time.perf_counter()-clock,
            "global_wall_budget_seconds":budget_seconds,"case_count":len(probes),"actual_launches":len(processes),
            "expected_accepts":sum(p.expected for p in probes),
            "actual_lean_accepts":sum(r["actual_lean_response"] is not None and r["actual_lean_response"].get("accepted") is True for r in records),
            "cases_with_issues":sum(bool(r["issues"]) for r in records),"timed_out":timed_out,
            "largest_intermediate_denominator_digits":max(i["instrumentation"]["max_intermediate_denominator_digits"] for i in inputs),
            "timing_scope":plan["timing_scope"],"checker":identity,"records":records,
            "scope":"Finite targeted resource falsification attempt, not an asymptotic bound, hard worst-case guarantee, standalone-native benchmark, protected execution root, empirical model validation or production authority. Successful cold-start timings do not isolate receiving cost.",
            "no_training":True,"scientific_acceptance":False,"production_authority":False}
    (out/"stress.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    lines=["# Bounded-wire / large-intermediate-rational resource probe","",
           f"Actual Lean launches: {report['actual_launches']}; cases: {report['case_count']}; cases with issues: {report['cases_with_issues']}; timeout: {timed_out}.","",
           "Each row includes a fresh actual Lean `--run` process and its startup/Main elaboration/IO/receiving. These are descriptive end-to-end measurements, not isolated receiver timing or asymptotic results.","",
           "| Case | Wire bytes | Largest intermediate denominator digits | Actual accepted | Cold process seconds | Status |",
           "|---|---:|---:|---|---:|---|"]
    for r in records:
        answer=r["actual_lean_response"]
        accepted=str(answer.get("accepted")) if answer is not None else "not observed"
        elapsed=f"{r['cold_process_wall_seconds']:.6f}" if r['cold_process_wall_seconds'] is not None else "not run"
        lines.append(f"| {r['id']} | {r['raw_bytes']} | {r['instrumentation']['max_intermediate_denominator_digits']} | {accepted} | {elapsed} | {r['status']} |")
    lines.extend(["",f"Total observed wall time: {report['total_observed_wall_seconds']:.6f} seconds; global budget {budget_seconds} seconds.","",
                  "All submitted rational operands remain within the unchanged 10^18 bound. Pairwise coprimality was checked by gcd, without claiming primality. The two schedule halves cancel to a bounded final value; the transient-negative controls distinguish physical from algebraic scope. Every actual response, raw input and process output is preserved. No source generation or training occurred.","",report["scope"],""])
    (out/"stress.md").write_text("\n".join(lines))
    return report


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checker",required=True,type=Path)
    parser.add_argument("--checker-arg",action="append",default=[])
    parser.add_argument("--checker-cwd",type=Path)
    parser.add_argument("--environment-json",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--budget-seconds",type=float,default=120)
    args=parser.parse_args()
    report=run(args.checker,tuple(args.checker_arg),args.checker_cwd,args.environment_json,args.out,args.budget_seconds)
    print(json.dumps({k:report[k] for k in ("case_count","actual_launches","cases_with_issues","timed_out","total_observed_wall_seconds","largest_intermediate_denominator_digits")}))
    if report["cases_with_issues"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
