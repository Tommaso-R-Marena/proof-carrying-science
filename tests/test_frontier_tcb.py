"""Regression and differential tests for the TCB-reduction (frontier) work.

* Regression tests for counterexamples 5-12 found against the former Python
  `unit_compatible` / `csv_disjoint` implementations (see
  formal/PCS_FRONTIER_FORMALIZATION_REPORT.md).
* Agreement between the strict CSV parser and `csv.DictReader` *inside* the strict subset.
* Python <-> Lean differential fuzzing of the verified Lean deciders
  (`PCS.V2.Units.unitCompatibleB`, `PCS.V2.Csv.csvDisjointB`, `PCS.V2.Csv.parseCsv`) via
  formal/tools/LeanBuiltinCheck.lean. Skipped when the formal library is not built.

These are tests, not proofs: the Lean-side correctness theorems are
`unitCompatibleB_iff`, `parseCsv_iff`, `csvDisjointB_iff`.
"""
from __future__ import annotations

import csv
import io
import random
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from pcs.checks.splits import StrictCSVError, csv_key_disjoint, parse_strict_csv
from pcs.checks.units import parse_unit, units_compatible

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formal"


# ---------------------------------------------------------------------------
# Python oracles (exceptions are replay FAILs in production)
# ---------------------------------------------------------------------------

def py_unit(a: str, b: str) -> str:
    try:
        ok, _ = units_compatible(a, b)
    except Exception:
        return "FAIL"
    return "PASS" if ok else "FAIL"


def py_csv(left: bytes, right: bytes, key: bytes, tmp: Path) -> str:
    try:
        key_s = key.decode("utf-8")
    except UnicodeDecodeError:
        return "FAIL"
    lp, rp = tmp / "l.csv", tmp / "r.csv"
    lp.write_bytes(left)
    rp.write_bytes(right)
    try:
        ok, _ = csv_key_disjoint(lp, rp, key_s)
    except Exception:
        return "FAIL"
    return "PASS" if ok else "FAIL"


def py_parse(raw: bytes) -> str:
    try:
        _, rows = parse_strict_csv(raw)
    except StrictCSVError:
        return "REJECT"
    return f"OK {len(rows)}"


# ---------------------------------------------------------------------------
# Regression tests: units (counterexamples 5-8)
# ---------------------------------------------------------------------------

def test_cx5_trailing_newline_unit_rejected():
    # Old `_TERM.match(...)` with `$` accepted "m\n" as "m".
    old = re.compile(r"([A-Za-z0-9]+)(?:\^(-?\d+))?$")
    assert old.match("m\n") is not None
    assert py_unit("m\n", "m") == "FAIL"


def test_cx6_unicode_digit_exponent_rejected():
    old = re.compile(r"([A-Za-z0-9]+)(?:\^(-?\d+))?$")
    assert old.match("m^\u0662") is not None  # `\d` matches ARABIC-INDIC DIGIT TWO
    assert py_unit("m^\u0662", "m^2") == "FAIL"


def test_cx7_overflow_does_not_turn_equal_dimensions_into_fail():
    with pytest.raises(OverflowError):
        _ = 1e3 ** 200
    assert py_unit("M^200", "M^200") == "PASS"
    dims, scale = parse_unit("M^200")
    assert dims == {"N": 200, "L": -600} and scale is None


def test_cx8_underflow_does_not_turn_equal_dimensions_into_fail():
    with pytest.raises(ZeroDivisionError):
        _ = 1.0 / (1e-9 ** 40)
    assert py_unit("1/ug^40", "1/ug^40") == "PASS"


def test_units_basic_semantics():
    assert py_unit("mg/L", "ug/mL") == "PASS"
    assert py_unit("L/h", "mL/min") == "PASS"
    assert py_unit("mg", "L") == "FAIL"
    assert py_unit("", "") == "PASS"
    assert py_unit("furlong", "furlong") == "FAIL"


# ---------------------------------------------------------------------------
# Regression tests: strict CSV (counterexamples 9-12)
# ---------------------------------------------------------------------------

def dictreader_keys(raw: bytes, key: str):
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    return [r.get(key) for r in rows]


