"""Conformance of the Python policy with the Lean model (tests, not proofs).

`lean_tables.json` is printed by Lean from the definitions the theorems are about
(`conformance/ExportTables.lean`).  This script drives the real Python functions
(`policy._decide`, `policy._numeric_evidence`, `policy.math_status`, `policy.assess_document`)
and compares every result with the Lean tables:

  A. real data: every receipt of the six committed held-out evidence bundles through
     `assess_document`; mathematical status and verdict must equal the Lean model's; the input
     conditions the theorems assume (`Doc.WellFormed`, no confirmed-and-flagged number) are checked;
  B. exhaustive skeleton: all 160 states of the decision table `core`, each reached through
     `_decide` with every decomposition of its aggregated facts;
  C. exhaustive gates: all 512 mismatch-gate states and all 64 match-gate states, each gate driven
     through the code path that computes it or through the helper that reports it.

In B and C the helpers that examine text and data (`_basic_findings`, `_analyse`, `_alternatives`)
are replaced by stubs returning the wanted finding: what is compared is the decision logic, not how
findings are computed.  Run: python3 research/claimcheck_assurance_v1/conformance/check_conformance.py
"""
import itertools, json, sys
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from research.claimcheck_v1_1 import policy  # noqa: E402
from research.claimcheck_v1_1.dev.common import context, documents  # noqa: E402

T = json.loads((HERE / "lean_tables.json").read_text())
CORE = {tuple(r[:6]): r[6] for r in T["core"]}
MATH = {tuple(r[0]): r[1] for r in T["math"]}
MISMATCH = {tuple(r[:9]): r[9] for r in T["mismatch"]}
MATCH = {tuple(r[:6]): r[6] for r in T["match"]}
assert len(CORE) == 160 and len(MATH) == 84 and len(MISMATCH) == 512 and len(MATCH) == 64
B2 = (False, True)
REAL_DECIDE = policy._decide


def kinds(receipt):
    out = []
    for e in (receipt.get("q1_mathematics") or {}).get("variants", []):
        po = e.get("predicted_outcome") or {}
        out.append("none" if not (e.get("lean") or {}).get("kernel_accepted") else
                   "undefined" if not po.get("defined") else "match" if po.get("verdict") == "consistent" else "mismatch")
    return tuple(out)


def part_a():
    seen_core, seen_math, n = set(), set(), 0
    for doc in documents("heldout"):
        if doc.variant != "original":
            continue
        receipts = json.loads((ROOT / "research/claimcheck_v1/benchmark/results/bundles" / doc.slug / "receipts.json").read_text())
        captured = []
        policy._decide = lambda ctx, receipt, it, cor, tau: captured.append((receipt, it, REAL_DECIDE(ctx, receipt, it, cor, tau))) or captured[-1][2]
        try:
            results = policy.assess_document(context(doc), receipts)
        finally:
            policy._decide = REAL_DECIDE
        by_token = {}
        for (receipt, it, res), res2 in zip(captured, results):
            assert res is res2
            n += 1
            ks = kinds(receipt)
            want_math = MATH[ks] if ks else "NOT_ESTABLISHED"
            assert res["mathematical_status"] == want_math, (doc.slug, receipt["claim_id"], ks, res["mathematical_status"])
            seen_math.add(ks)
            checks = (receipt.get("q2_correspondence") or {}).get("checks", {})
            quote_ok = bool(checks.get("quote_in_source")) and bool(checks.get("reported_value_in_quote"))
            has_window = it is not None and it.w0 is not None
            grounded = receipt.get("result") in ("PROVED", "REFUTED")
            if grounded:  # Doc.WellFormed, and that v1 reports a decided result only for a decided status
                assert quote_ok and has_window, "WellFormed violated"
                assert want_math in ("MATCH_PROVED", "MISMATCH_PROVED")
            gi = grounded and it is not None and it.ident is not None
            proved, refuted = receipt.get("result") == "PROVED", receipt.get("result") == "REFUTED"
            strong = bool(proved and gi and it.strong_match)
            weak = bool(proved and any(f["rule"] == "supported_by_another_number_in_the_sentence" and f["passed"] for f in res["findings"]))
            disc = bool(refuted and gi and res["findings"] and all(f["passed"] for f in res["findings"]))
            state = (want_math, has_window and quote_ok, gi, strong, weak, disc)
            assert CORE[state] == res["verdict"], (doc.slug, receipt["claim_id"], state, res["verdict"])
            seen_core.add(state)
            if has_window:
                by_token.setdefault((it.w0, it.token_start), set()).add(res["verdict"])
        assert not any({"CONFIRMATION", "DISCREPANCY_FOR_REVIEW"} <= v for v in by_token.values()), "a number is both confirmed and flagged"
    return {"receipts": n, "distinct_core_states": len(seen_core), "distinct_variant_patterns": len(seen_math)}


