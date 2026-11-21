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

  D. exhaustive mathematical status: all 84 variant patterns of the Lean table (one to three
     variants, each a match, a mismatch, an undefined statistic or not accepted by the kernel), each
     through the real `pipeline._complete` and `policy.math_status`, with every concrete way the
     pipeline holds a variant of that kind (rational or square-root value, which undefined reason,
     what was predicted for a variant the kernel did not accept, no Lean record or a refusal), the
     binding gate passed or failed, conventions named or not: 24,696 receipts;
  E. exhaustive verdict function: `outward m f corM corD` at every point of its finite domain
     (5 statuses × 2^16 findings × corM × corD = 1,310,720 points), printed by Lean at test time
     (`ExportOutward.lean`).  Every point that a Python input can reach (983,040; the other 327,680
     have a count whose dispersion wording fails, which no input produces: a count is not a
     dispersion statistic) is driven through `_numeric_evidence` (for a decided match, as
     `assess_document` does) and `_decide`, and must give Lean's verdict.  The facts the code computes
     from the receipt, the sentence and the predicted values (status, not-a-count, rounding,
     dispersion wording, out-of-grammar wording, printed sample size) are computed by the real code
     from a constructed input and checked to have the intended value; the rest come from stubs.

In B, C and E the helpers that examine text and data (`_basic_findings`, `_analyse`, `_alternatives`)
are replaced by stubs returning the wanted finding, and in E the sibling relation is an input: what
is compared is the decision logic, not how findings or siblings are computed.  Agreement on a finite
abstraction is evidence about the code, not a proof about Python.
Run (Lean 4.28.0 on PATH, after formal/build.sh):
python3 research/claimcheck_assurance_v1/conformance/check_conformance.py
"""
import hashlib, itertools, json, os, random, subprocess, sys, time
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from research.claimcheck_v1 import pipeline  # noqa: E402
from research.claimcheck_v1.oracle import Outcome  # noqa: E402
from research.claimcheck_v1.spec import ClaimSpec  # noqa: E402
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
        policy._decide = lambda ctx, receipt, it, cor, tau, *more: captured.append((receipt, it, REAL_DECIDE(ctx, receipt, it, cor, tau, *more))) or captured[-1][2]
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


REAL_GUARD = (policy.established_status, policy.binding_problem)


def input_condition():
    """Parts B, C and E check the decision logic on the Lean model's input condition: a receipt whose
    summary agrees with its kernel-checked variants and whose claim is the sentence's.  Their receipts
    are abstract (no concrete kernel records), so the guard is held at identity there; part D checks
    that the real guard is the identity on every receipt the real pipeline writes, and
    `outside_the_input_condition` checks, with the real guard, that every other receipt decides nothing."""
    policy.established_status = lambda receipt, **kw: (policy.math_status(receipt), None)
    policy.binding_problem = lambda receipt, manifest: None


def stubbed(basic_ok, analyse, alternatives):
    saved = {k: getattr(policy, k) for k in ("_basic_findings", "_analyse", "_alternatives", "_bound_to", "_rate_words", "_describe", "_same_quantity", "unit_factor",
                                             "established_status", "binding_problem")}
    input_condition()
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
    ctx = SimpleNamespace(source=window.ljust(40), data_unit=lambda spec: None, manifest={})
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
        ctx = SimpleNamespace(source="the mean was 10 in all".ljust(40), data_unit=lambda spec: None, manifest={})
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


# ---- D. the mathematical status, every variant pattern, through the real pipeline ----------------
# What the untrusted oracle predicted, i.e. the outcome the kernel was asked to confirm.
PREDICTED = {
    "consistent": [Outcome(True, "consistent", "rat", Fraction(10), None, 5, 0), Outcome(True, "consistent", "sqrt", Fraction(100), 1, 5, 0)],
    "inconsistent": [Outcome(True, "inconsistent", "rat", Fraction(50), None, 5, 0), Outcome(True, "inconsistent", "sqrt", Fraction(2500), -1, 5, 0)],
    "undefined": [Outcome(False, reason="emptySelection"), Outcome(False, reason="degenerate")],
}
ACCEPTED = {"kernel_accepted": True, "toolchain": "Lean (version 4.28.0)"}
NOT_ACCEPTED = [None, {"kernel_accepted": False, "detail": "the kernel did not accept the theorem"}]


def held_as(kind):
    """Every way the pipeline holds a variant of one abstract kind: (predicted outcome, Lean record)."""
    if kind == "none":  # the kernel accepted nothing, whatever was predicted; no record, or a refusal
        return [(o, lean) for os_ in PREDICTED.values() for o in os_ for lean in NOT_ACCEPTED]
    return [(o, ACCEPTED) for o in PREDICTED[{"match": "consistent", "mismatch": "inconsistent", "undefined": "undefined"}[kind]]]


def part_d():
    n, patterns, statuses = 0, set(), {}
    for length in (1, 2, 3):
        for pattern in itertools.product(("match", "mismatch", "undefined", "none"), repeat=length):
            want = MATH[pattern]
            for held in itertools.product(*(held_as(k) for k in pattern)):
                for bound_ok, named in itertools.product(B2, B2):
                    variants = [[ClaimSpec(("sd_sample", "sd_pop", "sd_sample")[j], "10", column="x"), f"convention {j}" if named else None, o, lean]
                                for j, (o, lean) in enumerate(held)]
                    receipt = {"claim": {"reading": "a reading"}, "data": {"name": "d.csv", "sha256": "0" * 64}}
                    r = pipeline._complete(pipeline._Pending(receipt, None, SimpleNamespace(ok=bound_ok, failures=["a gate failed"]), variants, [], Fraction(1)))
                    got = policy.math_status(r)
                    assert got == want, (pattern, [(o, lean) for o, lean in held], bound_ok, named, got, want)
                    assert REAL_GUARD[0](r) == (got, None), (pattern, REAL_GUARD[0](r))   # the guard accepts what v1 writes
                    assert kinds(r) == pattern  # the abstraction part A applies to committed receipts
                    # what part E assumes of a receipt: a decided result is the kernel's status, with the same polarity
                    if r["result"] in ("PROVED", "REFUTED"):
                        assert r["result"] == r["q1_mathematics"]["status"] and bound_ok
                    statuses[got] = statuses.get(got, 0) + 1
                    n += 1
            patterns.add(pattern)
    assert patterns == set(MATH)
    return {"variant_patterns": len(patterns), "receipts_through__complete": n, "by_status": dict(sorted(statuses.items()))}


# ---- E. the verdict function at every point of its finite domain ---------------------------------
FIELDS = ("hasWindow", "quoteOk", "grounded", "identOk", "basicOk", "boundedBound", "noCompeting", "lowRate", "pinnedOk",
          "notCount", "boundedAll", "noEligible", "beyondRounding", "dispersionNamed", "inGrammar", "sampleSizeOk")  # bits 0-15
MATHS = ("MATCH_PROVED", "MISMATCH_PROVED", "CONDITIONAL_ON_CONVENTION", "UNDEFINED_PROVED", "NOT_ESTABLISHED")
VERDICT = {"U": "UNKNOWN", "R": "REQUIRE_HUMAN_REVIEW", "C": "CONFIRMATION", "D": "DISCREPANCY_FOR_REVIEW"}


def lean_outward():
    build = HERE.parent / "formal" / ".build"
    assert (build / "ClaimCheckAssurance" / "Authority.olean").exists(), "run formal/build.sh first"
    started = time.monotonic()
    out = subprocess.run(["lean", "--run", str(HERE / "ExportOutward.lean")], env=dict(os.environ, LEAN_PATH=str(build)),
                         capture_output=True, text=True, check=True).stdout
    seconds = time.monotonic() - started
    table = dict(line.split(" ") for line in out.splitlines())
    assert tuple(table) == MATHS and all(len(v) == 1 << 18 and set(v) <= set(VERDICT) for v in table.values())
    return table, seconds, hashlib.sha256(out.encode()).hexdigest()


def rv(kind, value, verdict="inconsistent"):
    """A q1 variant entry as `_complete` writes it, with a defined predicted value (radicand for kind sqrt)."""
    po = {"defined": True, "verdict": verdict, "rows_used": 5, "rows_skipped_as_missing": 0,
          "value_kind": "rational" if kind == "rat" else "signed_square_root",
          "exact": {"numerator": str(value.numerator), "denominator": str(value.denominator)}}
    if kind == "sqrt":
        po["sign"] = 1
    return {"stat": "mean", "assumption": None, "predicted_outcome": po, "lean": ACCEPTED,
            "status": "PROVED" if verdict == "consistent" else "REFUTED"}


# printed "10": within one unit of the last digit (10.6, rational or √112.36) or not (50)
NEAR = [[rv("rat", Fraction(53, 5))], [rv("sqrt", Fraction(2809, 25))], [rv("rat", Fraction(50)), rv("sqrt", Fraction(2809, 25))]]
APART = [[rv("rat", Fraction(50))], [rv("sqrt", Fraction(2500))], [rv("rat", Fraction(50)), rv("sqrt", Fraction(2500))]]
DISPERSION = {"sd": ("sd_sample", "sd_pop", "sd"), "sem": ("sem",)}
NAMED = {"sd": ("standard deviation", "SD", "s.d."), "sem": ("standard error", "SEM", "s.e.m.")}
OTHER_STATS = ("mean", "median", "min", "max")
ODD = (", adjusted", ", geometric", ", log-transformed", " (IQR 4)", ", bootstrapped")
QUOTE_FAILS = ((False, False), (True, False), (False, True))
PIN_FAILS = [c for c in itertools.product(B2, B2, B2) if any(c)]  # (truncated, rate above the limit, a competitor)
ALT = SimpleNamespace(stat="median", column="y", x_column=None, filter=())
SIB_E = SimpleNamespace(literal="7", spec=ClaimSpec("mean", "7", column="x"), oracle_only=False, receipt={"receipt_sha256": "0" * 64}, scope_rows=(1,))
BOUND = lambda rd: True  # noqa: E731 -- what the stubbed `_bound_to` returns; the stubbed `_analyse` recognises it
CUR = SimpleNamespace()


def an(kind, truncated, rate_ok):
    reproduced = 0 if rate_ok else 100
    return SimpleNamespace(kind=kind, truncated=truncated, rate=Fraction(reproduced + 1, 101), eligible_readings=3, decoys=100,
                           decoys_reproduced=reproduced, examples=[], matching=[])


def e_stubs():
    saved = {k: getattr(policy, k) for k in ("_basic_findings", "_analyse", "_alternatives", "_bound_to", "established_status", "binding_problem")}
    input_condition()

    def analyse(ctx, it, restrict=None):
        if restrict is None:  # the mismatch rules: every eligible reading of the sentence
            return an("all", not CUR.boundedAll, True)
        if restrict is BOUND:  # the match rules: readings worded at this number
            return an("bound", not CUR.boundedBound, CUR.lowRate)
        return an("pin", CUR.pin[0], not CUR.pin[1])  # readings pinned by a confirmed sibling
    policy._basic_findings = lambda ctx, it: (CUR.basicOk, [{"rule": "eligible_reading", "passed": CUR.basicOk, "detail": "stub"}])
    policy._analyse = analyse
    policy._alternatives = lambda it, a, competing_only=False: [ALT] if {"bound": not CUR.noCompeting, "all": not CUR.noEligible, "pin": CUR.pin[2]}[a.kind] else []
    policy._bound_to = lambda ctx, it: BOUND
    return saved


def concretise(m, f, rng, used):
    """One Python input at the abstract point (m, f): receipt, item and context."""
    def pick(name, options):
        k = rng.randrange(len(options))
        used[name] = used.get(name, set()) | {k}
        return options[k]
    if not f["notCount"]:
        stat, phrase = "count", "the value"
    elif not f["dispersionNamed"]:
        stat, phrase = pick("dispersion_unnamed", [s for fam in DISPERSION.values() for s in fam]), "the value"
    else:
        fam = pick("named_or_not", ("none", "sd", "sem"))
        stat, phrase = ((pick("other_stat", OTHER_STATS), "the value") if fam == "none" else
                        (pick("dispersion_named_" + fam, DISPERSION[fam]), "the " + pick("naming_" + fam, NAMED[fam])))
    window = phrase + " was 10" + ("" if f["inGrammar"] else pick("odd", ODD)) + (
        pick("n_agrees", ("", " (n = 5)")) if f["sampleSizeOk"] else pick("n_differs", (" (n = 7)", " (N = 12)"))) + " in all"
    quote = (True, True) if f["quoteOk"] else pick("quote_fails", QUOTE_FAILS)
    q1 = {"status": {"MATCH_PROVED": "PROVED", "MISMATCH_PROVED": "REFUTED"}.get(m, "UNKNOWN"),
          "variants": pick("beyond", APART) if f["beyondRounding"] else pick("near", NEAR)}
    reason = {"CONDITIONAL_ON_CONVENTION": "ambiguous_convention", "UNDEFINED_PROVED": "statistic_undefined",
              "NOT_ESTABLISHED": "not_kernel_checked"}.get(m, "checked" if f["grounded"] else "binding_not_grounded")
    if m == "CONDITIONAL_ON_CONVENTION":
        q1["conditional"] = {"proved_if": "standard deviation uses denominator n − 1", "refuted_if": "standard deviation uses denominator n"}
    if m == "NOT_ESTABLISHED" and pick("no_q1_variants", B2):
        q1 = {"status": "UNKNOWN", "why": "No arithmetic was checked."}
    result = ("UNKNOWN" if not f["grounded"] else {"MATCH_PROVED": "PROVED", "MISMATCH_PROVED": "REFUTED"}.get(m)
              or pick("decided_without_status", ("PROVED", "REFUTED")))
    receipt = {"q1_mathematics": q1, "reason": reason, "result": result,
               "q2_correspondence": {"checks": {"quote_in_source": quote[0], "reported_value_in_quote": quote[1]},
                                     "failures": [] if f["quoteOk"] else ["The quote is not in the source."]}}
    spec = ClaimSpec(stat, "10", column="x")
    it = None
    if f["hasWindow"] or pick("no_window_as", ("no item", "no sentence")) == "no sentence":
        it = policy.Item(receipt, spec, result, policy.math_status(receipt))
        if f["hasWindow"]:
            it.w0, it.w1, it.token_start, it.token_end, it.literal = 0, len(window), window.index("10"), window.index("10") + 2, "10"
            it.quote, it.quote_start = window, 0
        it.ident, it.scope_rows = ((policy.family(stat), "x", None, (0, 1, 2, 3, 4)), (0, 1, 2, 3, 4)) if f["identOk"] else (None, None)
    ctx = SimpleNamespace(source=window, data_unit=lambda spec: None, manifest={})
    return receipt, it, ctx


# Which abstract fact each finding the code reports stands for, in the match and in the mismatch rules.
MATCH_RULES = {"eligible_reading": "basicOk", "bounded_reading_space": "boundedBound", "no_competing_reading_reproduces_the_number": "noCompeting",
               "low_chance_of_coincidence": "lowRate", "supported_by_another_number_in_the_sentence": "pinnedOk"}
MISMATCH_RULES = {"not_a_count": "notCount", "eligible_reading": "basicOk", "bounded_reading_space": "boundedAll",
                  "no_eligible_reading_reproduces_the_number": "noEligible", "beyond_rounding_convention": "beyondRounding",
                  "dispersion_statistic_named_explicitly": "dispersionNamed", "no_out_of_grammar_wording": "inGrammar",
                  "printed_sample_size_agrees": "sampleSizeOk", "supported_by_another_number_in_the_sentence": "corD"}


def outside_the_input_condition():
    """Asserted (since 2026-11-17): a receipt whose decided result contradicts the kernel's status decides nothing.

    The model takes the mathematical status as authoritative.  Until 2026-11-17 `_decide` chose the
    match or mismatch rules by `receipt["result"]`; such a receipt then gave DISCREPANCY_FOR_REVIEW or
    CONFIRMATION.  With the real guard (`policy.established_status`, `policy.binding_problem`) it must
    give UNKNOWN, with every finding passing and a sibling available.
    """
    seen = {}
    saved = e_stubs()
    try:
        for m, result in (("MATCH_PROVED", "REFUTED"), ("MISMATCH_PROVED", "PROVED")):
            f = dict.fromkeys(FIELDS, True)
            receipt, it, ctx = concretise(m, f, random.Random(0), {})
            receipt["result"] = it.v1_result = result
            CUR.basicOk = CUR.boundedBound = CUR.noCompeting = CUR.lowRate = CUR.boundedAll = CUR.noEligible = True
            CUR.pin = (False, False, False)
            if result == "PROVED":
                it.strong_match, it.findings = policy._numeric_evidence(ctx, it, policy.TAU)
            policy.established_status, policy.binding_problem = REAL_GUARD
            res = REAL_DECIDE(ctx, receipt, it, lambda item, same_column: [SIB_E], policy.TAU)
            input_condition()
            seen[f"status {m}, result {result}, all findings pass, siblings"] = res["verdict"]
            assert res["verdict"] == "UNKNOWN", (m, result, res["verdict"])
    finally:
        restore(saved)
    return seen


def part_e():
    table, lean_seconds, digest = lean_outward()
    rng, used = random.Random(20261116), {}
    started = time.monotonic()
    counts = {"points": 0, "unreachable_count_with_dispersion_wording_failed": 0, "checked": 0,
              "checked_with_a_receipt_v1_does_not_write": 0, "by_verdict": {}}
    findings_checked = {"match": 0, "mismatch": 0}
    saved = e_stubs()
    try:
        for m in MATHS:
            codes = table[m]
            for i in range(1 << 18):
                counts["points"] += 1
                f = {name: bool(i >> k & 1) for k, name in enumerate(FIELDS)}
                cor_m, cor_d = bool(i >> 16 & 1), bool(i >> 17 & 1)
                if not f["notCount"] and not f["dispersionNamed"]:
                    counts["unreachable_count_with_dispersion_wording_failed"] += 1
                    continue
                receipt, it, ctx = concretise(m, f, rng, used)
                CUR.basicOk, CUR.boundedBound, CUR.noCompeting, CUR.lowRate = f["basicOk"], f["boundedBound"], f["noCompeting"], f["lowRate"]
                CUR.boundedAll, CUR.noEligible = f["boundedAll"], f["noEligible"]
                if f["pinnedOk"]:
                    CUR.pin = (False, False, False)
                else:
                    k = rng.randrange(len(PIN_FAILS))
                    used["pin_fails"] = used.get("pin_fails", set()) | {k}
                    CUR.pin = PIN_FAILS[k]
                # as `assess_document` does: the match rules are evaluated for a decided match (it is in `decided`)
                decided = it is not None and it.w0 is not None and it.v1_result in ("PROVED", "REFUTED") and it.ident is not None
                if decided and it.v1_result == "PROVED":
                    it.strong_match, it.findings = policy._numeric_evidence(ctx, it, policy.TAU)
                    assert it.strong_match == (f["basicOk"] and f["boundedBound"] and f["noCompeting"] and f["lowRate"])  # Findings.matchGates
                res = REAL_DECIDE(ctx, receipt, it, lambda item, same_column: [SIB_E] if (cor_d if same_column else cor_m) else [], policy.TAU)
                want = VERDICT[codes[i]]
                assert res["mathematical_status"] == m, (m, i, res["mathematical_status"])
                assert res["verdict"] == want, (m, {k: v for k, v in f.items()}, cor_m, cor_d, receipt, res["verdict"], want)
                # every finding the code reports has the value of the abstract fact it stands for
                facts, rules = dict(f, corD=cor_d), MATCH_RULES if receipt["result"] == "PROVED" else MISMATCH_RULES
                for fd in res["findings"]:
                    assert fd["passed"] == facts[rules[fd["rule"]]], (m, fd["rule"], f, cor_m, cor_d)
                if res["findings"] and receipt["result"] == "REFUTED":  # the mismatch rules ran: all of them are reported
                    reported = {fd["rule"] for fd in res["findings"]}
                    dispersion = policy.family(it.spec.stat) in policy.EXPLICIT_DISPERSION or it.spec.stat == "sem"
                    assert reported == set(MISMATCH_RULES) - (set() if dispersion else {"dispersion_statistic_named_explicitly"}), reported
                    assert dispersion or f["dispersionNamed"]  # a statistic without the rule counts as named (the model's convention)
                    findings_checked["mismatch"] += 1
                elif res["findings"]:
                    findings_checked["match"] += 1
                if f["grounded"] and (m not in ("MATCH_PROVED", "MISMATCH_PROVED") or not f["quoteOk"]):
                    counts["checked_with_a_receipt_v1_does_not_write"] += 1
                counts["checked"] += 1
                counts["by_verdict"][res["verdict"]] = counts["by_verdict"].get(res["verdict"], 0) + 1
    finally:
        restore(saved)
    alternatives = {"dispersion_unnamed": 4, "named_or_not": 3, "other_stat": 4, "dispersion_named_sd": 3, "dispersion_named_sem": 1,
                    "naming_sd": 3, "naming_sem": 3, "odd": len(ODD), "n_agrees": 2, "n_differs": 2, "quote_fails": 3, "beyond": 3, "near": 3,
                    "no_q1_variants": 2, "decided_without_status": 2, "no_window_as": 2, "pin_fails": len(PIN_FAILS)}
    assert all(len(used.get(k, ())) == v for k, v in alternatives.items()), {k: sorted(used.get(k, ())) for k in alternatives}
    counts["by_verdict"] = dict(sorted(counts["by_verdict"].items()))
    counts.update({"lean_table_sha256": digest, "lean_seconds": round(lean_seconds, 1), "python_seconds": round(time.monotonic() - started, 1),
                   "concrete_alternatives_used": sum(alternatives.values()), "points_whose_reported_findings_were_checked": findings_checked,
                   "outside_the_input_condition_decides_nothing": outside_the_input_condition()})
    assert counts["points"] == 5 << 18 and counts["checked"] + counts["unreachable_count_with_dispersion_wording_failed"] == counts["points"]
    return counts


if __name__ == "__main__":
    report = {"lean_tables": {k: len(v) for k, v in T.items()}, "A_real_receipts": part_a(), "B_decision_table": part_b(), "C_gates": part_c(),
              "D_mathematical_status": part_d(), "E_verdict_function": part_e(), "passed": True}
    (HERE / "conformance_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
