"""Fixed research test shards and a census that refuses unassigned test modules.

This coordinates CI only. It never supplies verifier verdicts or adopts artifacts
from another runner; each native/process shard builds its own checked images.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREFIX = "research/progress_supervisor_v1/"
SHARDS = {
    "worker": (PREFIX + "test_worker.py",),
    "replay": (PREFIX + "test_replay.py",),
    "authority": (PREFIX + "test_progress.py", "tests/test_action_shield_v1.py", "tests/test_control_monitor_v1.py"),
    "codec": (PREFIX + "test_codec.py",),
    "intake": (PREFIX + "test_intake.py", PREFIX + "test_ci.py"),
}


def census(directory=HERE, assignments=SHARDS):
    found = {PREFIX + path.name for path in directory.glob("test_*.py")}
    assigned = [path for group in assignments.values() for path in group]
    if not assignments or any(not group for group in assignments.values()):
        raise ValueError("every shard must contain tests")
    if len(assigned) != len(set(assigned)):
        raise ValueError("a test module was assigned more than once")
    research = {path for path in assigned if path.startswith(PREFIX)}
    if research != found:
        raise ValueError("CI test census mismatch: " + json.dumps({
            "unassigned": sorted(found - research), "missing": sorted(research - found),
        }))
    if not {"tests/test_action_shield_v1.py", "tests/test_control_monitor_v1.py"} <= set(assigned):
        raise ValueError("required predecessor baseline omitted")
    return dict(shards=list(assignments), research_test_modules=len(found), assigned_test_modules=len(assigned))


def run(shard, output):
    census()
    if shard not in SHARDS:
        raise ValueError("unknown test shard")
    target = Path(output).resolve()
    target.mkdir(parents=True, exist_ok=False)
    return subprocess.run([
        sys.executable, "-m", "pytest", "-q", *SHARDS[shard],
        "--junitxml=" + str(target / "tests.xml"),
    ], cwd=ROOT).returncode


def aggregate(reports, output):
    """Require each assigned module's complete, unique, zero-skip JUnit report.

    Workflow job success is checked separately by the final job. These XML files
    are CI observations, not native authorization or scientific acceptance.
    """
    census()
    reports, target = Path(reports), Path(output)
    expected = {"progress-supervisor-tests-" + name for name in SHARDS}
    if {p.name for p in reports.iterdir()} != expected:
        raise ValueError("missing or unexpected test-shard artifacts")
    combined, seen_ids, counts = ET.Element("testsuites"), set(), {}
    for shard, modules in SHARDS.items():
        path = reports / ("progress-supervisor-tests-" + shard) / "tests.xml"
        with path.open("rb") as stream:
            raw = stream.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("bounded non-DTD test report required")
        root = ET.fromstring(raw)
        suites = list(root.iter("testsuite"))
        if not suites:
            raise ValueError("test report contains no suite")
        expected_modules = {m[:-3].replace("/", ".") for m in modules}
        seen_modules, count = set(), 0
        for suite in suites:
            cases = suite.findall("testcase")
            if not cases or len(cases) > 20000 or suite.get("tests") != str(len(cases)):
                raise ValueError("test report count mismatch")
            if any(suite.get(key) != "0" for key in ("failures", "errors", "skipped")):
                raise ValueError("test shard contains failure/error/skip")
            for case in cases:
                module, name = case.get("classname"), case.get("name")
                if module not in expected_modules or not name:
                    raise ValueError("unexpected test module or identity")
                identity = module, name
                if identity in seen_ids or any(case.find(tag) is not None for tag in ("failure", "error", "skipped")):
                    raise ValueError("duplicate or unsuccessful test case")
                seen_ids.add(identity);seen_modules.add(module)
            count += len(cases)
            combined.append(suite)
        if seen_modules != expected_modules:
            raise ValueError("assigned test module missing from results")
        counts[shard] = count
    target.mkdir(parents=True, exist_ok=False)
    summary = dict(format="pcs-progress-supervisor-ci-summary-v1", tests=sum(counts.values()),
                   failures=0, errors=0, skipped=0, shards=counts, census=census(),
                   ci_observations_not_authority=True, pcs_authority=False)
    with (target / "tests.xml").open("xb") as stream:
        ET.ElementTree(combined).write(stream, encoding="utf-8", xml_declaration=True)
    with (target / "summary.json").open("x") as stream:
        json.dump(summary, stream, indent=2)
    return summary


def main():
    parser = argparse.ArgumentParser(__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("matrix")
    test = commands.add_parser("test")
    test.add_argument("shard", choices=SHARDS)
    test.add_argument("output")
    collect = commands.add_parser("aggregate")
    collect.add_argument("reports")
    collect.add_argument("output")
    args = parser.parse_args()
    if args.command == "matrix":
        census()
        print("matrix=" + json.dumps({"shard": list(SHARDS)}, separators=(",", ":")))
        return 0
    if args.command == "aggregate":
        print(json.dumps(aggregate(args.reports, args.output)))
        return 0
    return run(args.shard, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