def test_cx9_duplicate_header_rejected():
    raw = b"id,id\n1,2\n"
    assert dictreader_keys(raw, "id") == ["2"]  # DictReader: last column wins silently
    assert py_parse(raw) == "REJECT"


def test_cx10_short_row_rejected():
    raw = b"x,id\n1\n"
    assert dictreader_keys(raw, "id") == [None]  # DictReader fills None
    assert py_parse(raw) == "REJECT"


def test_cx11_quoting_rejected():
    raw = b'id\n"1"\n'
    assert dictreader_keys(raw, "id") == ["1"]  # quote removal makes "1" and 1 collide
    assert py_parse(raw) == "REJECT"
    raw2 = b'id\n"a\nb"\n'
    assert dictreader_keys(raw2, "id") == ["a\nb"]  # embedded newline in a key
    assert py_parse(raw2) == "REJECT"


def test_cx12_lone_cr_rejected():
    raw = b"id\r1\r2\r"
    assert dictreader_keys(raw, "id") == ["1", "2"]  # DictReader treats CR as newline
    assert py_parse(raw) == "REJECT"


def test_strict_csv_agrees_with_dictreader_inside_subset():
    rng = random.Random(1234)
    for _ in range(300):
        width = rng.randint(1, 4)
        header = [f"c{i}" for i in range(width)]
        nrows = rng.randint(0, 5)
        rows = [[rng.choice(["", "a", "b", " 1", "x y", "\u00e9", "1"]) for _ in header]
                for _ in range(nrows)]
        nl = rng.choice(["\n", "\r\n"])
        text = nl.join([",".join(header)] + [",".join(r) for r in rows]) + rng.choice(["", nl])
        raw = text.encode("utf-8")
        h, rs = parse_strict_csv(raw)
        assert [x.decode() for x in h] == header
        # DictReader skips rows that are entirely empty; so does the strict parser
        # (an all-empty row of width 1 is the empty line).
        dr = list(csv.DictReader(io.StringIO(text, newline="")))
        assert [[r[c] for c in header] for r in dr] == [[f.decode() for f in r] for r in rs]


def test_examples_are_inside_strict_subset():
    paths = list((ROOT / "examples").rglob("*.csv")) + list((ROOT / "validation").rglob("*.csv"))
    for p in paths:
        parse_strict_csv(p.read_bytes())


# ---------------------------------------------------------------------------
# Python <-> Lean differential fuzzing
# ---------------------------------------------------------------------------

LEAN_READY = (
    shutil.which("lake") is not None
    and (FORMAL / ".lake" / "build" / "lib" / "lean" / "PCS.olean").exists()
)

UNIT_ATOMS = ["kg", "g", "mg", "ug", "m", "cm", "L", "mL", "uL", "s", "min", "h", "mol",
              "mmol", "umol", "M", "mM", "1", "furlong", "Kg", "", "m\n", "\u00b5g", "x1"]
UNIT_SEPS = ["*", "/", " ", "", "^", "^2", "^-1", "^0", "^\u0662", "^--1", "^+1", "^10"]


def rand_unit(rng: random.Random) -> str:
    s = ""
    for _ in range(rng.randint(0, 4)):
        s += rng.choice(UNIT_ATOMS)
        if rng.random() < 0.4:
            s += rng.choice(["^2", "^-1", "^3", "^0", "^-2", "^200"])
        s += rng.choice(UNIT_SEPS) if rng.random() < 0.7 else ""
    return s


CSV_ALPHABET = [b"id", b"x", b"1", b"2", b"a", b",", b"\n", b"\r\n", b"\r", b'"', b" ",
                b"\xc3\xa9", b"\xff", b"\x00", b"", b"ID"]


def rand_csv(rng: random.Random) -> bytes:
    if rng.random() < 0.6:
        cols = rng.sample([b"id", b"x", b"y"], rng.randint(1, 3))
        lines = [b",".join(cols)]
        for _ in range(rng.randint(0, 4)):
            lines.append(b",".join(rng.choice([b"1", b"2", b"3", b"a", b""]) for _ in cols))
        raw = rng.choice([b"\n", b"\r\n"]).join(lines) + rng.choice([b"", b"\n"])
        if rng.random() < 0.3:
            i = rng.randint(0, len(raw))
            raw = raw[:i] + rng.choice(CSV_ALPHABET) + raw[i:]
        return raw
    return b"".join(rng.choice(CSV_ALPHABET) for _ in range(rng.randint(0, 12)))