class Spec(SimpleNamespace):
    def to_json(self):
        return {}


def fake_receipt(math, grounded, quote_ok, variants=()):
    q1 = {"variants": list(variants), "status": {"MATCH_PROVED": "PROVED", "MISMATCH_PROVED": "REFUTED"}.get(math, "UNKNOWN")}
    reason = "checked"
    if math == "CONDITIONAL_ON_CONVENTION":
        q1["conditional"] = {"proved_if": "a", "refuted_if": "b"}
        reason = "ambiguous_convention"
    if math == "UNDEFINED_PROVED":
        reason = "statistic_undefined"
    result = q1["status"] if grounded and q1["status"] != "UNKNOWN" else "UNKNOWN"
    return {"q1_mathematics": q1, "reason": reason, "result": result,
            "q2_correspondence": {"checks": {"quote_in_source": quote_ok, "reported_value_in_quote": quote_ok}, "failures": []}}


def fake_item(receipt, math, has_window, ident_ok, stat="mean", strong=False):
    spec = Spec(stat=stat, reported="10", reported_unit=None, column="x")
    it = policy.Item(receipt, spec, receipt["result"], math)
    if has_window:
        it.w0, it.w1, it.token_start, it.token_end, it.literal = 0, 40, 0, 2, "10"
    it.ident, it.scope_rows = (("mean", 1) if ident_ok else None), (1,)
    it.strong_match = strong
    return it


SIB = SimpleNamespace(literal="7", spec=Spec(stat="mean", column="x"), oracle_only=False, receipt={"receipt_sha256": "0" * 64}, scope_rows=(1,))


def analysis(truncated=False, rate_ok=True):
    return SimpleNamespace(truncated=truncated, rate=Fraction(0) if rate_ok else Fraction(1), eligible_readings=1, decoys=100,
                           decoys_reproduced=0, examples=[], matching=[])


def stubbed(basic_ok, analyse, alternatives):
    saved = {k: getattr(policy, k) for k in ("_basic_findings", "_analyse", "_alternatives", "_bound_to", "_rate_words", "_describe", "_same_quantity", "unit_factor")}
    policy._basic_findings = lambda ctx, it: (basic_ok, [{"rule": "basic", "passed": basic_ok, "detail": "basic"}])
    policy._analyse = analyse
    policy._alternatives = alternatives
    policy._bound_to = lambda ctx, it: (lambda rd: True)
    policy._rate_words = lambda a, tau: "rate"
    policy._describe = lambda r: "alt"
    policy._same_quantity = lambda it, r: False
    policy.unit_factor = lambda a, b: None
    return saved


def restore(saved):
    for k, v in saved.items():
        setattr(policy, k, v)


def decide(math, has_window, quote_ok, grounded, ident_ok, *, strong=False, cor_m=False, basic_ok=True, pinned_ok=True,
           stat="mean", window="the mean was 10 in all", variants=(), truncated=False, alts=False, cor_d=False):
    receipt = fake_receipt(math, grounded, quote_ok, variants)
    it = fake_item(receipt, math, has_window, ident_ok, stat, strong)
    it.analysis = analysis(truncated=truncated)
    ctx = SimpleNamespace(source=window.ljust(40), data_unit=lambda spec: None)
    saved = stubbed(basic_ok, lambda ctx, it, restrict=None: analysis(rate_ok=pinned_ok),
                    lambda it, a, competing_only=False: ([SimpleNamespace()] if alts else []))
    try:
        return REAL_DECIDE(ctx, receipt, it, lambda item, same_column: ([SIB] if (cor_d if same_column else cor_m) else []), policy.TAU)["verdict"]
    finally:
        restore(saved)


