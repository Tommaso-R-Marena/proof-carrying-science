#!/usr/bin/env python3
"""Independent replay of a ClaimCheck v1.1 bundle.

    python replay_independent_v1_1.py BUNDLE --checker-sha256 <digest of the reviewed ClaimCheck.lean>

Stand-alone: Python standard library only.  It imports nothing from the ClaimCheck packages.

What it does
  1. Checks the digests in the v1.1 index.
  2. Runs the v1 independent replayer on BUNDLE/v1 (a separate program, as a subprocess).  That
     re-derives every Lean file from the receipts, re-runs the real Lean kernel, and recomputes every
     statistic with different code.
  3. For every v1.1 record, recomputes with its own code:
       * the mathematical status, from the kernel-checked theorems in the v1 receipt;
       * the invariants (a CONFIRMATION needs a kernel-accepted match, a DISCREPANCY_FOR_REVIEW a
         kernel-accepted mismatch, every theorem bound to the same data digest);
       * the rules that are plain arithmetic or text matching: count, rounding convention,
         printed sample size, plain number, decoy rate against its limit;
       * that each corroborating number is itself a kernel-checked CONFIRMATION in the same sentence;
       * the outward verdict, from the findings.

What it does NOT recompute, and says so in its output
  * the enumeration of the eligible reading space behind the decoy and "no competing reading"
    findings, and the positional wording patterns.  Those are taken as recorded.

This is an independent SOFTWARE replay.  It is not an independent person reading the paper, and it
is not a replication of the science.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

SCHEMA = "pcs-claimcheck-replay-v1.1"
BASIC = ("unit_fits_the_quantity", "plain_number", "eligible_reading", "number_worded_as_this_statistic")
STRONG = BASIC + ("bounded_reading_space", "no_competing_reading_reproduces_the_number", "low_chance_of_coincidence")
SUPPORT = "supported_by_another_number_in_the_sentence"
SAMPLE_SIZE = re.compile(r"\b[nN]\s*=\s*([0-9][0-9,]*)(?![0-9.])")
UNIT_FAMILIES = {
    "mass": {"kg": Fraction(1000), "g": Fraction(1), "mg": Fraction(1, 1000), "µg": Fraction(1, 10**6), "ug": Fraction(1, 10**6)},
    "length": {"km": Fraction(1000), "m": Fraction(1), "cm": Fraction(1, 100), "mm": Fraction(1, 1000), "µm": Fraction(1, 10**6), "um": Fraction(1, 10**6)},
    "time": {"d": Fraction(86400), "h": Fraction(3600), "min": Fraction(60), "s": Fraction(1), "ms": Fraction(1, 1000)},
    "volume": {"L": Fraction(1), "l": Fraction(1), "mL": Fraction(1, 1000), "ml": Fraction(1, 1000), "µL": Fraction(1, 10**6), "ul": Fraction(1, 10**6)},
    "fraction": {"fraction": Fraction(1), "%": Fraction(1, 100)},
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def scale_of(spec: dict, manifest: dict) -> Fraction:
    data_unit = "fraction" if spec["stat"] == "share" else ((manifest.get("columns") or {}).get(spec.get("column") or "") or {}).get("unit")
    reported = spec.get("reported_unit")
    if reported is None or reported == data_unit:
        return Fraction(1)
    for table in UNIT_FAMILIES.values():
        if data_unit in table and reported in table:
            return table[data_unit] / table[reported]
    return Fraction(1)


def half_unit(literal: str) -> Fraction:
    mantissa, _, exp = literal.lower().partition("e")
    return Fraction(10) ** (int(exp or 0) - len(mantissa.partition(".")[2])) / 2


def sqrt_between(lo: Fraction, hi: Fraction, sign: int, q: Fraction) -> bool:
    """lo <= sign*sqrt(q) <= hi, decided in rationals."""
    if sign == 0 or q == 0:
        return lo <= 0 <= hi
    if sign > 0:
        return (lo <= 0 or lo * lo <= q) and (0 <= hi and q <= hi * hi)
    return (lo <= 0 and q <= lo * lo) and (0 <= hi or hi * hi <= q)


def math_status(receipt: dict) -> str:
    variants = (receipt.get("q1_mathematics") or {}).get("variants") or []
    states = []
    for v in variants:
        po, lean = v.get("predicted_outcome") or {}, v.get("lean") or {}
        if not lean.get("kernel_accepted"):
            states.append("none")
        elif not po.get("defined"):
            states.append("undefined")
        else:
            states.append("match" if po.get("verdict") == "consistent" else "mismatch")
    if not states or "none" in states:
        return "NOT_ESTABLISHED"
    if set(states) == {"match"}:
        return "MATCH_PROVED"
    if set(states) == {"mismatch"}:
        return "MISMATCH_PROVED"
    if set(states) == {"match", "mismatch"}:
        return "CONDITIONAL_ON_CONVENTION"
    return "UNDEFINED_PROVED" if set(states) == {"undefined"} else "NOT_ESTABLISHED"


def expected_verdict(record: dict, receipt: dict, math: str) -> str:
    findings = {f["rule"]: f["passed"] for f in record["source_reading"]["findings"]}
    q2 = receipt.get("q2_correspondence") or {}
    if math in ("NOT_ESTABLISHED", "UNDEFINED_PROVED"):
        return "UNKNOWN"
    if not (q2.get("checks") or {}).get("quote_in_source") or not (q2.get("checks") or {}).get("reported_value_in_quote"):
        return "UNKNOWN"
    if math == "CONDITIONAL_ON_CONVENTION" or receipt.get("result") not in ("PROVED", "REFUTED"):
        return "REQUIRE_HUMAN_REVIEW"
    if receipt["result"] == "PROVED":
        if all(findings.get(rule) for rule in STRONG):
            return "CONFIRMATION"
        if all(findings.get(rule) for rule in BASIC) and findings.get(SUPPORT) and record["source_reading"]["corroborated_by"]:
            return "CONFIRMATION"
        return "REQUIRE_HUMAN_REVIEW"
    flagged = findings and all(findings.values()) and findings.get(SUPPORT) and record["source_reading"]["corroborated_by"]
    return "DISCREPANCY_FOR_REVIEW" if flagged else "REQUIRE_HUMAN_REVIEW"


def check_record(record: dict, receipts: dict, records_by_receipt: dict, manifest: dict) -> list:
    issues = []
    receipt = receipts.get(record.get("v1_receipt_sha256"))
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if sha(canonical(body)) != record.get("record_sha256"):
        issues.append("the record's own digest does not match its content")
    if receipt is None:
        return issues + ["the record points to a v1 receipt that is not in the bundle"]
    if sha(canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"})) != receipt.get("receipt_sha256"):
        issues.append("the v1 receipt's digest does not match its content")
    math = math_status(receipt)
    verdict = record["outward"]["verdict"]
    if record["mathematical"]["status"] != math:
        issues.append(f"mathematical status {record['mathematical']['status']} is not what the kernel-checked theorems support ({math})")
    if record.get("v1_result") != receipt.get("result"):
        issues.append("the recorded v1 result differs from the v1 receipt")
    if verdict == "CONFIRMATION" and not (receipt.get("result") == "PROVED" and math == "MATCH_PROVED"):
        issues.append("CONFIRMATION without a kernel-accepted match under the v1 gates")
    if verdict == "DISCREPANCY_FOR_REVIEW" and not (receipt.get("result") == "REFUTED" and math == "MISMATCH_PROVED"):
        issues.append("DISCREPANCY_FOR_REVIEW without a kernel-accepted mismatch under the v1 gates")
    if record["mathematical"].get("data_sha256") != (receipt.get("data") or {}).get("sha256"):
        issues.append("the record names a different data digest than the receipt")
    if record["scientific"]["status"] != "NOT_ASSESSED":
        issues.append("the scientific layer must be NOT_ASSESSED")
    if record["source_reading"].get("reviewed_by_a_person"):
        issues.append("a record may not claim that a person reviewed the reading")
    want = expected_verdict(record, receipt, math)
    if verdict != want:
        issues.append(f"outward verdict {verdict} is not what the findings support ({want})")
    findings = {f["rule"]: f for f in record["source_reading"]["findings"]}
    spec = (receipt.get("claim") or {}).get("spec") or {}
    q2 = receipt.get("q2_correspondence") or {}
    # ---- rules recomputed here ------------------------------------------------------------------
    rv = q2.get("reported_value") or {}
    if "plain_number" in findings:
        plain = re.fullmatch(r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", rv.get("literal_checked", "")) is not None
        if findings["plain_number"]["passed"] and not plain:
            issues.append("plain_number passed for a token with leading zeros")
    f = findings.get("low_chance_of_coincidence")
    if f is not None:
        limit = Fraction(record["source_reading"]["policy"]["max_decoy_coincidence_rate"])
        ok = Fraction(f["decoys_reproduced"] + 1, f["decoys"] + 1) <= limit        # the printed number counts among the comparable ones
        if ok != f["passed"]:
            issues.append("the decoy finding does not follow from its own numbers")
    if receipt.get("result") == "REFUTED" and findings:
        if "not_a_count" in findings and findings["not_a_count"]["passed"] != (spec.get("stat") != "count"):
            issues.append("the count rule was not applied correctly")
        if "beyond_rounding_convention" in findings:
            unit = 2 * half_unit(spec["reported"])
            scale = scale_of(spec, manifest)
            close = False
            for v in (receipt.get("q1_mathematics") or {}).get("variants", []):
                po = v.get("predicted_outcome") or {}
                if po.get("defined"):
                    value = Fraction(int(po["exact"]["numerator"]), int(po["exact"]["denominator"]))
                    rep = Fraction(spec["reported"])
                    if po.get("value_kind") == "rational":
                        close = close or abs(value * scale - rep) <= unit
                    else:
                        close = close or sqrt_between((rep - unit) / scale, (rep + unit) / scale, po.get("sign") or 0, value)
            if findings["beyond_rounding_convention"]["passed"] == close:
                issues.append("the rounding-convention rule does not follow from the kernel-checked value")
        if "printed_sample_size_agrees" in findings:
            sentence = (q2.get("sentence") or {}).get("text") or ""
            printed = {int(m.group(1).replace(",", "")) for m in SAMPLE_SIZE.finditer(sentence)}
            used = next(((v.get("predicted_outcome") or {}).get("rows_used") for v in (receipt.get("q1_mathematics") or {}).get("variants", [])
                         if (v.get("predicted_outcome") or {}).get("defined")), None)
            if findings["printed_sample_size_agrees"]["passed"] != (not printed or used in printed):
                issues.append("the printed-sample-size rule was not applied correctly")
    f = findings.get(SUPPORT)
    if f is not None and receipt.get("result") == "PROVED" and "decoys" in f:
        limit = Fraction(record["source_reading"]["policy"]["max_decoy_coincidence_rate"])
        if f["passed"] and Fraction(f["decoys_reproduced"] + 1, f["decoys"] + 1) > limit:
            issues.append("the sibling-support finding does not follow from its own numbers")
    # ---- corroboration ----------------------------------------------------------------------------
    for c in record["source_reading"]["corroborated_by"]:
        other = receipts.get(c.get("receipt_sha256"))
        other_record = records_by_receipt.get(c.get("receipt_sha256"))
        if other is None or other_record is None:
            issues.append("a corroborating number is not a receipt in this bundle")
            continue
        o2 = other.get("q2_correspondence") or {}
        if other.get("result") != "PROVED" or math_status(other) != "MATCH_PROVED":
            issues.append("a corroborating number is not a kernel-accepted match")
        if other_record["outward"]["verdict"] != "CONFIRMATION":
            issues.append("a corroborating number is not itself a CONFIRMATION")
        if (o2.get("sentence") or {}).get("start") != (q2.get("sentence") or {}).get("start"):
            issues.append("a corroborating number is in a different sentence")
        if (o2.get("reported_value") or {}).get("start") == rv.get("start"):
            issues.append("a number cannot corroborate itself")
        if receipt.get("result") == "REFUTED" and ((other.get("claim") or {}).get("spec") or {}).get("column") != spec.get("column"):
            issues.append("a mismatch is corroborated by a number from another column")
    return issues


def replay(bundle: Path, checker_sha256: str, v1_replayer: Path, skip_lean: bool, timeout: int) -> tuple:
    problems = []
    index = json.loads((bundle / "claimcheck_v1_1.json").read_text(encoding="utf-8"))
    for name, digest in index.get("files", {}).items():
        path = bundle / name
        if not path.is_file():
            problems.append(f"missing file: {name}")
        elif sha(path.read_bytes()) != digest:
            problems.append(f"digest mismatch: {name}")
    if index.get("checker_sha256") != checker_sha256:
        problems.append("the bundle names a different checker than the reviewed one you supplied")
    cmd = [sys.executable, str(v1_replayer), str(bundle / "v1"), "--checker-sha256", checker_sha256, "--timeout", str(timeout)]
    if skip_lean:
        cmd.append("--skip-lean")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ))
    try:
        v1 = json.loads(proc.stdout)
    except ValueError:
        v1 = {"all_replayed": False, "error": (proc.stderr or proc.stdout)[-400:]}
    if not v1.get("all_replayed"):
        problems.append("the v1 replay of the kernel evidence did not succeed")
    records = json.loads((bundle / "records.json").read_text(encoding="utf-8"))
    receipts = {r.get("receipt_sha256"): r for r in json.loads((bundle / "v1" / "receipts.json").read_text(encoding="utf-8"))}
    manifest = json.loads((bundle / "v1" / "manifest.json").read_text(encoding="utf-8"))
    by_receipt = {r.get("v1_receipt_sha256"): r for r in records}
    if len(records) != len(receipts):
        problems.append("the number of v1.1 records differs from the number of v1 receipts")
    rows = []
    for record in records:
        issues = check_record(record, receipts, by_receipt, manifest)
        rows.append({"claim_id": record.get("claim_id"), "verdict": record["outward"]["verdict"],
                     "mathematical": record["mathematical"]["status"], "issues": issues, "replayed": not issues})
    ok = not problems and all(r["replayed"] for r in rows)
    summary = {
        "schema": SCHEMA, "bundle": str(bundle), "all_replayed": ok, "proofs_rechecked_by_the_lean_kernel": not skip_lean and bool(v1.get("all_replayed")),
        "bundle_problems": problems,
        "v1_replay": {"all_replayed": v1.get("all_replayed"), "obligation_files_rechecked": (v1.get("results") or [{}])[0].get("obligation_files_rechecked"),
                      "bundle_problems": (v1.get("results") or [{}])[0].get("bundle_problems"), "error": v1.get("error")},
        "records": rows,
        "taken_as_recorded_not_recomputed": [
            "the enumeration of the eligible reading space (decoy counts, competing readings)",
            "the positional wording patterns that attach a number to a statistic",
            "the incompatible-unit and out-of-grammar wording checks"],
        "what_this_is": "An independent software replay. Not an independent human reading of the paper and not a scientific replication.",
    }
    return summary, ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--checker-sha256", required=True, help="digest of the reviewed ClaimCheck.lean, obtained independently of the bundle")
    ap.add_argument("--v1-replayer", type=Path, default=Path(__file__).resolve().parent.parent / "claimcheck_v1" / "replay_independent.py")
    ap.add_argument("--skip-lean", action="store_true", help="integrity and recomputation only (NOT a proof replay)")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args(argv)
    summary, ok = replay(args.bundle, args.checker_sha256, args.v1_replayer, args.skip_lean, args.timeout)
    text = json.dumps(summary, indent=1, ensure_ascii=False)
    if args.report:
        args.report.write_text(text, encoding="utf-8")
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