def x(b: bytes) -> str:
    return "x" + b.hex()


@pytest.mark.skipif(not LEAN_READY, reason="formal library not built")
def test_python_lean_differential_units_and_csv(tmp_path: Path):
    rng = random.Random(20261001)
    queries, expected = [], []
    fixed_units = [("m\n", "m"), ("m^\u0662", "m^2"), ("M^200", "M^200"),
                   ("1/ug^40", "1/ug^40"), ("mg/L", "ug/mL"), ("", ""), ("mg", "L")]
    units = fixed_units + [(rand_unit(rng), rand_unit(rng)) for _ in range(500)]
    for a, b in units:
        queries.append(f"U {x(a.encode())} {x(b.encode())}")
        expected.append(py_unit(a, b))
    fixed_csv = [(b"id,id\n1,2\n", b"id\n3\n", b"id"), (b"x,id\n1\n", b"id\n3\n", b"id"),
                 (b'id\n"1"\n', b"id\n1\n", b"id"), (b"id\r1\r", b"id\n2\n", b"id"),
                 (b"id\n1\n", b"id\n2\n", b"id"), (b"id\n1\n", b"id\n1\n", b"id")]
    csvs = fixed_csv + [(rand_csv(rng), rand_csv(rng), rng.choice([b"id", b"x", b"ID", b""]))
                        for _ in range(500)]
    for l, r, k in csvs:
        queries.append(f"C {x(l)} {x(r)} {x(k)}")
        expected.append(py_csv(l, r, k, tmp_path))
    for l, _, _ in csvs:
        queries.append(f"P {x(l)}")
        expected.append(py_parse(l))
    out = subprocess.run(
        ["lake", "env", "lean", "--run", "tools/LeanBuiltinCheck.lean"],
        cwd=FORMAL, input="\n".join(queries) + "\n", capture_output=True, text=True,
        timeout=900,
    )
    assert out.returncode == 0, out.stderr
    got = out.stdout.splitlines()
    assert len(got) == len(expected)
    mism = [(q, e, g) for q, e, g in zip(queries, expected, got) if e != g]
    assert not mism, mism[:10]
    # the fuzz corpus exercises both outcomes
    assert "PASS" in got and "FAIL" in got and "REJECT" in got


# ---------------------------------------------------------------------------
# Workflow: Lean `workflowCheckB` vs production `verify_static_workflow_replay_v06`
# ---------------------------------------------------------------------------

from copy import deepcopy  # noqa: E402
import hashlib  # noqa: E402

from pcs.canonical_json import canonicalize_jcs  # noqa: E402
from pcs.workflow_replay_v06 import verify_static_workflow_replay_v06  # noqa: E402

WF_SCRIPT = (
    b"import pandas as pd\n"
    b"df = pd.read_csv('input.csv')\n"
    b"df.to_csv('output.csv', index=False)\n"
)
WF_IN = b"id,x\n1,1\n"
WF_OUT = b"id,x\n1,2\n"


def _wf_base():
    def art(ident, source_path, raw):
        return {"id": ident, "path": f"artifacts/{ident}/payload", "role": "data",
                "sha256": hashlib.sha256(raw).hexdigest(), "media_type": "text/plain",
                "source_path": source_path}
    prop = {
        "inference_format": "pcs-static-workflow-map-v1",
        "inference_id": "W_STATIC_wf_source",
        "static_only": True,
        "user_code_executed": False,
        "human_confirmed": True,
        "source_path": "pipeline.py",
        "source_kind": "python",
        "analysis_mode": "python_ast",
        "dependency_claim_mode": "exact_resolved_set",
        "confidence": 0.98,
        "imports": ["pandas"],
        "resolved_references": [],
        "references_truncated": True,
    }
    node = {"id": "N_STATIC_wf_source", "operation": "static_python_workflow",
            "inputs": ["wf_input", "wf_source"], "outputs": ["wf_output"]}
    cert = {"artifacts": [art("wf_source", "pipeline.py", WF_SCRIPT),
                          art("wf_input", "input.csv", WF_IN),
                          art("wf_output", "output.csv", WF_OUT)],
            "workflow": {"nodes": [node]}}
    files = {"artifacts/wf_source/payload": WF_SCRIPT, "artifacts/wf_input/payload": WF_IN,
             "artifacts/wf_output/payload": WF_OUT}
    return cert, prop, node, files


