"""Semantic policy v1.1: when may a kernel-decided arithmetic result be said about a PAPER?

Three statements are kept apart in every v1.1 record.

  mathematical     what the Lean kernel established about one typed statement and the exact bytes
                   of one file.  Unchanged from v1.  It is preserved whatever the policy decides.
  source reading   whether there is enough support to say the sentence in the paper makes that
                   statement.  Decided here, by fixed rules that can only withhold.
  scientific       never assessed.

Outward verdicts (about the printed number, never about the paper's correctness):

  CONFIRMATION             the number is reproduced; the wording admits no other reading that
                           reproduces it; the admitted readings reproduce few comparable numbers (a
                           local density of at most 2 %; this limits coincidence but does not exclude
                           it: against a chooser who saw the data, the bound proved in a model of the
                           rule for an unrelated number is about 4 %, 2 per 51 comparable numbers;
                           see claimcheck_assurance_v1 Selection.lean)
  DISCREPANCY_FOR_REVIEW   the number is not reproduced under a reading that another number in the
                           same sentence independently supports; for a person to look at
  REQUIRE_HUMAN_REVIEW     a mathematical result exists, but support for the reading is insufficient
  UNKNOWN                  no mathematical result, or nothing to attach it to

Invariant (asserted in code and tests): CONFIRMATION only if v1 said PROVED; DISCREPANCY_FOR_REVIEW
only if v1 said REFUTED.  v1.1 never upgrades a v1 result.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction

from ..claimcheck_v1.grounding import ground
from ..claimcheck_v1.spec import ClaimSpec, SpecError, reported_half_unit, unit_factor
from . import POLICY_ID
from .binding import bound, canonical_literal, foreign_unit, part_of_a_date
from .space import DECOYS_PER_SIDE, MAX_CONDITIONS, Reading, SourceContext, family, printed_numbers, structurally_eligible, within

# Maximum decoy coincidence rate for a match to count as evidence for its reading: at most this
# share of nearby numbers of the same printed precision may be reproducible by SOME eligible reading.
# This is a local density around the printed number, not a probability of a false confirmation.
# In a model of this rule (research/claimcheck_assurance_v1/formal, Selection.lean) at most 2 in any 51
# consecutive comparable numbers can be confirmed, by the direct route and one supporting sibling
# together, and max(1, s) * 2 with s supporting reading sets; for an unrelated, uniformly placed number
# and a chooser who saw the data that is about 4 %.  Nothing bounds errors for related numbers.
TAU = Fraction(2, 100)
# With the printed number counted among the comparable numbers, a number needs at least 50 of
# them (49 decoys) before its rate can be at or below 2 %.  A one-digit number has nine.
MIN_DECOYS = 49

# Wording that marks a descriptive number as something outside the supported grammar.  A mismatch in
# such a sentence may only mean that the paper reports a statistic ClaimCheck does not compute.
OUT_OF_GRAMMAR = re.compile(
    r"\b(?:CI|CIs|confidence (?:interval|limit)s?|credible|IQR|interquartile|quartiles?|percentiles?|quantiles?|"
    r"geometric|harmonic|weighted|adjusted|corrected|standardi[sz]ed|normali[sz]ed|residuals?|"
    r"(?:log|ln|square[- ]root|arcsine|logit|box[- ]cox)[- ]?transform\w*|transformed|back[- ]transformed|"
    r"least[- ]squares? means?|LS[- ]?means?|marginal means?|estimated|model[- ](?:estimated|predicted|averaged)|predicted|fitted|"
    r"posterior|bootstrap\w*|trimmed|winsori[sz]ed|pooled|mode|modal)\b", re.IGNORECASE)
EXPLICIT_DISPERSION = {
    "sd": re.compile(r"\bSDs?\b|\bs\.d\.|\bstandard deviations?\b"),
    "sem": re.compile(r"\bSEM?s?\b|\bs\.e\.(?:m\.)?|\bstandard errors?\b"),
}
SAMPLE_SIZE = re.compile(r"\b[nN]\s*=\s*([0-9][0-9,]*)(?![0-9.])")

OUTWARD = ("CONFIRMATION", "DISCREPANCY_FOR_REVIEW", "REQUIRE_HUMAN_REVIEW", "UNKNOWN")


def policy_parameters() -> dict:
    return {"id": POLICY_ID, "max_decoy_coincidence_rate": str(TAU), "decoys": 2 * DECOYS_PER_SIDE, "min_decoys": MIN_DECOYS,
            "max_row_conditions": MAX_CONDITIONS,
            "note": "Fixed before the prospective evaluation. The rules can only withhold an outward verdict."}


@dataclass
class Item:
    """One v1 receipt (or, in development evaluation only, one oracle-predicted sibling)."""
    receipt: dict | None
    spec: ClaimSpec
    v1_result: str                 # PROVED / REFUTED / UNKNOWN (kernel + v1 gates)
    math: str                      # MATCH_PROVED / MISMATCH_PROVED / CONDITIONAL_ON_CONVENTION / UNDEFINED_PROVED / NOT_ESTABLISHED
    w0: int | None = None
    w1: int | None = None
    token_start: int | None = None
    token_end: int | None = None
    literal: str | None = None
    detected_unit: str | None = None
    quote: str | None = None
    quote_start: int | None = None
    ident: tuple | None = None
    scope_rows: tuple | None = None
    findings: list = field(default_factory=list)
    analysis: object = None
    strong_match: bool = False
    oracle_only: bool = False


def math_status(receipt: dict) -> str:
    q1 = receipt.get("q1_mathematics") or {}
    if q1.get("status") == "PROVED":
        return "MATCH_PROVED"
    if q1.get("status") == "REFUTED":
        return "MISMATCH_PROVED"
    if q1.get("conditional"):
        return "CONDITIONAL_ON_CONVENTION"
    if receipt.get("reason") == "statistic_undefined":
        return "UNDEFINED_PROVED"
    return "NOT_ESTABLISHED"


_DECIDED = {"MATCH_PROVED": "PROVED", "MISMATCH_PROVED": "REFUTED"}


def established_status(receipt: dict, *, oracle_receipts: bool = False) -> tuple[str, str | None]:
    """The mathematical status the receipt's kernel-checked variants establish, and whether its summary agrees.

    Returns (status, None) when every summary field of the receipt (`result`, `q1.status`,
    `q1.conditional`, `reason`) follows from its variants, and ("NOT_ESTABLISHED", why) otherwise.
    Each variant's status is recomputed as claimcheck_v1/pipeline.py::_complete computes it: decided only
    if the Lean kernel accepted the obligation, which states the variant's predicted outcome, and that
    outcome is defined; PROVED if the outcome is consistent, REFUTED if not.  The aggregate is recomputed
    with the same rule as `_complete`.  A summary is never trusted on its own: a receipt whose `result`
    or status was edited, or whose variants were dropped or downgraded, decides nothing.

    `oracle_receipts=True` is for development analysis only (like `oracle_siblings`): a receipt that
    `dev.common.oracle_receipts_raw` marked `oracle_predicted_only`, whose arithmetic is the untrusted
    oracle's prediction, is then taken at its summary.  The verification pipeline never sets it, so
    there an oracle-marked receipt is not kernel-established and decides nothing.
    """
    if oracle_receipts and receipt.get("oracle_predicted_only") is True:
        return math_status(receipt), None
    q1 = receipt.get("q1_mathematics")
    if not isinstance(q1, dict):
        q1 = {}
    variants = q1.get("variants")
    claimed = math_status(receipt)
    statuses = []
    for v in variants if isinstance(variants, list) else []:
        if not isinstance(v, dict) or not isinstance(v.get("predicted_outcome"), dict) or not isinstance(v.get("lean"), dict):
            return "NOT_ESTABLISHED", "a variant is malformed"
        po = v["predicted_outcome"]
        accepted = v["lean"].get("kernel_accepted") is True
        if accepted and po.get("defined") is True and po.get("verdict") in ("consistent", "inconsistent"):
            want = "PROVED" if po["verdict"] == "consistent" else "REFUTED"
        else:
            want = "UNKNOWN"
        if v.get("status") != want:
            return "NOT_ESTABLISHED", "a variant's status does not follow from its kernel result"
        statuses.append(want)
    conditional = False
    if not statuses:
        agg = "UNKNOWN"
    elif len(statuses) == 1:
        agg = statuses[0]
    elif all(x == "PROVED" for x in statuses):
        agg = "PROVED"
    elif all(x == "REFUTED" for x in statuses):
        agg = "REFUTED"
    elif "UNKNOWN" in statuses:
        agg = "UNKNOWN"
    else:
        agg, conditional = "UNKNOWN", True
    if (q1.get("status") or "UNKNOWN") != agg or bool(q1.get("conditional")) != conditional:
        return "NOT_ESTABLISHED", "the mathematical summary does not follow from the variants"
    if agg == "PROVED":
        status = "MATCH_PROVED"
    elif agg == "REFUTED":
        status = "MISMATCH_PROVED"
    elif conditional:
        status = "CONDITIONAL_ON_CONVENTION"
    elif receipt.get("reason") == "statistic_undefined":
        defined = variants[0]["predicted_outcome"].get("defined") if statuses else True
        if defined is not False or not all(v["lean"].get("kernel_accepted") is True for v in variants):
            return "NOT_ESTABLISHED", "an undefined statistic is claimed without a kernel-accepted undefined outcome"
        status = "UNDEFINED_PROVED"
    else:
        status = "NOT_ESTABLISHED"
    if status != claimed:
        return "NOT_ESTABLISHED", "the mathematical summary does not follow from the variants"
    reason = receipt.get("reason")
    # the reasons _complete writes: a decided status ends with "checked" or "binding_not_grounded"
    if (status in _DECIDED and reason not in ("checked", "binding_not_grounded")) or \
       (reason == "statistic_undefined" and status != "UNDEFINED_PROVED") or \
       (reason == "ambiguous_convention" and status != "CONDITIONAL_ON_CONVENTION"):
        return "NOT_ESTABLISHED", f"the receipt's reason {reason!r} contradicts the kernel-established status {status}"
    result = receipt.get("result")
    if result in ("PROVED", "REFUTED") and _DECIDED.get(status) != result:
        return "NOT_ESTABLISHED", f"the receipt's result {result} contradicts the kernel-established status {status}"
    return status, None


_SD_CONVENTIONS = {"n-1": "sd_sample", "n": "sd_pop"}


def binding_problem(receipt: dict, manifest: dict | None) -> str | None:
    """Why the receipt's claim is not the sentence's, or None.  The same two checks as the v1.1 replayer:
    the claim's reported value must be the printed literal whenever the quote check found it, and the
    checked variants must be exactly those the claim's statistic requires (claimcheck_v1/pipeline.py::
    expand_spec: both standard-deviation conventions unless the manifest declares one)."""
    spec = (receipt.get("claim") or {}).get("spec") or {}
    q2 = receipt.get("q2_correspondence") or {}
    if (q2.get("checks") or {}).get("reported_value_in_quote") and spec.get("reported") != (q2.get("reported_value") or {}).get("literal_checked"):
        return "the claim's reported value is not the number printed in the sentence"
    variants = (receipt.get("q1_mathematics") or {}).get("variants") or []
    if variants:
        stat = spec.get("stat")
        if stat in ("sd", "sd_sample", "sd_pop"):
            declared = (manifest or {}).get("sd_convention")
            want = [_SD_CONVENTIONS[declared]] if declared in _SD_CONVENTIONS else ["sd_sample", "sd_pop"]
        else:
            want = [stat]
        if [v.get("stat") if isinstance(v, dict) else None for v in variants] != want:
            return "the checked variants are not the ones the claim's statistic requires"
    return None


def identity(ctx: SourceContext, spec: ClaimSpec) -> tuple[tuple | None, tuple | None]:
    """(what is computed, rows that enter it) for a reading; mirrors ``space.readings_for_window``."""
    t = ctx.table
    if not t.ok:
        return None, None
    rows = t.select(spec.filter)
    if rows is None:
        return None, None
    if spec.stat == "count":
        counted = t.used(rows, spec.column) if spec.column in t.names else rows
        return ("count", counted), counted
    if spec.stat == "share":
        hit = t.select(spec.filter + spec.sub_filter)
        return ("share", rows, hit), rows
    if spec.column not in t.names or (spec.x_column is not None and spec.x_column not in t.names):
        return None, None
    used = t.used(rows, spec.column, spec.x_column)
    if spec.stat == "pearson":
        a, b = sorted((spec.column, spec.x_column))
        return ("pearson", a, b, used), used
    return (family(spec.stat), spec.column, spec.x_column, used), used


def _scope(reading: Reading) -> tuple:
    return reading.ident[1] if reading.stat in ("count", "share") else reading.ident[3]


def _item(ctx: SourceContext, receipt: dict, oracle_receipts: bool = False) -> Item | None:
    try:
        spec = ClaimSpec.from_json((receipt.get("claim") or {}).get("spec"), allow_unspecified_sd=True)
    except SpecError:
        return None
    q2 = receipt.get("q2_correspondence") or {}
    status, inconsistent = established_status(receipt, oracle_receipts=oracle_receipts)
    inconsistent = inconsistent or binding_problem(receipt, ctx.manifest)
    # an inconsistent receipt is never decided and never corroborates anything
    it = Item(receipt, spec, "INCONSISTENT" if inconsistent else receipt.get("result", "UNKNOWN"), status)
    if q2.get("reported_value") and q2.get("sentence") and q2.get("quote"):
        it.w0, it.w1 = q2["sentence"]["start"], q2["sentence"]["end"]
        it.token_start = q2["reported_value"]["start"]
        it.token_end = q2["reported_value"]["end"]
        it.literal = q2["reported_value"]["literal_checked"]
        it.detected_unit = q2["reported_value"].get("unit_printed_after")
        it.quote, it.quote_start = q2["quote"]["text"], q2["quote"]["start"]
        it.ident, it.scope_rows = identity(ctx, spec)
    return it


def _describe(reading: Reading) -> str:
    cond = " and ".join(f"{c.column} {'=' if c.kind == 'text_eq' else '≠' if c.kind == 'text_ne' else c.cmp} {c.value}" for c in reading.filter)
    target = reading.column or "rows"
    if reading.x_column:
        target += f" vs {reading.x_column}"
    return f"{reading.stat} of {target}" + (f" where {cond}" if cond else "")


def _analyse(ctx: SourceContext, it: Item, restrict=None):
    return ctx.analyse(w0=it.w0, w1=it.w1, reported=it.literal, detected_unit=it.detected_unit, quote=it.quote,
                       quote_start=it.quote_start, restrict=restrict)


def _same_quantity(it: Item, rd: Reading) -> bool:
    """Same statistic family and the same column(s) as the proposed reading (the rows may differ)."""
    spec = it.spec
    if family(rd.stat) != family(spec.stat):
        return False
    if spec.stat in ("count", "share"):
        return True
    if spec.stat == "pearson":
        return {rd.column, rd.x_column} == {spec.column, spec.x_column}
    return (rd.column, rd.x_column) == (spec.column, spec.x_column)


def _bound_to(ctx: SourceContext, it: Item):
    """Predicate: is a reading's statistic worded at this item's number?"""
    window = ctx.source[it.w0:it.w1]
    start, end = it.token_start - it.w0, (it.token_end or it.token_start) - it.w0
    cache: dict = {}

    def check(rd: Reading) -> bool:
        if rd.stat not in cache:
            cache[rd.stat] = bound(rd.stat, window, start, end, ctx.manifest) is not None
        return cache[rd.stat]
    return check


def _alternatives(it: Item, analysis, *, competing_only: bool = False) -> list[Reading]:
    """Other eligible readings that reproduce the printed number.

    ``competing_only`` keeps those that are a different quantity (another statistic or column).
    Readings of the same statistic and column over a different row selection are *equivalent
    selections*: whichever the sentence means, the number is reproduced.
    """
    seen, out = set(), []
    for rd, _ru in analysis.matching:
        if rd.ident != it.ident and rd.ident not in seen and not (competing_only and _same_quantity(it, rd)):
            seen.add(rd.ident)
            out.append(rd)
    return out


def _numeric_evidence(ctx: SourceContext, it: Item, tau: Fraction) -> tuple[bool, list]:
    """Full-space test for a match: eligible, bounded space, unique, low decoy coincidence rate."""
    findings = []
    window = ctx.source[it.w0:it.w1]
    base_ok, base = _basic_findings(ctx, it)
    findings.extend(base)
    problems = [] if base_ok else ["x"]
    # Only readings whose wording is attached to THIS number can be confirmed for it, so only they
    # count as competitors and as ways to reproduce a decoy.
    a = it.analysis = it.analysis or _analyse(ctx, it, restrict=_bound_to(ctx, it))
    findings.append({"rule": "bounded_reading_space", "passed": not a.truncated,
                     "detail": f"{a.eligible_readings} readings that this sentence's wording attaches to the number were examined"
                               + (" (the space was too large to examine completely)." if a.truncated else ".")})
    alts = _alternatives(it, a, competing_only=True)
    same = [r for r in _alternatives(it, a) if _same_quantity(it, r)]
    findings.append({"rule": "no_competing_reading_reproduces_the_number", "passed": not alts,
                     "detail": ("A different statistic or column named in the sentence also reproduces it: " + "; ".join(_describe(r) for r in alts[:4]) + ".") if alts
                     else ("No other statistic or column named in the sentence reproduces the printed number."
                           + (f" The same statistic over {len(same)} other row selection(s) the sentence names gives the same value." if same else "")),
                     "competing_readings": [_describe(r) for r in alts[:8]],
                     "equivalent_row_selections": [{"reading": _describe(r), "spec": r.spec(it.literal, it.spec.reported_unit).to_json()} for r in same[:8]]})
    ok_rate = a.rate <= tau
    findings.append({"rule": "low_chance_of_coincidence", "passed": ok_rate,
                     "detail": _rate_words(a, tau),
                     "decoys": a.decoys, "decoys_reproduced": a.decoys_reproduced,
                     "examples": [{"offset_in_last_digit_units": k, "reading": _describe(r)} for k, r in a.examples]})
    return (not problems and not a.truncated and not alts and ok_rate), findings


def _basic_findings(ctx: SourceContext, it: Item) -> tuple[bool, list]:
    """Gates every outward verdict needs: a plain number, an eligible reading, wording attached to the number."""
    window = ctx.source[it.w0:it.w1]
    date = part_of_a_date(window, it.token_start - it.w0, (it.token_end or it.token_start) - it.w0)
    plain = canonical_literal(it.literal) and not date
    problems = structurally_eligible(it.spec, ctx.table, ctx.manifest, window)
    how = bound(it.spec.stat, window, it.token_start - it.w0, (it.token_end or it.token_start) - it.w0, ctx.manifest)
    alien = foreign_unit(it.spec.stat, window, (it.token_end or it.token_start) - it.w0, ctx.data_unit(it.spec))
    findings = [
        {"rule": "unit_fits_the_quantity", "passed": alien is None,
         "detail": (alien[0].upper() + alien[1:] + ".") if alien else "No unit printed after the number conflicts with this reading."},
        {"rule": "plain_number", "passed": plain,
         "detail": "The printed token is a plain number." if plain else
                   ("The printed token is part of a calendar date, not a quantity." if date else
                    "The printed token looks like part of an identifier (leading zeros), not a quantity.")},
        {"rule": "eligible_reading", "passed": not problems,
         "detail": " ".join(problems) or f"At most {MAX_CONDITIONS} row conditions, each a group label named in the sentence."},
        {"rule": "number_worded_as_this_statistic", "passed": how is not None,
         "detail": (f"The wording attached to the number fits this statistic (“{how}”)." if how else
                    "Nothing attached to this number says it is this statistic (the statistic's wording occurs elsewhere in the sentence, or not at all)."),
         "wording": how},
    ]
    return plain and not problems and how is not None and alien is None, findings


def _rate_words(a, tau: Fraction) -> str:
    total = a.decoys + 1
    if Fraction(1, total) > tau:
        return (f"The printed number has too few digits to carry evidence: only {total} comparable numbers exist (same decimals, same number "
                f"of digits), so a chance match cannot be made unlikely (limit {float(tau):.0%}).")
    return (f"{a.decoys_reproduced + 1} of {total} comparable numbers (same decimals, same number of digits; the printed one included) are "
            f"reproduced by some reading the sentence's wording attaches to this number (limit {float(tau):.0%}).")


def sibling_proposals(ctx: SourceContext, receipt: dict) -> list[dict]:
    """Untrusted, data-aware candidates: other numbers in the same sentence that the SAME column and rows reproduce.

    They are proposals like any other: each must pass the v1 gates and the kernel before the policy
    counts it as corroboration.
    """
    it = _item(ctx, receipt)
    if it is None or it.w0 is None or it.ident is None or it.spec.stat in ("count", "share") or it.spec.column is None:
        return []
    window = ctx.source[it.w0:it.w1]
    out, seen = [], set()
    for start, _end, literal in printed_numbers(window):
        if it.w0 + start == it.token_start or literal in seen:
            continue
        seen.add(literal)
        try:
            probe = ClaimSpec("count", literal)
            g = ground(ctx.source, window, probe, ctx.manifest, quote_start=it.w0)
        except Exception:
            continue
        if g.token_start is None or g.token_start == it.token_start:
            continue
        analysis = ctx.analyse(w0=it.w0, w1=it.w1, reported=literal, detected_unit=g.detected_unit, quote=window, quote_start=it.w0,
                               restrict=lambda rd: rd.column == it.spec.column and rd.stat not in ("count", "share") and _scope(rd) == it.scope_rows)
        for rd, ru in analysis.matching[:3]:
            out.append({"quote": window, "quote_start": it.w0, "spec": rd.spec(literal, ru).to_json()})
    return out


def assess_document(ctx: SourceContext, receipts: list[dict], *, tau: Fraction = TAU, oracle_siblings: bool = False,
                    oracle_receipts: bool = False) -> list[dict]:
    """Outward verdict and findings for every v1 receipt about one source and one data file.

    ``oracle_siblings=True`` (development evaluation only) lets oracle-predicted sibling matches
    corroborate without a kernel run.  ``oracle_receipts=True`` (development analysis and offline tests
    only) accepts receipts marked ``oracle_predicted_only`` at their summary.  The verification pipeline
    sets neither: there, every decided verdict needs a status established by kernel-accepted variants
    (``established_status``), and corroborating siblings are kernel-checked receipts in ``receipts``.
    """
    items = [_item(ctx, r, oracle_receipts) for r in receipts]
    decided = [it for it in items if it is not None and it.w0 is not None and it.ident is not None
               and _DECIDED.get(it.math) == it.v1_result]
    for it in decided:
        if it.v1_result == "PROVED":
            it.strong_match, it.findings = _numeric_evidence(ctx, it, tau)
    siblings_extra: list[Item] = []
    if oracle_siblings:
        for it in decided:
            if it.v1_result == "PROVED" and it.strong_match:
                continue
            for prop in sibling_proposals(ctx, it.receipt):
                spec = ClaimSpec.from_json(prop["spec"])
                g = ground(ctx.source, prop["quote"], spec, ctx.manifest, quote_start=prop["quote_start"])
                sib = Item(None, spec, "PROVED", "MATCH_PROVED", it.w0, it.w1, g.token_start, g.token_end, spec.reported, g.detected_unit,
                           prop["quote"], prop["quote_start"], oracle_only=True)
                sib.ident, sib.scope_rows = identity(ctx, spec)
                if g.ok and sib.ident is not None:
                    sib.strong_match, sib.findings = _numeric_evidence(ctx, sib, tau)
                    siblings_extra.append(sib)
    strong = [s for s in decided + siblings_extra if s.v1_result == "PROVED" and s.math == "MATCH_PROVED" and s.strong_match]

    def corroborators(it: Item, same_column: bool) -> list[Item]:
        out = []
        for s in strong:
            if s is it or (s.w0, s.w1) != (it.w0, it.w1) or s.token_start == it.token_start or s.scope_rows != it.scope_rows:
                continue
            if s.spec.stat in ("count", "share"):
                if same_column:
                    continue
            elif it.spec.stat not in ("count", "share") and s.spec.column != it.spec.column:
                continue
            out.append(s)
        return out

    results = []
    for receipt, it in zip(receipts, items):
        results.append(_decide(ctx, receipt, it, corroborators, tau, oracle_receipts))
    return results


def _decide(ctx: SourceContext, receipt: dict, it: Item | None, corroborators, tau: Fraction, oracle_receipts: bool = False) -> dict:
    math, inconsistent = established_status(receipt, oracle_receipts=oracle_receipts)
    inconsistent = inconsistent or binding_problem(receipt, ctx.manifest)
    if inconsistent:
        math = "NOT_ESTABLISHED"
    q2 = receipt.get("q2_correspondence") or {}
    findings: list = []
    reasons: list[str] = []

    def out(verdict: str, corroboration=()):
        if verdict not in OUTWARD:
            raise ValueError("unknown outward verdict")
        # fail closed (not an assert, which `python -O` removes): a decided verdict needs the matching
        # kernel-established status AND the matching v1 result
        if (verdict == "CONFIRMATION" and not (math == "MATCH_PROVED" and receipt.get("result") == "PROVED")) or \
           (verdict == "DISCREPANCY_FOR_REVIEW" and not (math == "MISMATCH_PROVED" and receipt.get("result") == "REFUTED")):
            reasons.append("A decided verdict was not supported by the kernel-established status; it is withheld.")
            verdict, corroboration = "UNKNOWN", ()
        return {"verdict": verdict, "mathematical_status": math, "reasons": reasons, "findings": findings,
                "corroborated_by": [{"printed": s.literal, "reading": s.spec.to_json(), "kernel_checked": not s.oracle_only,
                                     "receipt_sha256": (s.receipt or {}).get("receipt_sha256")} for s in corroboration],
                "policy": policy_parameters() | {"max_decoy_coincidence_rate": str(tau)}}

    if inconsistent:
        reasons.append("The receipt is not consistent with its own kernel-checked variants or with the sentence ("
                       + inconsistent + "), so nothing is decided from it.")
        return out("UNKNOWN")
    if math in ("NOT_ESTABLISHED", "UNDEFINED_PROVED"):
        reasons.append({"NOT_ESTABLISHED": "No mathematical result was established by the Lean kernel.",
                        "UNDEFINED_PROVED": "The statistic is undefined for this file (kernel-confirmed)."}[math])
        return out("UNKNOWN")
    if it is None or it.w0 is None or not q2.get("checks", {}).get("quote_in_source") or not q2.get("checks", {}).get("reported_value_in_quote"):
        reasons.append("The quoted sentence or the number is not in the source, so there is nothing to attach the result to.")
        return out("UNKNOWN")
    if math == "CONDITIONAL_ON_CONVENTION":
        reasons.append("The number matches under one standard-deviation convention and not the other; the source does not say which was used.")
        return out("REQUIRE_HUMAN_REVIEW")
    if receipt.get("result") not in ("PROVED", "REFUTED"):
        reasons.append("The arithmetic was decided, but the sentence does not pass the lexical checks for this reading: "
                       + " ".join(q2.get("failures") or []))
        return out("REQUIRE_HUMAN_REVIEW")
    if it.ident is None:
        reasons.append("The reading's rows could not be analysed.")
        return out("REQUIRE_HUMAN_REVIEW")
    window = ctx.source[it.w0:it.w1]

    if math == "MATCH_PROVED":                # the kernel-established status decides the branch, not `result`
        findings.extend(it.findings)
        if it.strong_match:
            return out("CONFIRMATION")
        # a weak match can still be supported by a strong sibling that pins the column and the rows
        cor = corroborators(it, same_column=False)
        if cor and _basic_findings(ctx, it)[0]:
            is_bound = _bound_to(ctx, it)
            pinned = _analyse(ctx, it, restrict=lambda rd: is_bound(rd) and any(
                _scope(rd) == s.scope_rows and (rd.column == s.spec.column or rd.stat == "count" or s.spec.stat in ("count", "share")) for s in cor))
            alts = _alternatives(it, pinned, competing_only=True)
            ok = not alts and pinned.rate <= tau and not pinned.truncated
            findings.append({"rule": "supported_by_another_number_in_the_sentence", "passed": ok,
                             "detail": f"Another number in this sentence ({', '.join(sorted({s.literal for s in cor}))}) is confirmed from the same rows"
                                       f"{'' if it.spec.stat in ('count', 'share') else ' and column'}. Among the readings that fixes: "
                                       + _rate_words(pinned, tau)
                                       + ("" if not alts else " Another statistic also reproduces this number."),
                             "decoys": pinned.decoys, "decoys_reproduced": pinned.decoys_reproduced})
            if ok:
                return out("CONFIRMATION", cor)
        reasons.append("The number is reproduced, but that alone does not show the sentence means this reading: "
                       + " ".join(f["detail"] for f in findings if not f["passed"]))
        return out("REQUIRE_HUMAN_REVIEW")

    # ---- a proved mismatch -------------------------------------------------------------------------
    blocked = False

    def rule(name: str, passed: bool, detail: str, **extra):
        nonlocal blocked
        findings.append({"rule": name, "passed": passed, "detail": detail, **extra})
        if not passed:
            blocked = True
            reasons.append(detail)

    spec = it.spec
    rule("not_a_count", spec.stat != "count",
         "What a count counts (rows, individuals, sequences, sites) is not fixed by the sentence's wording, so a count that differs is never flagged automatically."
         if spec.stat == "count" else "The statistic is not a count.")
    for f in _basic_findings(ctx, it)[1]:
        rule(f["rule"], f["passed"], f["detail"])
    a = it.analysis = it.analysis or _analyse(ctx, it)
    rule("bounded_reading_space", not a.truncated, "The sentence admits too many readings to examine completely." if a.truncated
         else f"{a.eligible_readings} eligible readings of this sentence were examined.")
    alts = _alternatives(it, a)
    rule("no_eligible_reading_reproduces_the_number", not alts,
         ("Another eligible reading of the same sentence reproduces the printed number (" + "; ".join(_describe(r) for r in alts[:4])
          + "), so the mismatch is probably a wrong reading.") if alts else "No eligible reading of this sentence reproduces the printed number.",
         alternatives=[_describe(r) for r in alts[:8]])
    # rounding conventions: within one unit of the last printed digit is not a discrepancy
    variants = [(v.get("predicted_outcome") or {}) for v in (receipt.get("q1_mathematics") or {}).get("variants", [])]
    half = reported_half_unit(spec.reported)
    scale = unit_factor(ctx.data_unit(spec), spec.reported_unit) or Fraction(1)
    close = False
    for po in variants:
        if po.get("defined"):
            value = Fraction(int(po["exact"]["numerator"]), int(po["exact"]["denominator"]))
            kind = "rat" if po.get("value_kind") == "rational" else "sqrt"
            close = close or within(kind, po.get("sign"), value, scale, Fraction(spec.reported), 2 * half)
    rule("beyond_rounding_convention", not close,
         "The file's value differs from the printed number by no more than one unit in the last printed digit. Truncation, double rounding "
         "or round-half-even would explain that; it is not treated as a discrepancy." if close
         else "The difference exceeds one unit in the last printed digit.")
    fam = family(spec.stat) if spec.stat != "sem" else "sem"
    if fam in EXPLICIT_DISPERSION:
        named = EXPLICIT_DISPERSION[fam].search(window) is not None
        rule("dispersion_statistic_named_explicitly", named,
             "The sentence names this statistic explicitly." if named else
             "The sentence gives a “±” value without saying whether it is a standard deviation, a standard error or an interval.")
    odd = sorted({m.group(0).lower() for m in OUT_OF_GRAMMAR.finditer(window)})
    rule("no_out_of_grammar_wording", not odd,
         ("The sentence uses wording for statistics or transformations ClaimCheck does not compute (" + ", ".join(odd[:6]) + ").") if odd
         else "No wording for unsupported statistics or transformations was found in the sentence.")
    used = next((po.get("rows_used") for po in variants if po.get("defined")), None)
    printed_n = sorted({int(m.group(1).replace(",", "")) for m in SAMPLE_SIZE.finditer(window)})
    n_ok = not printed_n or used in printed_n
    rule("printed_sample_size_agrees", n_ok,
         f"The sentence prints n = {', '.join(map(str, printed_n))}, but this reading uses {used} rows of the file. The authors probably analysed "
         "different rows or a different file version." if not n_ok else
         ("The sentence prints no sample size." if not printed_n else f"The printed sample size {used} equals the rows this reading uses."))
    cor = corroborators(it, same_column=True)
    rule("supported_by_another_number_in_the_sentence", bool(cor),
         (f"Another number in this sentence ({', '.join(sorted({s.literal for s in cor}))}) is reproduced from the same column and the same rows, "
          "which supports the reading.") if cor else
         "No other number in the sentence is reproduced from the same column and rows, so nothing independent supports this reading.")
    if blocked:
        return out("REQUIRE_HUMAN_REVIEW")
    return out("DISCREPANCY_FOR_REVIEW", cor)
