#!/usr/bin/env python3
"""Independent replay of a ClaimCheck evidence bundle.

This single file deliberately imports NOTHING from the ClaimCheck package.  It
re-derives every fact it reports:

  1. every bundled file matches the digest recorded in bundle.json;
  2. the bundled checker is the reviewed checker (digest given by YOU, the reviewer);
  3. each Lean obligation is exactly: checker text + data numeral + claim + theorem, where
       - the numeral decodes to the bundled data file byte for byte,
       - the claim and expected outcome are re-rendered here from the receipt and compared;
  4. the real Lean compiler accepts each obligation afresh, using only standard axioms;
  5. the quoted text and the printed number are at the recorded offsets of the bundled source;
  6. a second, differently written calculation (Python csv + Decimal) agrees with the
     kernel-checked value and verdict.

It needs Python 3.11+ and Lean 4.28.0 on PATH (or PCS_CLAIMCHECK_LEAN).  Exit code 0 only if
every receipt replays.  A successful replay re-establishes what the receipts say and nothing
more: it does not establish data custody, the meaning of a sentence, or any scientific conclusion.
"""
from __future__ import annotations

import argparse
import csv
import decimal
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

THEOREM = "pcs_claim_outcome"
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
SAFE = re.compile(r"[A-Za-z0-9 _.,:;()\[\]%/+\-#=<>&*!?@^|~]*\Z")
STAT = {"count": ".count", "sum": ".sum", "mean": ".mean", "median": ".median", "min": ".min", "max": ".max",
        "var_sample": ".varSample", "sd_sample": ".sdSample", "sd_pop": ".sdPop", "sem": ".sem"}