def _wf_case(mut_prop=None, mut_node=None, raw_prop=None, contract=None):
    cert, prop, node, files = _wf_base()
    if mut_prop:
        mut_prop(prop)
    if mut_node:
        mut_node(node)
    text = canonicalize_jcs(prop) if raw_prop is None else raw_prop(canonicalize_jcs(prop))
    node["contract"] = contract if contract is not None else {
        "type": "external", "namespace": "pcs-manifest-workflow-contract-v1", "proposition": text}
    return cert, files


READ_REF = {"kind": "read", "path": "input.csv", "artifact_id": "wf_input",
            "api": "pandas.read_csv", "location": "line 2"}

# (name, case, Lean-covered?)  Lean deliberately leaves JCS canonicality of the
# proposition and the `confidence`/`analysis_mode` comparison to the production Boolean,
# which the authority still requires conjunctively.
WF_CASES = [
    ("correct", _wf_case(), True),
    ("false_output", _wf_case(mut_node=lambda n: n.update(outputs=["wf_input"])), True),
    ("not_human_confirmed", _wf_case(mut_prop=lambda p: p.update(human_confirmed=False)), True),
    ("static_only_missing", _wf_case(mut_prop=lambda p: p.pop("static_only")), True),
    ("static_only_int", _wf_case(mut_prop=lambda p: p.update(static_only=1)), True),
    ("user_code_executed", _wf_case(mut_prop=lambda p: p.update(user_code_executed=True)), True),
    ("wrong_inference_id", _wf_case(mut_prop=lambda p: p.update(inference_id="W_STATIC_x")), True),
    ("wrong_source_kind", _wf_case(mut_prop=lambda p: p.update(source_kind="r")), True),
    ("wrong_source_path", _wf_case(mut_prop=lambda p: p.update(source_path="./pipeline.py")), True),
    ("wrong_operation", _wf_case(mut_node=lambda n: n.update(operation="static_r_workflow")), True),
    ("subset_ok", _wf_case(mut_prop=lambda p: p.update(dependency_claim_mode="claimed_subset"),
                           mut_node=lambda n: n.update(outputs=[])), True),
    ("subset_extra", _wf_case(mut_prop=lambda p: p.update(dependency_claim_mode="claimed_subset"),
                              mut_node=lambda n: n.update(outputs=["wf_output", "wf_input"])), True),
    ("exact_missing_output", _wf_case(mut_node=lambda n: n.update(outputs=[])), True),
    ("bad_mode", _wf_case(mut_prop=lambda p: p.update(dependency_claim_mode="all")), True),
    ("source_not_input", _wf_case(mut_prop=lambda p: p.update(dependency_claim_mode="claimed_subset"),
                                  mut_node=lambda n: n.update(inputs=["wf_input"])), True),
    ("ref_ok", _wf_case(mut_prop=lambda p: p.update(resolved_references=[READ_REF])), True),
    ("ref_null_artifact", _wf_case(mut_prop=lambda p: p.update(
        resolved_references=[dict(READ_REF, artifact_id=None)])), True),
    ("ref_wrong_path", _wf_case(mut_prop=lambda p: p.update(
        resolved_references=[dict(READ_REF, path="./input.csv")])), True),
    ("ref_wrong_kind", _wf_case(mut_prop=lambda p: p.update(
        resolved_references=[dict(READ_REF, kind="write")])), True),
    ("refs_missing", _wf_case(mut_prop=lambda p: p.pop("resolved_references")), True),
    ("duplicate_key", _wf_case(raw_prop=lambda t: t.replace(
        '{"analysis_mode"', '{"human_confirmed":false,"analysis_mode"', 1)
        .replace(',"human_confirmed":true', ',"human_confirmed":true', 1)), True),
    ("other_namespace", _wf_case(contract={"type": "external", "namespace": "other",
                                           "proposition": "{}"}), True),
    ("non_string_proposition", _wf_case(contract={
        "type": "external", "namespace": "pcs-manifest-workflow-contract-v1",
        "proposition": 1}), True),
    ("not_json_proposition", _wf_case(raw_prop=lambda t: t[:-1]), True),
    ("noncanonical_proposition", _wf_case(raw_prop=lambda t: t.replace(",", ", ", 1)), False),
    ("string_confidence", _wf_case(mut_prop=lambda p: p.update(confidence="0.98")), False),
    ("wrong_analysis_mode", _wf_case(mut_prop=lambda p: p.update(analysis_mode="r_literal_heuristic")), False),
]


