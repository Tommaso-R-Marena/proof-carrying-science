"""Differential JCS checks: independent Rust reference vs PCS Python canonicalize_jcs."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .paths import RESULTS, RUST_CRATE


def _pcs_canonicalize(value: Any) -> str:
    from pcs.canonical_json import canonicalize_jcs

    return canonicalize_jcs(value)


def _pcs_jcs_sha256(value: Any) -> str:
    from pcs.canonical_json import jcs_sha256

    return jcs_sha256(value)


def ensure_rust_binary() -> Path:
    bin_path = RUST_CRATE / "target" / "release" / "pcs-independent-jcs"
    if bin_path.is_file():
        return bin_path
    subprocess.run(
        ["cargo", "build", "--release"],
        cwd=RUST_CRATE,
        check=True,
        capture_output=True,
        text=True,
    )
    if not bin_path.is_file():
        raise RuntimeError(f"rust binary missing after build: {bin_path}")
    return bin_path


def rust_canonicalize(raw_json: str, binary: Path | None = None) -> tuple[int, str, str]:
    binary = binary or ensure_rust_binary()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        tmp.write(raw_json)
        path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [str(binary), "canonicalize", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    finally:
        path.unlink(missing_ok=True)


def rust_hash(raw_json: str, binary: Path | None = None) -> tuple[int, str, str]:
    binary = binary or ensure_rust_binary()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        tmp.write(raw_json)
        path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [str(binary), "hash", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    finally:
        path.unlink(missing_ok=True)


VECTORS: list[dict[str, Any]] = [
    {"id": "empty_object", "json": "{}", "expect_accept": True},
    {"id": "key_order", "json": '{"b":1,"a":2}', "expect_accept": True},
    {"id": "nested", "json": '{"z":{"y":[3,2,1]},"a":null}', "expect_accept": True},
    {"id": "unicode_escape", "json": '{"cafe":"caf\\u00e9"}', "expect_accept": True},
    {"id": "duplicate_key", "json": '{"a":1,"a":2}', "expect_accept": False},
    {"id": "nan_literal", "json": "NaN", "expect_accept": False},
    {"id": "infinity", "json": "Infinity", "expect_accept": False},
    {"id": "neg_zero_number", "value": 0.0, "expect_accept": True},
    {"id": "large_int_as_float", "value": 9007199254740992, "expect_accept": True},
    {"id": "array_mixed", "value": [None, True, False, 1, "x"], "expect_accept": True},
    {"id": "empty_array", "json": "[]", "expect_accept": True},
    {"id": "nested_empty", "json": '{"a":[],"b":{}}', "expect_accept": True},
    {"id": "scientific", "value": 1e-7, "expect_accept": True},
    {"id": "scientific_large", "value": 1e21, "expect_accept": True},
    {"id": "bool_not_int", "value": True, "expect_accept": True},
    {"id": "string_surrogate_pair_ok", "json": '{"x":"\\uD83D\\uDE00"}', "expect_accept": True},
]


def run_differential(output: Path | None = None) -> dict[str, Any]:
    binary = ensure_rust_binary()
    disagreements: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for vec in VECTORS:
        case: dict[str, Any] = {"id": vec["id"]}
        if "json" in vec:
            raw = vec["json"]
            try:
                pcs_value = json.loads(raw)
                pcs_ok = True
                pcs_canon = _pcs_canonicalize(pcs_value)
                pcs_hash = _pcs_jcs_sha256(pcs_value)
            except Exception as exc:  # noqa: BLE001
                pcs_ok = False
                pcs_canon = None
                pcs_hash = None
                case["pcs_error"] = f"{type(exc).__name__}: {exc}"
            rc, rust_out, rust_err = rust_canonicalize(raw, binary)
            rust_ok = rc == 0
            case.update(
                {
                    "pcs_ok": pcs_ok,
                    "rust_ok": rust_ok,
                    "pcs_canonical": pcs_canon,
                    "rust_canonical": rust_out if rust_ok else None,
                    "rust_stderr": rust_err or None,
                }
            )
            if pcs_ok and rust_ok and pcs_canon != rust_out:
                disagreements.append(
                    {
                        "id": vec["id"],
                        "kind": "canonicalize_mismatch",
                        "pcs": pcs_canon,
                        "rust": rust_out,
                    }
                )
            if pcs_ok and rust_ok:
                rh_rc, rh, _ = rust_hash(raw, binary)
                if rh_rc == 0 and rh != pcs_hash:
                    disagreements.append(
                        {
                            "id": vec["id"],
                            "kind": "hash_mismatch",
                            "pcs": pcs_hash,
                            "rust": rh,
                        }
                    )
            if vec.get("expect_accept") is False and rust_ok and pcs_ok:
                disagreements.append(
                    {
                        "id": vec["id"],
                        "kind": "expected_reject_but_both_accepted",
                    }
                )
        else:
            value = vec["value"]
            pcs_canon = _pcs_canonicalize(value)
            pcs_hash = _pcs_jcs_sha256(value)
            raw = json.dumps(value)
            rc, rust_out, rust_err = rust_canonicalize(raw, binary)
            case.update(
                {
                    "pcs_ok": True,
                    "rust_ok": rc == 0,
                    "pcs_canonical": pcs_canon,
                    "rust_canonical": rust_out if rc == 0 else None,
                    "pcs_hash": pcs_hash,
                    "rust_stderr": rust_err or None,
                }
            )
            if rc == 0 and rust_out != pcs_canon:
                disagreements.append(
                    {
                        "id": vec["id"],
                        "kind": "canonicalize_mismatch",
                        "pcs": pcs_canon,
                        "rust": rust_out,
                    }
                )
        cases.append(case)

    report = {
        "format": "pcs-independent-jcs-differential-v1",
        "vector_count": len(VECTORS),
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
        "cases": cases,
        "note": (
            "Disagreements are observed differences between an independent Rust "
            "reference and PCS Python JCS; they are not automatically PCS defects."
        ),
    }
    out = output or (RESULTS / "jcs_differential.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
