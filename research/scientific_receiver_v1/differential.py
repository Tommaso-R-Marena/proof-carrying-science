"""Seeded finite differential campaign against the actual compiled Lean CLI.

--checker is a test-harness input, never a receiving authority selector. Corpus
construction emits only data bytes; it does not generate Lean/Python source.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
import random
import struct
import subprocess
import time
from typing import Any

from . import producer, reference

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SEED = 20261018


@dataclass(frozen=True)
class Case:
    name: str
    family: str
    raw: bytes
    expected: bool


def _set(raw: bytes, index: int, value: bytes) -> bytes:
    fields = raw.split(b"|")
    fields[index] = value
    return b"|".join(fields)


def corpus(seed: int = SEED, count: int = 256) -> list[Case]:
    """Generate fixed-family mutations and independently labeled positive controls."""
    rng = random.Random(seed)
    cases: list[Case] = []
    for entry in json.loads((HERE / "fixtures/index.json").read_text())["cases"]:
        cases.append(Case("fixture/" + entry["id"], "frozen-fixture", (HERE / "fixtures" / entry["wire"]).read_bytes(), entry["accepted"]))
    for index in range(count):
        steps = rng.randrange(65)
        physical = index % 2 == 0
        if physical:
            firings = tuple(F(rng.randrange(31), 6) for _ in range(steps))
            initialA = sum(firings, F(0)) + F(rng.randrange(31), 6)
            initialB = F(rng.randrange(31), 6)
        else:
            firings = tuple(F(rng.randrange(-30, 31), rng.choice((1,2,3,4,5,6))) for _ in range(steps))
            initialA = F(rng.randrange(-30, 31), rng.choice((1,2,3,4,5,6)))
            initialB = F(rng.randrange(-30, 31), rng.choice((1,2,3,4,5,6)))
        actual = initialA - sum(firings, F(0))
        box = (actual - F(rng.randrange(1, 7), 6), actual + F(rng.randrange(1, 7), 6))
        claim = (box[0] - F(1,2), box[1] + F(1,3))
        witness = producer.build(initialA, initialB, firings, box=box, claim=claim,
                                 physical=physical, unitCode=bool(index % 3))
        raw = producer.encode(witness)
        prefix = f"random/{index:03d}/"
        cases.append(Case(prefix+"positive", "random-positive", raw, True))
        changed = producer.build(initialA+1, initialB, (*firings, F(1)) if steps < 64 else firings,
                                 physical=physical, unitCode=witness.unitCode)
        cases.append(Case(prefix+"consistent-change", "consistent-change-positive", producer.encode(changed), True))
        widened = replace(witness, lower=witness.lower-1, upper=witness.upper+1)
        cases.append(Case(prefix+"widened-claim", "widened-positive", producer.encode(widened), True))
        mutations = {
            "unknown-tag": b"OTHER" + raw[len(b"PCS-SCI-BOUND-V1"):],
            "unknown-version": raw.replace(b"BOUND-V1", b"BOUND-V2", 1),
            "unknown-policy": _set(raw,1,b"2"),
            "unknown-family": _set(raw,2,b"2"),
            "wrong-species": _set(raw,3,b"1"),
            "wrong-stoichiometry": _set(raw,5,b"1"),
            "wrong-weight": _set(raw,7,b"2"),
            "unrelated-expression": _set(raw,9,b"1"),
            "unknown-unit": _set(raw,11,b"2"),
            "unknown-physical-code": _set(raw,12,b"2"),
            "missing-assumption": _set(raw,13,b"0"),
            "missing-limitation": _set(raw,14,b"0"),
            "integer-plus": _set(raw,1,b"+1"),
            "integer-leading-zero": _set(raw,1,b"01"),
            "integer-negative-zero": _set(raw,3,b"-0"),
            "integer-whitespace": _set(raw,1,b" 1"),
            "integer-exponent": _set(raw,1,b"1e0"),
            "integer-overflow": _set(raw,15,b"1000000000000000001"),
            "field-too-long": _set(raw,15,b"1"*21),
            "denominator-zero": _set(raw,16,b"0"),
            "denominator-negative": _set(raw,16,b"-1"),
            "rational-nonreduced": _set(_set(raw,15,str(2*initialA.numerator).encode()),16,str(2*initialA.denominator).encode()),
            "step-overflow": _set(raw,10,b"65"),
            "step-negative": _set(raw,10,b"-1"),
            "count-overflow": _set(raw,31,b"65"),
            "count-negative": _set(raw,31,b"-1"),
            "truncated": b"|".join(raw.split(b"|")[:-1]),
            "trailing-field": raw+b"|0",
            "newline": raw+b"\n",
            "unicode": raw+b"\xc2\xa0",
            "bom": b"\xef\xbb\xbf"+raw,
            "oversize": raw+b"0"*(8193-len(raw)),
            "incorrect-reference": producer.encode(replace(witness,referenceStep=(steps+1)%65)),
            "incorrect-environment": producer.encode(replace(witness,envValue=actual+1)),
            "incorrect-total": producer.encode(replace(witness,declaredTotal=witness.declaredTotal+1)),
            "initial-evidence-mismatch": producer.encode(replace(witness,initialA=initialA+1)),
            "reversed-box": producer.encode(replace(witness,boxLo=actual+1,boxHi=actual-1)),
            "reversed-claim": producer.encode(replace(witness,lower=actual+1,upper=actual-1)),
            "box-outside-claim": producer.encode(replace(witness,lower=witness.boxLo+F(1,100))),
        }
        for family, data in mutations.items():
            cases.append(Case(prefix+family, family, data, False))
    physical_controls = [
        ("negative-initial-a", F(-1),F(2),()),
        ("negative-initial-b", F(2),F(-1),()),
        ("negative-firing", F(2),F(0),(F(-1),)),
        ("temporary-negative", F(2),F(0),(F(3),F(-2))),
    ]
    for name, a,b,fs in physical_controls:
        for physical in (False, True):
            cases.append(Case(f"physical/{name}/{int(physical)}", "physical-state-control",
                              producer.encode(producer.build(a,b,fs,physical=physical)), not physical))
    return cases


def corpus_sha256(cases: list[Case]) -> str:
    digest = hashlib.sha256()
    for case in cases:
        name = case.name.encode("ascii")
        digest.update(struct.pack(">I",len(name))); digest.update(name)
        digest.update(struct.pack(">I",len(case.raw))); digest.update(case.raw)
    return digest.hexdigest()


# Actual subprocess framing is finalized with the Lean CLI owner before use.

def _unique_json(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate checker response key")
        result[key] = value
    return result


def executable_identity(checker: Path, checker_args: tuple[str, ...] = (), checker_cwd: Path | None = None) -> dict[str, Any]:
    resolved = checker.resolve(strict=True)
    raw = resolved.read_bytes()
    if raw[:4] != b"\x7fELF":
        raise ValueError("--checker must name the actual Lean/lake or compiled receiver ELF executable, not a script wrapper")
    directory = (checker_cwd or Path.cwd()).resolve(strict=True)
    argument_files = []
    for arg in checker_args:
        path = directory / arg
        if path.is_file():
            argument_files.append({"path":str(path.resolve()),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    return {"path": str(resolved), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "command": [str(resolved), *checker_args], "cwd":str(directory),
            "argument_files":argument_files,
            "execution_mode": "Lean --run compiled IR; not standalone native" if "--run" in checker_args else "standalone executable",
            "lean_path":os.environ.get("LEAN_PATH"),
            "python_version":sys.version,"platform":platform.platform()}


def query_lean(checker: Path, raws: list[bytes], *, timeout: float = 120,
               checker_args: tuple[str, ...] = (), checker_cwd: Path | None = None) -> list[dict[str, Any]]:
    """One actual process per bounded batch; one isolated process per oversize frame."""
    if any(len(raw) > 8192 for raw in raws) and len(raws) != 1:
        raise ValueError("oversize framing must run in an isolated process")
    frames = b"".join(struct.pack(">I", len(raw)) + raw for raw in raws)
    result = subprocess.run([str(checker.resolve(strict=True)), *checker_args], input=frames, cwd=checker_cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"actual Lean CLI exited {result.returncode}: {result.stderr.decode(errors='replace')[:1000]}")
    lines = result.stdout.splitlines()
    if len(lines) != len(raws):
        raise RuntimeError(f"actual Lean CLI returned {len(lines)} responses for {len(raws)} requests")
    responses = [json.loads(line, object_pairs_hook=_unique_json) for line in lines]
    if any(type(response) is not dict for response in responses):
        raise RuntimeError("actual Lean CLI emitted a non-object response")
    return responses


def expected_result(result: dict[str, Any]) -> dict[str, Any]:
    fields = ("finalA", "finalB", "total", "lowerA", "upperA", "lowerB", "upperB")
    return {**{name: f"{result[name][0]}/{result[name][1]}" for name in fields},
            "stepCount": result["referenceStep"], "unitCode": result["unitCode"],
            "physical": result["physical"]}


def response_issues(raw: bytes, response: dict[str, Any], decision: reference.Decision) -> list[str]:
    issues = []
    if type(response.get("accepted")) is not bool:
        issues.append("accepted_not_bool")
    if response.get("protocol") != "PCS-SCI-BOUND-V1" or type(response.get("policy")) is not int or response.get("policy") != 1:
        issues.append("response_protocol_policy")
    if response.get("scientific_acceptance") is not False or response.get("production_authority") is not False:
        issues.append("response_scope_flags")
    if len(raw) <= 8192 and response.get("raw_hex") != raw.hex():
        issues.append("raw_byte_echo")
    if response.get("accepted") != decision.accepted:
        issues.append("acceptance_disagreement")
    if response.get("accepted") is True and decision.accepted:
        if response.get("result") != expected_result(decision.result):
            issues.append("accepted_result_disagreement")
    elif response.get("accepted") is False and response.get("result", "missing") is not None:
        issues.append("reject_result_not_null")
    return issues


def run(checker: Path, out: Path, *, seed: int = SEED, count: int = 256,
        checker_args: tuple[str, ...] = (), checker_cwd: Path | None = None) -> dict[str, Any]:
    identity = executable_identity(checker, checker_args, checker_cwd)
    cases = corpus(seed, count)
    out.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    decisions = [reference.assess(case.raw) for case in cases]
    responses: list[dict[str, Any] | None] = [None] * len(cases)
    bounded = [index for index, case in enumerate(cases) if len(case.raw) <= 8192]
    for offset in range(0, len(bounded), 512):
        batch = bounded[offset:offset + 512]
        batch_responses = query_lean(checker, [cases[index].raw for index in batch], checker_args=checker_args, checker_cwd=checker_cwd)
        for index, response in zip(batch, batch_responses, strict=True):
            responses[index] = response
    for index, case in enumerate(cases):
        if len(case.raw) > 8192:
            responses[index] = query_lean(checker, [case.raw], checker_args=checker_args, checker_cwd=checker_cwd)[0]
    summaries: dict[str, Counter] = defaultdict(Counter)
    mismatches = []
    records = []
    for case, decision, response in zip(cases, decisions, responses, strict=True):
        assert response is not None
        issues = response_issues(case.raw, response, decision)
        if decision.accepted != case.expected:
            issues.append("reference_expectation_disagreement")
        tally = summaries[case.family]
        tally["cases"] += 1
        tally["expected_accepts"] += int(case.expected)
        tally["reference_accepts"] += int(decision.accepted)
        tally["lean_accepts"] += int(response.get("accepted") is True)
        tally["cases_with_issues"] += int(bool(issues))
        record = {"id": case.name, "family": case.family, "bytes": len(case.raw),
                  "raw_sha256": hashlib.sha256(case.raw).hexdigest(), "expected": case.expected,
                  "reference_accepted": decision.accepted, "reference_reason": decision.reason,
                  "lean": response, "issues": issues}
        records.append(record)
        if issues:
            mismatches.append({**record, "raw_hex": case.raw.hex()})
    duration = time.perf_counter() - clock
    report = {
        "format": "pcs-scientific-receiver-differential-v1", "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(), "wall_seconds": duration,
        "seed": seed, "random_positive_contracts": count, "case_count": len(cases),
        "checker": identity, "framing": "uint32-big-endian length then exact bytes; one JSON line per frame; oversize isolated",
        "corpus_sha256": corpus_sha256(cases),
        "preregistration_sha256": hashlib.sha256((HERE / "preregistration.json").read_bytes()).hexdigest(),
        "reference_accepts": sum(d.accepted for d in decisions),
        "lean_accepts": sum(r.get("accepted") is True for r in responses if r is not None),
        "cases_with_issues": len(mismatches),
        "issue_counts": dict(Counter(issue for item in mismatches for issue in item["issues"])),
        "families": {name: dict(counts) for name, counts in sorted(summaries.items())},
        "mismatches": mismatches,
        "scope": "Observed finite differential agreement only. No general Python-to-Lean refinement, compiler/IO/OS correspondence, empirical science, protected host root or production authority.",
        "scientific_acceptance": False, "production_authority": False,
    }
    report_raw = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    (out / "differential.json").write_text(report_raw)
    (out / "decisions.jsonl").write_text("".join(json.dumps(item, sort_keys=True, separators=(",",":")) + "\n" for item in records))
    (out / "corpus-manifest.json").write_text(json.dumps([
        {"id": case.name,"family":case.family,"raw_hex":case.raw.hex(),"expected":case.expected}
        for case in cases], separators=(",",":"), sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checker", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--checker-arg", action="append", default=[], help="Actual executable argument; use --checker-arg=--run for switches")
    parser.add_argument("--checker-cwd", type=Path)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--count", type=int, default=256)
    args = parser.parse_args()
    report = run(args.checker, args.out, seed=args.seed, count=args.count, checker_args=tuple(args.checker_arg), checker_cwd=args.checker_cwd)
    print(json.dumps({"case_count": report["case_count"], "cases_with_issues": report["cases_with_issues"],
                      "corpus_sha256": report["corpus_sha256"], "out": str(args.out.resolve())}))
    if report["cases_with_issues"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