def test_cx13_null_reference_does_not_match_artifact_named_None():
    cert, files = _wf_case(mut_prop=lambda p: p.update(
        resolved_references=[dict(READ_REF, artifact_id=None)]))
    assert verify_static_workflow_replay_v06(cert, files)["valid"] is False


def test_cx14_string_confidence_rejected():
    cert, files = _wf_case(mut_prop=lambda p: p.update(confidence="0.98"))
    assert verify_static_workflow_replay_v06(cert, files)["valid"] is False


@pytest.mark.skipif(not LEAN_READY, reason="formal library not built")
def test_python_lean_differential_workflow():
    queries, expected, covered, names = [], [], [], []
    for name, (cert, files), cov in WF_CASES:
        res = verify_static_workflow_replay_v06(cert, files)
        fresh = res.get("_authority_fresh_sources")
        if fresh is None:  # replay failed before analysis (malformed contract)
            cert2 = deepcopy(cert)
            for n in cert2["workflow"]["nodes"]:
                n.pop("contract", None)
            fresh = verify_static_workflow_replay_v06(cert2, files).get("_authority_fresh_sources", [])
            if not fresh:
                _, _, _, f0 = _wf_base()
                c0, _ = _wf_case()
                fresh = verify_static_workflow_replay_v06(c0, f0)["_authority_fresh_sources"]
        queries.append(f"W {x(canonicalize_jcs(cert).encode())} {x(canonicalize_jcs(fresh).encode())}")
        expected.append("PASS" if res["valid"] else "FAIL")
        covered.append(cov)
        names.append(name)
    out = subprocess.run(
        ["lake", "env", "lean", "--run", "tools/LeanBuiltinCheck.lean"],
        cwd=FORMAL, input="\n".join(queries) + "\n", capture_output=True, text=True,
        timeout=900,
    )
    assert out.returncode == 0, out.stderr
    got = out.stdout.splitlines()
    assert len(got) == len(expected)
    for name, e, g, cov in zip(names, expected, got, covered):
        if cov:
            assert e == g, (name, e, g)
        else:
            # outside Lean's check, production must reject; the authority requires both
            assert e == "FAIL", name
        # Lean never accepts what production rejects among Lean-covered cases, and
        # the conjunction (production AND Lean) never accepts a rejected case.
    assert expected[0] == "PASS" and got[0] == "PASS"


# ---------------------------------------------------------------------------
# Environment: Lean `envFactsB` on production `capture_environment_v06` output
# ---------------------------------------------------------------------------

import tempfile  # noqa: E402

from pcs.environment_v06 import capture_environment_v06  # noqa: E402

HEX64 = "0123456789abcdef" * 4


def _capture(files: dict[str, bytes]):
    with tempfile.TemporaryDirectory() as d:
        inv = []
        for i, (p, b) in enumerate(sorted(files.items())):
            target = Path(d) / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b)
            inv.append({"artifact_id": f"env{i}", "path": p, "size": len(b),
                        "sha256": hashlib.sha256(b).hexdigest(),
                        "media_type": "text/plain", "role": "environment"})
        return inv, capture_environment_v06(d, inv)


def _lean_inventory(inv, files):
    return [{"artifact_id": it["artifact_id"], "path": it["path"],
             "bytes_hex": files[it["path"]].hex(), "sha256": it["sha256"]} for it in inv]


def _deps(cap):
    return {d["name"]: d for d in cap["python"]["dependencies"]}


