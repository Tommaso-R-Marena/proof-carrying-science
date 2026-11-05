"""Regression and Python <-> Lean differential tests for the verified PK/PD path.

The Lean authority decides `pkpd_contract` / `pkpd_reference_match` itself
(`PCS.V2.PKPDCheck`, proved sound in `pkpdContractRun_sound` / `pkpdMatchRun_sound`; the
real-valued meaning of a PASS is `PCSReal.PKPD.pcs_pkpd_reference_match_real`).  These
tests are evidence, not proofs:

* regressions for the strict numeric surface (counterexamples 18-21 in
  formal/PCS_FRONTIER_FORMALIZATION_REPORT.md): `Decimal()` / `float()` / `csv.DictReader`
  accepted spellings that the high-assurance path rejects;
* differential agreement of the Lean strict decimal reader with production;
* differential agreement of the Lean contract check and of the Lean certified-interval
  reference match with the production Decimal(50) replay, on inputs away from the
  tolerance boundary (exactly at the boundary the two may legitimately differ; any
  disagreement makes the Lean authority reject the package, i.e. fails closed).
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

from pcs.adapters.pkpd import check_contract_file, check_output_file, strict_decimal_text
from pcs.replay_v06 import _strict_tolerance

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formal"
EXAMPLE = ROOT / "examples" / "pkpd_one_compartment"
MODEL = (EXAMPLE / "pk_model.json").read_bytes()
PRED = (EXAMPLE / "predictions.csv").read_bytes()


def x(b: bytes) -> str:
    return "x" + b.hex()


def lean_available() -> bool:
    return shutil.which("lake") is not None and (FORMAL / ".lake" / "build" / "lib").exists()


def run_lean(queries: list[str]) -> list[str]:
    out = subprocess.run(
        ["lake", "env", "lean", "--run", "tools/LeanBuiltinCheck.lean"],
        cwd=FORMAL, input="\n".join(queries) + "\n", capture_output=True, text=True,
        timeout=900,
    )
    assert out.returncode == 0, out.stderr
    got = out.stdout.splitlines()
    assert len(got) == len(queries)
    return got


# ---------------------------------------------------------------------------
# Python oracles
# ---------------------------------------------------------------------------

def py_decimal(text: str) -> str:
    try:
        q = Fraction(strict_decimal_text(text))
    except Exception:
        return "REJECT"
    return f"{q.numerator}/{q.denominator}"


def py_contract(model: bytes, tmp: Path) -> str:
    p = tmp / "m.json"
    p.write_bytes(model)
    try:
        ok, _ = check_contract_file(p)
    except Exception:
        return "FAIL"
    return "PASS" if ok else "FAIL"


def py_match(model: bytes, csv: bytes, rel: str, abs_: str, tmp: Path) -> str:
    mp, cp = tmp / "m.json", tmp / "p.csv"
    mp.write_bytes(model)
    cp.write_bytes(csv)
    try:
        ok, _ = check_output_file(mp, cp, time_column="time", concentration_column="concentration",
                                  effect_column="effect", rel_tol=_strict_tolerance(rel),
                                  abs_tol=_strict_tolerance(abs_))
    except Exception:
        return "FAIL"
    return "PASS" if ok else "FAIL"


# ---------------------------------------------------------------------------
# Regressions: strict numeric surface (production narrowed fail-closed)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [" 1.0", "1.0 ", "+1", ".5", "5.", "1_0", "NaN", "Infinity",
                                  "-inf", "1e", "1e+", "\u0661", "１", "1e401", "1e00001", ""])
def test_strict_decimal_rejects_lenient_spellings(text):
    Decimal  # noqa: B018 - Decimal() itself would accept several of these
    with pytest.raises(ValueError):
        strict_decimal_text(text)


@pytest.mark.parametrize("value", [" 1e-9", "1_0", "inf", "nan", True, None, "-"])
def test_strict_tolerance_rejects(value):
    with pytest.raises(ValueError):
        _strict_tolerance(value)


def _with_row(field: str) -> bytes:
    return PRED.replace(b"\n0.5,", b"\n" + field.encode() + b",", 1)


@pytest.mark.parametrize("field", [" 0.5", "+0.5", ".5", "0_5", "NaN"])
def test_reference_match_rejects_lenient_time_cells(tmp_path, field):
    # counterexample 19: Decimal(row[...]) accepted these cells; the strict path FAILs
    assert py_match(MODEL, PRED, "1e-9", "1e-12", tmp_path) == "PASS"
    assert py_match(MODEL, _with_row(field), "1e-9", "1e-12", tmp_path) == "FAIL"


def test_reference_match_rejects_quoted_and_duplicate_headers(tmp_path):
    # counterexample 20: csv.DictReader unquoted fields and resolved duplicate headers
    quoted = PRED.replace(b"\n0.5,", b'\n"0.5",', 1)
    dup = PRED.replace(b"time,concentration,effect", b"time,concentration,effect,time", 1)
    dup = b"\n".join(l + b",0" if i and l else l for i, l in enumerate(dup.split(b"\n")))
    assert py_match(MODEL, quoted, "1e-9", "1e-12", tmp_path) == "FAIL"
    assert py_match(MODEL, dup, "1e-9", "1e-12", tmp_path) == "FAIL"


# ---------------------------------------------------------------------------
# Differential: Lean vs production
# ---------------------------------------------------------------------------

def _decimal_corpus(rng: random.Random) -> list[str]:
    fixed = ["0", "-0", "1", "-1", "0.5", "-02.50", "1e-9", "1E+21", "1e400", "1e401", "1e-400",
             "123.456e-7", "1.", ".1", "1e", "--1", "1e1e1", "١", "9" * 30, "0.000", "1e0400"]
    alphabet = "0123456789.-+eE _"
    return fixed + ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))
                    for _ in range(400)]


def _mutated_models(rng: random.Random) -> list[bytes]:
    base = json.loads(MODEL)
    out = [MODEL]

    def put(path, value):
        m = json.loads(MODEL)
        cur = m
        for k in path[:-1]:
            cur = cur[k]
        if value is KeyError:
            cur.pop(path[-1], None)
        else:
            cur[path[-1]] = value
        out.append(json.dumps(m).encode())

    for q in ["dose", "volume", "clearance"]:
        for v in [0, -1, 0.0, True, "1", None, 1e-30, 12345678901234567890, 2.5]:
            put([q, "value"], v)
        for u in ["", " ", "mg", "L", "L/h", "mL/min", "kg", "h", "mg^1", "mg / L", "furlong"]:
            put([q, "unit"], u)
        put([q], KeyError)
    for u in ["h", "min", "s", "mg", "", "h^2"]:
        put(["time_unit"], u)
    for u in ["mg/L", "ug/mL", "mol/L", "M", "kg/m^3", ""]:
        put(["concentration_unit"], u)
    put(["pd"], None)
    put(["pd"], KeyError)
    put(["pd"], 5)
    put(["pd", "model_type"], "hill")
    for k in ["e0", "emax", "ec50"]:
        for v in [0, -2.5, 1]:
            put(["pd", k, "value"], v)
        put(["pd", k, "unit"], "mg/L")
    put(["pd", "effect_unit"], "mg")
    put(["model_type"], "two_compartment")
    # raw-text JSON adversaries
    out += [MODEL.replace(b'"dose"', b'"dose": 1, "dose"', 1),           # duplicate key
            MODEL.replace(b"100.0", b"0100.0", 1),                          # leading zero
            MODEL.replace(b"100.0", b"NaN", 1),
            b"\xef\xbb\xbf" + MODEL,                                         # BOM
            MODEL + b"  \n",
            MODEL + b"x",
            MODEL.replace(b'"mg"', b'"m\x01g"', 1),                         # raw control char
            b"[]", b"", b"\xff"]
    del base, rng
    return out


def _perturbed_predictions(rng: random.Random) -> list[bytes]:
    lines = PRED.decode().splitlines()
    out = [PRED, PRED.replace(b"\n", b"\r\n")]
    for delta in ["0", "1e-13", "1e-11", "1e-7", "1e-3", "-1e-3", "-1e-11"]:
        rows = [lines[0]]
        for ln in lines[1:]:
            t, c, e = ln.split(",")
            c2 = Decimal(c) * (1 + Decimal(delta))
            rows.append(f"{t},{c2},{e}")
        out.append(("\n".join(rows) + "\n").encode())
        rows = [lines[0]]
        for ln in lines[1:]:
            t, c, e = ln.split(",")
            e2 = Decimal(e) * (1 + Decimal(delta))
            rows.append(f"{t},{c},{e2}")
        out.append(("\n".join(rows) + "\n").encode())
    out += [lines[0].encode() + b"\n",                                      # no data rows
            PRED.replace(b"\n0.5,", b"\n-0.5,", 1),                         # negative time
            PRED.replace(b"effect", b"eff", 1),                             # missing column
            PRED.replace(b"time,", b"t,", 1),
            PRED.replace(b"\n0.5,", b"\n0.50000,", 1),                      # same value
            PRED.replace(b"\n0.5,", b"\n5e-1,", 1),
            PRED.replace(b"\n0.5,", b"\n0.6,", 1)]                          # wrong time
    del rng
    return out


@pytest.mark.skipif(not lean_available(), reason="formal library not built")
def test_lean_python_pkpd_differential(tmp_path):
    rng = random.Random(20261001)
    queries: list[str] = []
    expected: list[str] = []
    for d in _decimal_corpus(rng):
        queries.append(f"D {x(d.encode())}")
        expected.append(py_decimal(d))
    for m in _mutated_models(rng):
        queries.append(f"M {x(m)}")
        expected.append(py_contract(m, tmp_path))
    for c in _perturbed_predictions(rng):
        for rel, abs_ in [("1e-9", "1e-12"), ("1e-6", "0"), ("0", "1e-3")]:
            queries.append(f"K {x(MODEL)} {x(c)} {rel} {abs_}")
            expected.append(py_match(MODEL, c, rel, abs_, tmp_path))
    got = run_lean(queries)
    mism = [(q[:80], e, g) for q, e, g in zip(queries, expected, got) if e != g]
    assert not mism, mism[:10]
    assert {"PASS", "FAIL", "REJECT"} <= set(got)