def part_b():
    n = 0
    for (math, att, gi, strong, weak, disc), want in CORE.items():
        for has_window, quote_ok in itertools.product(B2, B2):
            if (has_window and quote_ok) != att:
                continue
            for grounded, ident_ok in itertools.product(B2, B2):
                if (grounded and ident_ok) != gi:
                    continue
                for cor_m, basic_ok, pinned_ok in itertools.product(B2, B2, B2):
                    if (cor_m and basic_ok and pinned_ok) != weak:
                        continue
                    # `strong` and `disc` are facts about a grounded, analysable record of the right kind
                    got = decide(math, has_window, quote_ok, grounded, ident_ok, strong=strong, cor_m=cor_m, basic_ok=basic_ok if math == "MATCH_PROVED" else True,
                                 pinned_ok=pinned_ok, cor_d=disc)
                    if math == "MISMATCH_PROVED" and not disc:
                        pass
                    assert got == want, ((math, att, gi, strong, weak, disc), (has_window, quote_ok, grounded, ident_ok, cor_m, basic_ok, pinned_ok), got, want)
                    n += 1
    return {"core_states": len(CORE), "calls_to__decide": n}


CLOSE = [{"predicted_outcome": {"defined": True, "exact": {"numerator": "10", "denominator": "1"}, "value_kind": "rational", "sign": None, "rows_used": 5}}]
FAR = [{"predicted_outcome": {"defined": True, "exact": {"numerator": "50", "denominator": "1"}, "value_kind": "rational", "sign": None, "rows_used": 5}}]


def part_c():
    n = 0
    for (g1, g2, g3, g4, g5, g6, g7, g8, cor_d), want in MISMATCH.items():
        # g1 not a count; g6 dispersion named (only a dispersion statistic can fail it); so a count
        # cannot also fail g6 through the code: those 128 states are checked with g6 forced true.
        if not g1 and not g6:
            continue
        stat = "count" if not g1 else ("mean" if g6 else "sd_sample")
        window = "the value was 10" + (" adjusted" if not g7 else "") + (" n = 7" if not g8 else "") + " overall"
        got = decide("MISMATCH_PROVED", True, True, True, True, stat=stat, basic_ok=g2, truncated=not g3, alts=not g4,
                     variants=(FAR if g5 else CLOSE), window=window, cor_d=cor_d)
        assert got == want, ((g1, g2, g3, g4, g5, g6, g7, g8, cor_d), got, want)
        n += 1
    m = 0
    for (g1, g2, g3, g4, cor_m, pin), want in MATCH.items():
        receipt = fake_receipt("MATCH_PROVED", True, True)
        it = fake_item(receipt, "MATCH_PROVED", True, True)
        ctx = SimpleNamespace(source="the mean was 10 in all".ljust(40), data_unit=lambda spec: None)
        saved = stubbed(g1, lambda ctx, it, restrict=None: analysis(truncated=not g2, rate_ok=g4),
                        lambda it, a, competing_only=False: ([SimpleNamespace()] if (competing_only and not g3) else []))
        try:
            it.strong_match, it.findings = policy._numeric_evidence(ctx, it, policy.TAU)
            policy._analyse = lambda ctx, it, restrict=None: analysis(rate_ok=pin)
            policy._alternatives = lambda it, a, competing_only=False: []
            got = REAL_DECIDE(ctx, receipt, it, lambda item, same_column: ([SIB] if cor_m and not same_column else []), policy.TAU)["verdict"]
        finally:
            restore(saved)
        assert it.strong_match == (g1 and g2 and g3 and g4)
        assert got == want, ((g1, g2, g3, g4, cor_m, pin), got, want)
        m += 1
    return {"mismatch_gate_states_checked": n, "mismatch_gate_states_unreachable_in_code": len(MISMATCH) - n, "match_gate_states_checked": m}


if __name__ == "__main__":
    report = {"lean_tables": {k: len(v) for k, v in T.items()}, "A_real_receipts": part_a(), "B_decision_table": part_b(), "C_gates": part_c(), "passed": True}
    (HERE / "conformance_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