GOOD_REQ = (f"numpy==1.26.0\npandas == 2.1.0 \\\n    --hash=sha256:{HEX64}\n"
            "scipy>=1.0\n# comment==1.0\n").encode()


def test_cx15_wildcard_and_range_pins_are_not_exact():
    _, cap = _capture({"requirements.txt": b"numpy==1.*\npandas==1.0,<2\nx===1.0\ny==1.0\n"})
    deps = _deps(cap)
    assert deps["numpy"]["exact_pin"] is False and deps["numpy"]["version"] is None
    assert deps["pandas"]["exact_pin"] is False
    assert deps["x"]["exact_pin"] is False
    assert deps["y"]["exact_pin"] is True and deps["y"]["version"] == "1.0"


def test_cx16_short_container_digest_is_not_digest_pinned():
    _, cap = _capture({"Dockerfile": b"FROM python@sha256:abc\n"})
    assert cap["containers"][0]["stages"][0]["digest_pinned"] is False
    _, cap = _capture({"Dockerfile": f"FROM python@sha256:{HEX64}\n".encode()})
    assert cap["containers"][0]["stages"][0]["digest_pinned"] is True


def test_cx17_empty_hash_option_is_not_a_hash_pin():
    _, cap = _capture({"requirements.txt": b"numpy==1.0 --hash=sha256:\n"})
    assert _deps(cap)["numpy"]["hash_pinned"] is False
    _, cap = _capture({"requirements.txt": f"numpy==1.0 --hash=sha256:{HEX64}\n".encode()})
    assert _deps(cap)["numpy"]["hash_pinned"] is True


def _env_cases():
    cases = []

    def add(name, files, expect, mutate=None, inv_files=None):
        inv, cap = _capture(files)
        if mutate:
            cap = mutate(deepcopy(cap))
        cases.append((name, _lean_inventory(inv, inv_files or files), cap, expect))

    docker = (f"FROM --platform=linux/amd64 python@sha256:{HEX64} AS build\n"
              "RUN pip install -r requirements.txt\n").encode()
    add("requirements_python_version_docker",
        {"requirements.txt": GOOD_REQ, ".python-version": b"3.11.4\n", "Dockerfile": docker},
        "PASS")
    add("crlf", {"requirements.txt": GOOD_REQ.replace(b"\n", b"\r\n")}, "PASS")
    add("runtime_txt", {"runtime.txt": b"python-3.10.2\n"}, "PASS")
    add("continuation_is_not_a_new_requirement", {"requirements.txt": b"foo \\\nnumpy==1.0\n"}, "PASS")
    add("wildcard_not_checked", {"requirements.txt": b"numpy==1.*\n"}, "PASS")
    add("no_environment_sources", {"README.md": b"hello\n"}, "PASS")
    # semantic substitutions in the declared capture are caught by Lean
    def bump(cap):
        for d in cap["python"]["dependencies"]:
            if d["name"] == "numpy":
                d["version"] = "1.27.0"
        return cap
    add("substituted_version", {"requirements.txt": GOOD_REQ}, "FAIL", mutate=bump)

    def fake_hash(cap):
        for d in cap["python"]["dependencies"]:
            if d["name"] == "numpy":
                d["hash_pinned"] = True
        return cap
    add("claimed_hash_pin_absent", {"requirements.txt": GOOD_REQ}, "FAIL", mutate=fake_hash)

    def fake_name(cap):
        for d in cap["python"]["dependencies"]:
            if d["name"] == "numpy":
                d["name"] = "numpyy"
        return cap
    add("substituted_name", {"requirements.txt": GOOD_REQ}, "FAIL", mutate=fake_name)

    def fake_digest(cap):
        st = cap["containers"][0]["stages"][0]
        st["reference"] = "python@sha256:" + "f" * 64
        return cap
    add("substituted_container_digest", {"Dockerfile": docker}, "FAIL", mutate=fake_digest)

    def fake_py(cap):
        cap["python"]["interpreter_constraints"][0]["value"] = "3.12.0"
        return cap
    add("substituted_python_version", {".python-version": b"3.11.4\n"}, "FAIL", mutate=fake_py)

    def fake_size(cap):
        cap["sources"][0]["size"] += 1
        return cap
    add("substituted_source_size", {"requirements.txt": GOOD_REQ}, "FAIL", mutate=fake_size)
    # inventory bytes differ from the bytes that were captured
    add("different_committed_bytes", {"requirements.txt": GOOD_REQ}, "FAIL",
        inv_files={"requirements.txt": GOOD_REQ.replace(b"1.26.0", b"1.25.0")})
    # fail-closed narrowing: non-ASCII whitespace / exotic line breaks in a file whose
    # facts must be verified
    add("nbsp_rejected", {"requirements.txt": "numpy==1.0\u00a0\n".encode()}, "FAIL")
    add("lone_cr_rejected", {"requirements.txt": b"numpy==1.0\rpandas==2.0\n"}, "FAIL")
    return cases