UNITS = [
    {"kg": Fraction(1000), "g": Fraction(1), "mg": Fraction(1, 1000), "µg": Fraction(1, 10**6), "ug": Fraction(1, 10**6)},
    {"km": Fraction(1000), "m": Fraction(1), "cm": Fraction(1, 100), "mm": Fraction(1, 1000), "µm": Fraction(1, 10**6), "um": Fraction(1, 10**6)},
    {"d": Fraction(86400), "h": Fraction(3600), "min": Fraction(60), "s": Fraction(1), "ms": Fraction(1, 1000)},
    {"L": Fraction(1), "l": Fraction(1), "mL": Fraction(1, 1000), "ml": Fraction(1, 1000), "µL": Fraction(1, 10**6), "ul": Fraction(1, 10**6)},
    {"fraction": Fraction(1), "%": Fraction(1, 100)},
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def lb(text: str) -> str:
    return f'b "{text}"' if SAFE.match(text) else "[" + ", ".join(str(x) for x in text.encode("utf-8")) + "]"


def rat(q: Fraction) -> str:
    return f"(({q.numerator} : Rat) / {q.denominator})"


def cond(c: dict) -> str:
    if c["kind"] == "text_eq":
        return f".textEq ({lb(c['column'])}) ({lb(c['value'])})"
    if c["kind"] == "text_ne":
        return f".textNe ({lb(c['column'])}) ({lb(c['value'])})"
    return f".num ({lb(c['column'])}) .{c['cmp']} {rat(Fraction(c['value']))}"


def conds(cs: list) -> str:
    return "[" + ", ".join(cond(c) for c in cs) + "]"


def scale_for(spec: dict, stat: str, manifest: dict) -> Fraction:
    data_unit = "fraction" if stat == "share" else ((manifest.get("columns") or {}).get(spec.get("column") or "") or {}).get("unit")
    rep = spec.get("reported_unit")
    if rep is None or rep == data_unit:
        return Fraction(1)
    for fam in UNITS:
        if data_unit in fam and rep in fam:
            return fam[data_unit] / fam[rep]
    raise ValueError("unit conversion in receipt is not derivable")


def render_tail(data: bytes, spec: dict, stat: str, manifest: dict, outcome: dict) -> str:
    """Independent re-rendering of the generated part of an obligation from receipt fields."""
    if stat == "share":
        st = f".share {conds(spec['sub_filter'])}"
    elif stat == "pearson":
        st = f".pearson ({lb(spec['x_column'])})"
    elif stat == "ols_slope":
        st = f".olsSlope ({lb(spec['x_column'])})"
    elif stat == "ols_intercept":
        st = f".olsIntercept ({lb(spec['x_column'])})"
    else:
        st = STAT[stat]
    column = "none" if spec.get("column") is None else f"some ({lb(spec['column'])})"
    na = "[" + ", ".join(lb(t) for t in (manifest.get("na_tokens") or ["", "NA"])) + "]"
    if not outcome["defined"]:
        exp = f".undefined .{outcome['reason']}"
    else:
        q = Fraction(int(outcome["exact"]["numerator"]), int(outcome["exact"]["denominator"]))
        val = f"(.rat {rat(q)})" if outcome["value_kind"] == "rational" else f"(.sqrt ({outcome['sign']} : Int) {rat(q)})"
        exp = f".checked .{outcome['verdict']} {val} {outcome['rows_used']} {outcome['rows_skipped_as_missing']}"
    return (
        "\n-- ===== generated obligation (data numeral, claim, expected outcome) =====\n"
        "open PCS.ClaimCheck\n\n"
        f"def pcs_src : Source := ⟨0x{data.hex() or '0'}, {len(data)}⟩\n\n"
        "def pcs_claim : Claim :=\n"
        "  { column := " + column + ",\n"
        "    filter := " + conds(spec["filter"]) + ",\n"
        "    stat := " + st + ",\n"
        "    naTokens := " + na + ",\n"
        "    scale := " + rat(scale_for(spec, stat, manifest)) + ",\n"
        "    reported := " + lb(spec["reported"]) + " }\n\n"
        f"theorem {THEOREM} : run pcs_src pcs_claim = {exp} := by decide +kernel\n\n"
        f"#print axioms {THEOREM}\n"
    )


def run_lean(lean: str, text: str, timeout: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="pcs-claimcheck-replay-") as tmp:
        path = Path(tmp) / "Obligation.lean"
        path.write_text(text, encoding="utf-8")
        try:
            p = subprocess.run([lean, str(path)], capture_output=True, text=True, timeout=timeout, cwd=tmp,
                               env={"PATH": os.environ.get("PATH", ""), "HOME": tmp, "LANG": "C.UTF-8"})
        except subprocess.TimeoutExpired:
            return False, "timeout"
    out = p.stdout.strip()
    if p.returncode != 0 or p.stderr.strip():
        return False, "lean rejected: " + (out.splitlines() or ["?"])[0][:200]
    if out == f"'{THEOREM}' does not depend on any axioms":
        return True, "no axioms"
    m = re.fullmatch(r"'" + THEOREM + r"' depends on axioms: \[([A-Za-z0-9_., ]*)\]", out)
    if not m:
        return False, "unexpected lean output"
    axioms = {a.strip() for a in m.group(1).split(",") if a.strip()}
    if not axioms <= ALLOWED_AXIOMS:
        return False, "non-standard axioms: " + ", ".join(sorted(axioms - ALLOWED_AXIOMS))
    return True, "axioms: " + ", ".join(sorted(axioms))


# ---- second calculation: csv module + Decimal --------------------------------------------------
def second_opinion(data: bytes, spec: dict, stat: str, manifest: dict):
    """Return (approximate value in data units, rows used) using a different parser and arithmetic."""
    decimal.getcontext().prec = 60
    text = data.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    header = [h.strip(" \t") for h in rows[0]]
    body = rows[1:]
    na = set(manifest.get("na_tokens") or ["", "NA"])

    def col(name):
        return header.index(name)

    def passes(row, cs):
        for c in cs:
            cell = row[col(c["column"])].strip(" \t")
            if c["kind"] == "text_eq":
                ok = cell == c["value"]
            elif c["kind"] == "text_ne":
                ok = cell != c["value"]
            else:
                if cell in na:
                    return False
                x, y = Decimal(cell), Decimal(c["value"])
                ok = {"eq": x == y, "ne": x != y, "lt": x < y, "le": x <= y, "gt": x > y, "ge": x >= y}[c["cmp"]]
            if not ok:
                return False
        return True

    sel = [r for r in body if passes(r, spec["filter"])]
    if stat == "count":
        if spec.get("column") is None:
            return Decimal(len(sel)), len(sel)
        n = sum(1 for r in sel if r[col(spec["column"])].strip(" \t") not in na)
        return Decimal(n), n
    if stat == "share":
        hit = [r for r in sel if passes(r, spec["sub_filter"])]
        return Decimal(len(hit)) / Decimal(len(sel)), len(sel)
    if stat in ("pearson", "ols_slope", "ols_intercept"):
        ix, iy = col(spec["x_column"]), col(spec["column"])
        pairs = [(Decimal(r[ix].strip()), Decimal(r[iy].strip())) for r in sel
                 if r[ix].strip(" \t") not in na and r[iy].strip(" \t") not in na]
        n = len(pairs)
        mx = sum(p[0] for p in pairs) / n
        my = sum(p[1] for p in pairs) / n
        sxx = sum((p[0] - mx) ** 2 for p in pairs)
        syy = sum((p[1] - my) ** 2 for p in pairs)
        sxy = sum((p[0] - mx) * (p[1] - my) for p in pairs)
        if stat == "pearson":
            return sxy / (sxx * syy).sqrt(), n
        if stat == "ols_slope":
            return sxy / sxx, n
        return my - sxy / sxx * mx, n
    xs = [Decimal(r[col(spec["column"])].strip(" \t")) for r in sel if r[col(spec["column"])].strip(" \t") not in na]
    n = len(xs)
    m = sum(xs) / n
    ss = sum((x - m) ** 2 for x in xs)
    if stat == "sum":
        return sum(xs), n
    if stat == "mean":
        return m, n
    if stat == "median":
        s = sorted(xs)
        return (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2), n
    if stat == "min":
        return min(xs), n
    if stat == "max":
        return max(xs), n
    if stat == "var_sample":
        return ss / (n - 1), n
    if stat == "sd_sample":
        return (ss / (n - 1)).sqrt(), n
    if stat == "sd_pop":
        return (ss / n).sqrt(), n
    if stat == "sem":
        return (ss / (n - 1) / n).sqrt(), n
    raise ValueError("unknown statistic")


def replay(bundle: Path, checker_sha256: str | None, timeout: int, skip_lean: bool) -> tuple[list[dict], bool]:
    index = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    listed = set(index["files"])
    present = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file() and p.name != "bundle.json"}
    for name in sorted(listed | present):
        if name not in present:
            problems.append(f"missing file: {name}")
        elif name not in listed:
            problems.append(f"file not in bundle index: {name}")
        elif sha((bundle / name).read_bytes()) != index["files"][name]["sha256"]:
            problems.append(f"digest mismatch: {name}")
    checker = (bundle / "ClaimCheck.lean").read_text(encoding="utf-8")
    if checker_sha256 and sha(checker.encode("utf-8")) != checker_sha256:
        problems.append("bundled ClaimCheck.lean is not the reviewed checker you named")
    data = (bundle / "data.csv").read_bytes()
    source = (bundle / "source.txt").read_bytes().decode("utf-8")
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    receipts = json.loads((bundle / "receipts.json").read_text(encoding="utf-8"))
    lean = os.environ.get("PCS_CLAIMCHECK_LEAN") or shutil.which("lean")
    if not skip_lean:
        if not lean:
            problems.append("no lean executable: cannot replay proofs")
        else:
            ver = subprocess.run([lean, "--version"], capture_output=True, text=True).stdout
            if "version 4.28.0," not in ver:
                problems.append("Lean 4.28.0 required")
    results = []
    for r in receipts:
        row = {"claim_id": r["claim_id"], "recorded_result": r["result"], "issues": []}
        issues = row["issues"]
        body = {k: v for k, v in r.items() if k != "receipt_sha256"}
        canon = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        if sha(canon) != r.get("receipt_sha256"):
            issues.append("receipt digest does not match its content")
        if r["data"]["sha256"] != sha(data):
            issues.append("receipt names different data bytes")
        if r["source"]["sha256"] != sha(source.encode("utf-8")):
            issues.append("receipt names a different source text")
        q2 = r.get("q2_correspondence", {})
        if "quote" in q2 and source[q2["quote"]["start"]:q2["quote"]["end"]] != q2["quote"]["text"]:
            issues.append("quote is not at the recorded source offsets")
        if "reported_value" in q2:
            rv = q2["reported_value"]
            if source[rv["start"]:rv["end"]] != rv["printed"]:
                issues.append("reported number is not at the recorded source offsets")
            printed = rv["printed"].replace(",", "").replace("−", "-")
            if Fraction(printed) != Fraction(rv["literal_checked"]) or printed.lstrip("+-") != rv["literal_checked"].lstrip("+-"):
                issues.append("checked literal differs from the printed number")
        statuses = []
        for v in r.get("q1_mathematics", {}).get("variants", []):
            lean_rec, po = v.get("lean", {}), v["predicted_outcome"]
            if not lean_rec.get("kernel_accepted"):
                statuses.append("UNKNOWN")
                continue
            spec = r["claim"]["spec"]
            try:
                tail = render_tail(data, spec, v["stat"], manifest, po)
            except Exception as exc:  # noqa: BLE001 - any failure is a replay failure
                issues.append(f"cannot re-render obligation: {exc}")
                statuses.append("UNKNOWN")
                continue
            expected_text = checker + tail
            name = lean_rec.get("obligation_file")
            if name:
                on_disk = (bundle / "obligations" / name).read_text(encoding="utf-8")
                if on_disk != expected_text:
                    issues.append(f"{name}: bundled obligation differs from the one derived from the receipt")
            if sha(expected_text.encode("utf-8")) != lean_rec.get("obligation_sha256"):
                issues.append("obligation digest in receipt differs from the re-derived obligation")
            if not skip_lean and lean:
                ok, detail = run_lean(lean, expected_text, timeout)
                if not ok:
                    issues.append(f"fresh Lean check failed ({detail})")
            if po["defined"]:
                try:
                    approx, used = second_opinion(data, spec, v["stat"], manifest)
                    scale = scale_for(spec, v["stat"], manifest)
                    q = Fraction(int(po["exact"]["numerator"]), int(po["exact"]["denominator"]))
                    exact = Decimal(q.numerator) / Decimal(q.denominator)
                    if po["value_kind"] != "rational":
                        exact = exact.sqrt() * po["sign"]
                    if used != po["rows_used"]:
                        issues.append("second calculation used a different number of rows")
                    if abs(approx - exact) > Decimal(10) ** -30 * max(Decimal(1), abs(exact)):
                        issues.append("second calculation disagrees with the kernel-checked value")
                    rep = Decimal(spec["reported"])
                    frac_digits = len(spec["reported"].lower().partition("e")[0].partition(".")[2])
                    exp = int(spec["reported"].lower().partition("e")[2] or 0)
                    half = Decimal(10) ** (exp - frac_digits) / 2
                    sc = Decimal(scale.numerator) / Decimal(scale.denominator)
                    verdict = "consistent" if abs(approx * sc - rep) <= half else "inconsistent"
                    margin = abs(abs(approx * sc - rep) - half)
                    if verdict != po["verdict"] and margin > Decimal(10) ** -25:
                        issues.append("second calculation reaches a different verdict")
                except Exception as exc:  # noqa: BLE001
                    issues.append(f"second calculation failed: {type(exc).__name__}")
                statuses.append("PROVED" if po["verdict"] == "consistent" else "REFUTED")
            else:
                statuses.append("UNKNOWN")
        # recompute Q1 status and the headline from the variants
        if not statuses:
            q1 = "UNKNOWN"
        elif len(set(statuses)) == 1:
            q1 = statuses[0]
        else:
            q1 = "UNKNOWN"
        recorded_q1 = r.get("q1_mathematics", {}).get("status", "UNKNOWN")
        if q1 != recorded_q1:
            issues.append(f"Q1 status {recorded_q1} is not what the variants support ({q1})")
        grounded = q2.get("status") == "GROUNDED"
        headline = q1 if (grounded and q1 in ("PROVED", "REFUTED")) else "UNKNOWN"
        if headline != r["result"]:
            issues.append(f"result {r['result']} is not what Q1 and Q2 support ({headline})")
        row["replayed"] = not issues
        results.append(row)
    ok = not problems and all(x["replayed"] for x in results)
    return [{"bundle_problems": problems}] + results, ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--checker-sha256", help="digest of the reviewed ClaimCheck.lean (obtain it independently of the bundle)")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--skip-lean", action="store_true", help="integrity and second-calculation checks only (NOT a proof replay)")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args(argv)
    results, ok = replay(args.bundle, args.checker_sha256, args.timeout, args.skip_lean)
    summary = {
        "schema": "pcs-claimcheck-replay-v1", "bundle": str(args.bundle), "all_replayed": ok,
        "proofs_rechecked": not args.skip_lean, "checker_digest_supplied_by_reviewer": bool(args.checker_sha256),
        "results": results,
    }
    text = json.dumps(summary, indent=1, ensure_ascii=False)
    if args.report:
        args.report.write_text(text, encoding="utf-8")
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
