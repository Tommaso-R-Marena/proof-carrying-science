"""Live Lean controls for ClaimCheck (fails if Lean 4.28.0 is unavailable — it never skips).

    python -m research.claimcheck_v1.check_live [--fuzz 300] [--seed 20261110]

1. Positive controls: fixed claims whose predicted outcome the kernel must accept.
2. Negative controls: forged outcomes (wrong verdict, wrong exact value, wrong row count, wrong
   reason) and a silently altered data numeral.  The kernel must REJECT every one.
3. Differential fuzz: random CSV dialects (quotes, CRLF, BOM, missing values, malformed files) and
   random claims.  The Python oracle and the Lean checker are two independent implementations of
   the same semantics; the kernel must accept every oracle prediction.  Any disagreement fails.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import replace
from fractions import Fraction

from .lean import batch_source, check_source, checker_text, lean_claim, lean_outcome, obligation_source
from .oracle import Outcome, evaluate
from .spec import ClaimSpec, Cond

NA = ("", "NA")
FIXTURE = (
    b"id,group,mass_g,len_mm,note\r\n"
    b"1,a,10.5,100,\"x, y\"\r\n"
    b"2,a,11.5,104,ok\r\n"
    b"3,b,NA,98,\"say \"\"hi\"\"\"\r\n"
    b"4,b,9.25,97,ok\r\n"
    b"5,b,12,1.01e2,ok\r\n"
)


def _spec(**kw) -> ClaimSpec:
    kw.setdefault("filter", ())
    kw.setdefault("sub_filter", ())
    return ClaimSpec(**kw)


POSITIVE = [
    _spec(stat="mean", column="mass_g", reported="10.81"),
    _spec(stat="mean", column="mass_g", reported="10.8"),
    _spec(stat="mean", column="mass_g", reported="10.9"),                      # inconsistent
    _spec(stat="sd_sample", column="mass_g", reported="1.21"),
    _spec(stat="sd_pop", column="mass_g", reported="1.05"),
    _spec(stat="sem", column="mass_g", reported="0.6"),
    _spec(stat="var_sample", column="mass_g", reported="1.47"),
    _spec(stat="median", column="len_mm", reported="100"),
    _spec(stat="min", column="len_mm", reported="97"),
    _spec(stat="max", column="len_mm", reported="104"),
    _spec(stat="sum", column="mass_g", reported="43.25"),
    _spec(stat="count", reported="5"),
    _spec(stat="count", column="mass_g", reported="4"),
    _spec(stat="count", reported="3", filter=(Cond("text_eq", "group", "b"),)),
    _spec(stat="share", reported="60", sub_filter=(Cond("text_eq", "group", "b"),)),
    _spec(stat="share", reported="0.4", sub_filter=(Cond("text_ne", "group", "b"),)),
    _spec(stat="mean", column="mass_g", reported="11.0", filter=(Cond("text_eq", "group", "a"),)),
    _spec(stat="mean", column="len_mm", reported="98.5", filter=(Cond("num", "mass_g", "9.25", "ge"), Cond("text_eq", "group", "b"))),
    _spec(stat="pearson", column="mass_g", x_column="len_mm", reported="0.76"),
    _spec(stat="pearson", column="mass_g", x_column="len_mm", reported="-0.76"),  # inconsistent
    _spec(stat="ols_slope", column="mass_g", x_column="len_mm", reported="0.31"),
    _spec(stat="ols_intercept", column="mass_g", x_column="len_mm", reported="-20.7"),
    _spec(stat="mean", column="nope", reported="1"),                              # undefined: column
    _spec(stat="mean", column="note", reported="1"),                              # undefined: non-numeric
    _spec(stat="mean", column="mass_g", reported="1", filter=(Cond("text_eq", "group", "zzz"),)),  # undefined: empty
]
SCALES = {14: Fraction(100)}  # share reported as a percentage


def _batch(cases: list[tuple[bytes, ClaimSpec, tuple, Fraction, Outcome]]) -> tuple[str, int]:
    """One file, one independent single-claim theorem per case (cases have different data)."""
    parts = [checker_text(), "\nopen PCS.ClaimCheck\n"]
    for i, (data, spec, na, scale, outcome) in enumerate(cases):
        parts.append(f"def s{i} : Source := ⟨0x{data.hex() or '0'}, {len(data)}⟩\n")
        parts.append(f"def c{i} : Claim :=\n  {lean_claim(spec, na, scale)}\n")
        parts.append(f"theorem pcs_claim_{i} : run s{i} c{i} = {lean_outcome(outcome)} := by decide +kernel\n#print axioms pcs_claim_{i}\n")
    return "".join(parts), len(cases)


def _forge(o: Outcome, rng: random.Random) -> Outcome:
    if not o.defined:
        other = "csvMalformed" if o.reason != "csvMalformed" else "columnNotFound"
        return replace(o, reason=other)
    kind = rng.choice(["verdict", "value", "used", "missing"])
    if kind == "verdict":
        return replace(o, verdict="inconsistent" if o.verdict == "consistent" else "consistent")
    if kind == "value":
        return replace(o, value=o.value + Fraction(1, 10**9))
    if kind == "used":
        return replace(o, used=o.used + 1)
    return replace(o, missing=o.missing + 1)


def _cell(rng: random.Random) -> str:
    r = rng.random()
    if r < 0.08:
        return rng.choice(["NA", ""])
    if r < 0.12:
        return f"{rng.randint(1, 99)}e{rng.randint(-3, 3)}"
    if r < 0.5:
        return str(rng.randint(-50, 500))
    return f"{rng.randint(-50, 500)}.{rng.randint(0, 999):0{rng.randint(1, 3)}d}"


def _random_case(rng: random.Random) -> tuple[bytes, ClaimSpec, tuple, Fraction]:
    n = rng.randint(0, 9)
    groups = ["a", "b", "c c"]
    rows = [["g", "x", "y", "t"]]
    for _ in range(n):
        rows.append([rng.choice(groups), _cell(rng), _cell(rng), rng.choice(["ok", "p, q", 'say "hi"', "", "7"])])
    bad = rng.random()
    if bad < 0.04 and n:
        rows[rng.randrange(1, n + 1)].append("extra")
    elif bad < 0.08 and n:
        rows[rng.randrange(1, n + 1)][1] = "abc"
    elif bad < 0.10:
        rows[0][2] = "x"                       # duplicate header
    eol = rng.choice(["\n", "\r\n", "\r"])
    lines = []
    for r in rows:
        cells = []
        for c in r:
            if any(ch in c for ch in ',"\n') or rng.random() < 0.1:
                c = '"' + c.replace('"', '""') + '"'
            cells.append(c)
        lines.append(",".join(cells))
    text = eol.join(lines) + (eol if rng.random() < 0.8 else "")
    if bad > 0.97:
        text = text.replace(eol, eol + eol, 1)  # blank line
    if 0.94 < bad <= 0.97:
        text += '"unterminated'
    data = (b"\xef\xbb\xbf" if rng.random() < 0.1 else b"") + text.encode("utf-8")
    stat = rng.choice(["count", "share", "sum", "mean", "median", "min", "max", "var_sample", "sd_sample", "sd_pop",
                       "sem", "pearson", "ols_slope", "ols_intercept"])
    filt = ()
    r = rng.random()
    if r < 0.3:
        filt = (Cond("text_eq", "g", rng.choice(groups)),)
    elif r < 0.4:
        filt = (Cond("text_ne", "g", rng.choice(groups)),)
    elif r < 0.55:
        filt = (Cond("num", rng.choice(["x", "y", "t"]), str(rng.randint(0, 200)), rng.choice(["lt", "le", "gt", "ge", "eq", "ne"])),)
    elif r < 0.6:
        filt = (Cond("text_eq", "missing_col", "a"),)
    column = rng.choice(["x", "y"]) if stat not in ("count", "share") or rng.random() < 0.3 else None
    if stat == "share":
        column = None
    spec = ClaimSpec(stat=stat, reported="0", column=column, x_column=("y" if column == "x" else "x") if stat in ("pearson", "ols_slope", "ols_intercept") else None,
                     filter=filt, sub_filter=(Cond("text_eq", "g", rng.choice(groups)),) if stat == "share" else ())
    scale = rng.choice([Fraction(1), Fraction(1), Fraction(1, 1000), Fraction(100)])
    probe = evaluate(data, spec, NA, scale)
    reported = "0"
    if probe.defined:
        approx = probe.approx() * float(scale)
        digits = rng.randint(0, 3)
        nudge = rng.choice([0, 0, 0, 1, -1]) * 10 ** -digits
        reported = f"{approx + nudge:.{digits}f}"
        if reported.startswith("-0") and float(reported) == 0:
            reported = reported[1:]
    return data, replace(spec, reported=reported), NA, scale


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuzz", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20261110)
    ap.add_argument("--report")
    args = ap.parse_args(argv)
    rng = random.Random(args.seed)
    report = {"positive": 0, "negative_rejected": 0, "fuzz_cases": 0, "fuzz_outcomes": {}, "failures": []}
    t0 = time.monotonic()

    cases = [(FIXTURE, s, NA, SCALES.get(i, Fraction(1)), evaluate(FIXTURE, s, NA, SCALES.get(i, Fraction(1)))) for i, s in enumerate(POSITIVE)]
    text, n = _batch(cases)
    res = check_source(text, claims=n)
    if not res.accepted:
        report["failures"].append(f"positive controls rejected: {res.detail}")
    report["positive"] = len(cases)
    kinds = sorted({(c[4].verdict or c[4].reason) for c in cases})
    report["positive_outcome_kinds"] = kinds

    # each forged obligation must be rejected on its own
    for i, (data, spec, na, scale, outcome) in enumerate(cases):
        if i % 3:
            continue
        forged = _forge(outcome, rng)
        r = check_source(obligation_source(data, spec, na, scale, forged))
        if r.accepted:
            report["failures"].append(f"forged outcome accepted for positive control {i}")
        else:
            report["negative_rejected"] += 1
    data, spec, na, scale, outcome = cases[0]
    altered = data.replace(b"10.5", b"10.6")
    r = check_source(obligation_source(altered, spec, na, scale, outcome))
    if r.accepted:
        report["failures"].append("altered data numeral accepted with the old outcome")
    else:
        report["negative_rejected"] += 1

    # shared-parse batch: all positive controls about FIXTURE in one pcs_batch, one theorem each
    items = [(c[1], c[2], c[3], c[4]) for c in cases]
    rb = check_source(batch_source(FIXTURE, items), claims=len(items))
    if not rb.accepted:
        report["failures"].append(f"shared-parse batch of positive controls rejected: {rb.detail}")
    report["batch_positive"] = len(items)
    bad = list(items)
    bad[7] = (bad[7][0], bad[7][1], bad[7][2], _forge(bad[7][3], rng))
    if check_source(batch_source(FIXTURE, bad), claims=len(bad)).accepted:
        report["failures"].append("a batch containing one forged outcome was accepted")
    else:
        report["negative_rejected"] += 1

    fuzz = []
    for _ in range(args.fuzz):
        data, spec, na, scale = _random_case(rng)
        o = evaluate(data, spec, na, scale)
        fuzz.append((data, spec, na, scale, o))
        key = o.verdict if o.defined else "undefined:" + o.reason
        report["fuzz_outcomes"][key] = report["fuzz_outcomes"].get(key, 0) + 1
    for start in range(0, len(fuzz), 100):
        chunk = fuzz[start:start + 100]
        text, n = _batch(chunk)
        r = check_source(text, claims=n, timeout=1800)
        if not r.accepted:
            # locate the disagreement precisely
            for j, case in enumerate(chunk):
                rr = check_source(obligation_source(*case))
                if not rr.accepted:
                    report["failures"].append({"fuzz_index": start + j, "detail": rr.detail, "data": case[0].decode("utf-8", "replace"),
                                               "spec": case[1].to_json(), "scale": str(case[3])})
    report["fuzz_cases"] = len(fuzz)
    report["seconds"] = round(time.monotonic() - t0, 1)
    report["seed"] = args.seed
    report["ok"] = not report["failures"]
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if args.report:
        open(args.report, "w", encoding="utf-8").write(text)
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