@pytest.mark.skipif(not LEAN_READY, reason="formal library not built")
def test_python_lean_differential_environment():
    cases = _env_cases()
    queries = [f"E {x(canonicalize_jcs(inv).encode())} {x(canonicalize_jcs(cap).encode())}"
               for _, inv, cap, _ in cases]
    out = subprocess.run(
        ["lake", "env", "lean", "--run", "tools/LeanBuiltinCheck.lean"],
        cwd=FORMAL, input="\n".join(queries) + "\n", capture_output=True, text=True,
        timeout=900,
    )
    assert out.returncode == 0, out.stderr
    got = out.stdout.splitlines()
    assert [(n, g) for (n, _, _, _), g in zip(cases, got)] == [(n, e) for n, _, _, e in cases]


# ---------------------------------------------------------------------------
# Canonical ZIP: Lean `decodeZip` vs Python `zipfile`, and raw-archive authority mode
# ---------------------------------------------------------------------------

import io  # noqa: E402
import json as _json  # noqa: E402
import struct  # noqa: E402
import zipfile as _zipfile  # noqa: E402

from pcs.canonical_zip_v06 import canonical_zip_bytes_v06, is_canonical_zip_v06  # noqa: E402

GOLDEN = ROOT / "tests" / "v06_golden"
GOLDEN_META = _json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))
GOLDEN_MEMBERS = {
    rel: (GOLDEN / rel).read_bytes()
    for rel in ["certificate.json", "certificate_signature.json", "package_manifest.json",
                "package_signature.json", "artifacts/fixture.bin", "normalized/index.json",
                GOLDEN_META["normalized_wire_path"]]
}


def _expected_decode(members: dict[str, bytes]) -> str:
    return "OK " + ";".join(
        n.encode().hex() + "=" + hashlib.sha256(members[n]).hexdigest() for n in sorted(members))


def _zip_mutations():
    base = canonical_zip_bytes_v06({"a.txt": b"hello", "b/\u00e9.txt": b"xyz"})
    cases = [("canonical", base, _expected_decode({"a.txt": b"hello", "b/\u00e9.txt": b"xyz"})),
             ("golden", canonical_zip_bytes_v06(GOLDEN_MEMBERS), _expected_decode(GOLDEN_MEMBERS)),
             ("trailing_byte", base + b"\x00", "REJECT"),
             ("leading_byte", b"\x00" + base, "REJECT")]
    # DEFLATE member
    buf = io.BytesIO()
    with _zipfile.ZipFile(buf, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"hello" * 10)
    cases.append(("deflate", buf.getvalue(), "REJECT"))
    # unsorted members (otherwise canonical fields)
    buf = io.BytesIO()
    with _zipfile.ZipFile(buf, "w") as zf:
        for name in ["b.txt", "a.txt"]:
            info = _zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system, info.create_version, info.extract_version = 3, 20, 20
            info.external_attr = 0o100644 << 16
            zf.writestr(info, b"x")
    cases.append(("unsorted", buf.getvalue(), "REJECT"))
    # duplicate member names
    import warnings
    buf = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with _zipfile.ZipFile(buf, "w") as zf:
            for data in [b"1", b"2"]:
                info = _zipfile.ZipInfo("a.txt", (1980, 1, 1, 0, 0, 0))
                info.create_system, info.create_version, info.extract_version = 3, 20, 20
                info.external_attr = 0o100644 << 16
                zf.writestr(info, data)
    cases.append(("duplicate", buf.getvalue(), "REJECT"))
    # local header name disagrees with central directory name
    loc = bytearray(base)
    loc[30:35] = b"c.txt"
    cases.append(("local_central_name_mismatch", bytes(loc), "REJECT"))
    # central directory points the second member at the first local header (overlap)
    cd = bytearray(base)
    eocd_off = len(cd) - 22
    cd_off = struct.unpack_from("<I", cd, eocd_off + 16)[0]
    first_len = 46 + struct.unpack_from("<H", cd, cd_off + 28)[0]
    struct.pack_into("<I", cd, cd_off + first_len + 42, 0)
    cases.append(("overlapping_members", bytes(cd), "REJECT"))
    # CRC field corrupted in both headers
    crc = bytearray(base)
    crc[14] ^= 1
    struct.pack_into("<B", crc, cd_off + 16, crc[cd_off + 16] ^ 1)
    cases.append(("bad_crc", bytes(crc), "REJECT"))
    # archive comment
    cases.append(("comment", base[:-2] + b"\x01\x00!", "REJECT"))
    return cases


@pytest.mark.skipif(not LEAN_READY, reason="formal library not built")
def test_python_lean_differential_zip():
    cases = _zip_mutations()
    out = subprocess.run(
        ["lake", "env", "lean", "--run", "tools/LeanBuiltinCheck.lean"],
        cwd=FORMAL, input="\n".join(f"Z {x(z)}" for _, z, _ in cases) + "\n",
        capture_output=True, text=True, timeout=900,
    )
    assert out.returncode == 0, out.stderr
    got = out.stdout.splitlines()
    assert [(n, g) for (n, _, _), g in zip(cases, got)] == [(n, e) for n, _, e in cases]
    # Python's zipfile accepts several of the archives Lean rejects (these remain on
    # the legacy, explicitly less-assured path).
    for name in ["trailing_byte", "deflate", "unsorted"]:
        z = dict((n, b) for n, b, _ in cases)[name]
        with _zipfile.ZipFile(io.BytesIO(z)) as zf:
            assert zf.namelist()


def _golden_pem(path: Path) -> None:
    import base64
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    key = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(GOLDEN_META["public_key_raw_base64"], validate=True))
    path.write_bytes(key.public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo))


AUTHORITY_READY = shutil.which("lake") is not None


@pytest.mark.skipif(not AUTHORITY_READY, reason="Lean/Lake unavailable")
def test_canonical_golden_zip_is_verified_by_lean_from_raw_bytes(tmp_path: Path):
    from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06
    bundle = tmp_path / "golden.pcs.zip"
    bundle.write_bytes(canonical_zip_bytes_v06(GOLDEN_MEMBERS))
    pem = tmp_path / "pk.pem"
    _golden_pem(pem)
    res = verify_package_zip_end_to_end_v06(bundle, pem)
    assert res["valid"] is True and res["authoritative"] is True
    assert res["archive_assurance"] == "lean-decoded-canonical-zip"
    assert res["lean_authority"]["archive_mode"] == "lean-decoded-canonical-zip"
    assert res["lean_authority"]["verdict"] == "ACCEPT"


@pytest.mark.skipif(not AUTHORITY_READY, reason="Lean/Lake unavailable")
def test_noncanonical_zip_is_legacy_or_rejected_when_canonical_required(tmp_path: Path):
    from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06
    bundle = tmp_path / "golden.deflate.zip"
    with _zipfile.ZipFile(bundle, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
        for n, b in GOLDEN_MEMBERS.items():
            zf.writestr(n, b)
    assert not is_canonical_zip_v06(bundle.read_bytes(), GOLDEN_MEMBERS)
    pem = tmp_path / "pk.pem"
    _golden_pem(pem)
    res = verify_package_zip_end_to_end_v06(bundle, pem)
    assert res["valid"] is True
    assert res["archive_assurance"] == "python-materialized-legacy-zip"
    strict = verify_package_zip_end_to_end_v06(bundle, pem, require_canonical_archive=True)
    assert strict["valid"] is False and strict["failed_stage"] == "canonical_archive"
