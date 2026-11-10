"""Proposal -> gates -> exact oracle -> Lean kernel -> three-question receipt.

A *proposal* is untrusted data from any origin (rule, language model, person):

    {"quote": "<text copied from the paper>", "spec": {<ClaimSpec JSON>}, "quote_start": optional int}

The pipeline answers three separate questions and never lets one stand in for another:

  Q1 mathematics      PROVED / REFUTED / UNKNOWN — decided only by the Lean kernel on the exact
                      data bytes, for the typed claim, under explicitly listed assumptions.
  Q2 correspondence   which deterministic source/data bindings were checked; the *meaning* of the
                      sentence stays UNREVIEWED unless a named person confirms it.
  Q3 interpretation   NOT_ASSESSED — ClaimCheck never judges whether evidence supports a
                      scientific conclusion; it lists what remains open.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import AUTHORITY, VERSION
from .grounding import Grounding, ground
from .lean import (LeanUnavailable, MAX_DATA_BYTES, check_source, checker_sha256, obligation_source)
from .oracle import UNDEFINED_EXPLANATIONS, Outcome, evaluate
from .spec import ClaimSpec, SpecError, canonical, reported_half_unit, sha256_hex, unit_factor

RECEIPT_SCHEMA = "pcs-claimcheck-receipt-v1"
MAX_SOURCE_BYTES = 2_000_000
DEFAULT_NA = ("", "NA")
LINEAR_UNIT_STATS = ("sum", "mean", "median", "min", "max", "sd_sample", "sd_pop", "sem", "ols_intercept", "sd")

STAT_WORDS = {
    "count": "number of rows", "share": "fraction of rows", "sum": "sum", "mean": "arithmetic mean",
    "median": "median", "min": "minimum", "max": "maximum", "var_sample": "sample variance (denominator n − 1)",
    "sd_sample": "standard deviation (denominator n − 1)", "sd_pop": "standard deviation (denominator n)",
    "sem": "standard error of the mean (sample SD / √n)", "pearson": "Pearson correlation coefficient",
    "ols_slope": "ordinary-least-squares slope", "ols_intercept": "ordinary-least-squares intercept",
    "sd": "standard deviation (convention not stated)",
}


def _cond_words(c) -> str:
    if c.kind == "text_eq":
        return f"{c.column} is “{c.value}”"
    if c.kind == "text_ne":
        return f"{c.column} is not “{c.value}”"
    sym = {"eq": "=", "ne": "≠", "lt": "<", "le": "≤", "gt": ">", "ge": "≥"}[c.cmp]
    return f"{c.column} {sym} {c.value}"


def describe(spec: ClaimSpec) -> str:
    """Plain-language reading of a typed claim (deterministic; shown next to every verdict)."""
    where = " and ".join(_cond_words(c) for c in spec.filter)
    rows = f"rows where {where}" if where else "all rows"
    unit = f" {spec.reported_unit}" if spec.reported_unit else ""
    if spec.stat == "count":
        subject = f"number of {rows}" + (f" with a value in {spec.column}" if spec.column else "")
    elif spec.stat == "share":
        sub = " and ".join(_cond_words(c) for c in spec.sub_filter)
        subject = f"fraction of {rows} where {sub}"
    elif spec.stat in ("pearson", "ols_slope", "ols_intercept"):
        subject = f"{STAT_WORDS[spec.stat]} of {spec.column} against {spec.x_column} over {rows}"
    else:
        subject = f"{STAT_WORDS[spec.stat]} of {spec.column} over {rows}"
    return f"The {subject} equals {spec.reported}{unit} when rounded to the printed precision."


def _fraction_json(q: Fraction) -> dict:
    return {"numerator": str(q.numerator), "denominator": str(q.denominator)}


def _outcome_json(o: Outcome, scale: Fraction) -> dict:
    if not o.defined:
        return {"defined": False, "reason": o.reason, "explanation": UNDEFINED_EXPLANATIONS.get(o.reason, "")}
    out = {
        "defined": True, "verdict": o.verdict, "rows_used": o.used, "rows_skipped_as_missing": o.missing,
        "value_kind": "rational" if o.value_kind == "rat" else "signed_square_root",
        "exact": _fraction_json(o.value),
        "approximate_in_reported_units": float(o.approx() * float(scale)),
        "approximation_note": "floating-point rendering for display only; the verdict uses the exact value",
    }
    if o.value_kind == "sqrt":
        out["sign"] = o.sign
        out["exact_note"] = "value = sign × √(numerator/denominator)"
    return out


def _unknown(receipt: dict, reason: str, message: str) -> dict:
    receipt["result"] = "UNKNOWN"
    receipt["reason"] = reason
    receipt["message"] = message
    receipt.setdefault("q1_mathematics", {"status": "UNKNOWN", "why": "No arithmetic was checked."})
    receipt["scope"] = "Nothing is asserted about the paper’s statement."
    receipt["receipt_sha256"] = sha256_hex(canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"}))
    return receipt


def expand_spec(spec: ClaimSpec) -> list[tuple[ClaimSpec, str | None]]:
    """Concrete variants of a claim whose convention is not stated."""
    if spec.stat == "sd":
        return [(replace(spec, stat="sd_sample"), "standard deviation uses denominator n − 1"),
                (replace(spec, stat="sd_pop"), "standard deviation uses denominator n")]
    return [(spec, None)]


def verify_proposal(
    proposal: Any, *, source_text: str, source_meta: dict, data: bytes, manifest: dict,
    origin: str = "unspecified", run_lean: bool = True, lean_timeout: int = 600, keep_dir: Path | None = None,
    claim_id: str = "claim",
) -> dict:
    """Check one untrusted proposal.  Always returns a receipt; never raises on bad proposals."""
    data_sha = sha256_hex(data)
    receipt: dict = {
        "schema": RECEIPT_SCHEMA, "version": VERSION, "authority": AUTHORITY, "claim_id": claim_id,
        "proposal_origin": origin,
        "proposal_origin_note": "Who proposed this reading. A proposer has no authority; only the checks below count.",
        "source": {"name": source_meta.get("name"), "sha256": sha256_hex(source_text.encode("utf-8")),
                   "license": source_meta.get("license"), "citation": source_meta.get("citation")},
        "data": {"name": manifest.get("data_name"), "sha256": data_sha, "bytes": len(data),
                 "pinned_sha256": manifest.get("sha256"), "license": manifest.get("license"),
                 "origin": manifest.get("origin")},
        "q3_interpretation": {
            "status": "NOT_ASSESSED",
            "meaning": "ClaimCheck does not judge whether this number supports any scientific conclusion.",
            "open_obligations": [
                "Whether this file is the data the authors actually analysed (custody and completeness).",
                "Whether sampling, measurement and exclusions make the statistic meaningful for the question asked.",
                "Whether any comparison, trend or causal reading drawn from the number is justified.",
            ],
        },
    }
    # ---- proposal shape ------------------------------------------------------------------------
    try:
        if not isinstance(proposal, dict) or not isinstance(proposal.get("quote"), str):
            raise SpecError("proposal must be an object with a quote string and a spec object")
        if set(proposal) - {"quote", "spec", "quote_start", "note"}:
            raise SpecError("proposal has unexpected fields")
        quote_start = proposal.get("quote_start")
        if quote_start is not None and type(quote_start) is not int:
            raise SpecError("quote_start must be an integer")
        spec = ClaimSpec.from_json(proposal.get("spec"), allow_unspecified_sd=True)
    except SpecError as exc:
        receipt["q2_correspondence"] = {"status": "NOT_GROUNDED", "why": str(exc)}
        return _unknown(receipt, "malformed_proposal", f"The proposed claim is not well formed: {exc}")
    receipt["claim"] = {"spec": spec.to_json(), "reading": describe(spec)}

    # ---- data identity -------------------------------------------------------------------------
    pin = manifest.get("sha256")
    if pin is not None and pin != data_sha:
        receipt["q2_correspondence"] = {"status": "NOT_GROUNDED", "why": "data digest mismatch"}
        return _unknown(receipt, "data_digest_mismatch",
                        "The data file's SHA-256 differs from the digest pinned in the manifest. The file is corrupted, "
                        "truncated or a different version; nothing was checked against it.")
    if len(data) > MAX_DATA_BYTES:
        receipt["q2_correspondence"] = {"status": "NOT_CHECKED", "why": "data file too large"}
        return _unknown(receipt, "data_too_large",
                        f"The data file has {len(data)} bytes; the kernel check is bounded to {MAX_DATA_BYTES} bytes.")
    if len(source_text.encode("utf-8")) > MAX_SOURCE_BYTES:
        return _unknown(receipt, "source_too_large", "The source document exceeds the supported size.")

    # ---- Q2: deterministic grounding ------------------------------------------------------------
    g: Grounding = ground(source_text, proposal["quote"], spec, manifest, quote_start=quote_start)
    q2 = {
        "status": "GROUNDED" if g.ok else "NOT_GROUNDED",
        "meaning": ("GROUNDED means only that the checks below passed. It does not mean the sentence has been "
                    "understood: the semantic reading is a proposal until a named person confirms it."),
        "semantic_reading": "UNREVIEWED",
        "checks": g.checks,
        "data_digest_pinned": pin is not None,
        "failures": g.failures,
    }
    if g.quote_start is not None:
        q2["quote"] = {"start": g.quote_start, "end": g.quote_end, "text": g.quote_text}
        receipt["q3_interpretation"]["interpretive_wording_in_sentence"] = g.interpretive_terms
    if g.token_start is not None:
        q2["reported_value"] = {"start": g.token_start, "end": g.token_end, "printed": g.token_text,
                                "literal_checked": spec.reported, "unit_printed_after": g.detected_unit}
        q2["sentence"] = {"start": g.window_start, "end": g.window_end, "text": source_text[g.window_start:g.window_end]}
    if pin is None:
        q2["note_unpinned"] = "No expected digest was supplied for the data file, so only the bytes you gave were checked."
    receipt["q2_correspondence"] = q2
    if not g.checks.get("quote_in_source") or not g.checks.get("reported_value_in_quote"):
        return _unknown(receipt, "not_in_source", g.failures[0])

    # ---- units -----------------------------------------------------------------------------------
    columns = manifest.get("columns") or {}
    data_unit = "fraction" if spec.stat == "share" else (columns.get(spec.column or "") or {}).get("unit")
    if spec.reported_unit is not None and spec.stat not in LINEAR_UNIT_STATS + ("share",):
        return _unknown(receipt, "unit_not_supported", f"A unit conversion is not defined for the statistic “{spec.stat}”.")
    scale = unit_factor(data_unit, spec.reported_unit)
    if scale is None:
        return _unknown(receipt, "unit_not_convertible",
                        f"The claim reports {spec.reported_unit!r} but the manifest gives the data unit as {data_unit!r}; "
                        "no exact conversion between them is defined.")
    na_tokens = tuple(manifest.get("na_tokens") or DEFAULT_NA)

    # ---- Q1: oracle prediction, then the Lean kernel ----------------------------------------------
    variants = []
    for concrete, assumption in expand_spec(spec):
        outcome = evaluate(data, concrete, na_tokens, scale)
        entry = {"stat": concrete.stat, "assumption": assumption, "predicted_outcome": _outcome_json(outcome, scale)}
        if run_lean:
            try:
                src = obligation_source(data, concrete, na_tokens, scale, outcome)
                keep = None if keep_dir is None else keep_dir / f"{claim_id}.{concrete.stat}.lean"
                res = check_source(src, timeout=lean_timeout, keep=keep)
                entry["lean"] = res.to_json()
                entry["lean"]["checker_sha256"] = checker_sha256()
                if keep is not None:
                    entry["lean"]["obligation_file"] = keep.name
            except LeanUnavailable as exc:
                entry["lean"] = {"kernel_accepted": False, "detail": str(exc)}
        else:
            entry["lean"] = {"kernel_accepted": False, "detail": "Lean check not requested"}
        accepted = entry["lean"]["kernel_accepted"]
        entry["status"] = ("UNKNOWN" if not accepted or not outcome.defined
                           else "PROVED" if outcome.verdict == "consistent" else "REFUTED")
        variants.append((concrete, outcome, entry))

    half = reported_half_unit(spec.reported)
    assumptions = [
        f"Rounding: the printed value {spec.reported} stands for any exact value within ±{half} of it "
        "(rounding to the last printed digit, ties accepted either way).",
        f"Missing values: cells equal to one of {list(na_tokens)!r} are excluded; the count of excluded rows is part of the proof.",
        "Every other cell in the columns used is read as an exact decimal number; no rows are added, removed or reweighted.",
    ]
    if scale != 1:
        assumptions.append(f"Unit conversion: reported value = {scale} × statistic in data units ({data_unit} → {spec.reported_unit}).")
    statuses = [e["status"] for _, _, e in variants]
    q1: dict = {"variants": [e for _, _, e in variants], "assumptions": assumptions,
                "decided_by": "Lean 4 kernel (decide +kernel) on the exact data bytes; the Python prediction has no authority"}
    conditional_on = None
    if len(variants) == 1:
        q1["status"] = statuses[0]
    elif all(s == "PROVED" for s in statuses):
        q1["status"] = "PROVED"
        q1["note"] = "Holds under both standard-deviation conventions (n − 1 and n)."
    elif all(s == "REFUTED" for s in statuses):
        q1["status"] = "REFUTED"
        q1["note"] = "Fails under both standard-deviation conventions (n − 1 and n)."
    elif "UNKNOWN" in statuses:
        q1["status"] = "UNKNOWN"
    else:
        # one convention proves, the other refutes: a conditional result, reported as such
        proved = next(e for _, _, e in variants if e["status"] == "PROVED")
        q1["status"] = "UNKNOWN"
        conditional_on = proved["assumption"]
        q1["conditional"] = {
            "proved_if": proved["assumption"],
            "refuted_if": next(e for _, _, e in variants if e["status"] == "REFUTED")["assumption"],
            "note": "The source does not say which convention was used, so no unconditional verdict is given.",
        }
    receipt["q1_mathematics"] = q1
    primary = variants[0][1]
    if q1["status"] == "UNKNOWN":
        if conditional_on:
            return _finish(receipt, "UNKNOWN", "ambiguous_convention",
                           f"The value matches only if the {conditional_on}; the source does not state the convention.")
        if not primary.defined and all(e["lean"]["kernel_accepted"] for _, _, e in variants):
            return _finish(receipt, "UNKNOWN", "statistic_undefined",
                           UNDEFINED_EXPLANATIONS.get(primary.reason, "The statistic is undefined for this file.")
                           + " (The Lean kernel confirmed this.)")
        detail = next((e["lean"].get("detail") for _, _, e in variants if not e["lean"]["kernel_accepted"]), "")
        return _finish(receipt, "UNKNOWN", "not_kernel_checked", f"The Lean kernel did not confirm a verdict: {detail}")
    if not g.ok:
        return _finish(receipt, "UNKNOWN", "binding_not_grounded",
                       "The arithmetic was checked, but the link between the sentence and this reading failed a "
                       "deterministic check: " + " ".join(g.failures))
    return _finish(receipt, q1["status"], "checked", "")


def _finish(receipt: dict, result: str, reason: str, message: str) -> dict:
    spec_reading = receipt["claim"]["reading"]
    q1 = receipt["q1_mathematics"]
    receipt["result"] = result
    receipt["reason"] = reason
    data = receipt["data"]
    file_words = f"the data file {data.get('name') or ''} (SHA-256 {data['sha256'][:16]}…)".replace("  ", " ")
    if result == "PROVED":
        receipt["message"] = "The printed number is reproduced exactly from the data file under the stated reading."
        receipt["scope"] = (
            f"PROVED, for {file_words} only: “{spec_reading}” Not established: that this reading is what the authors "
            "meant, that this is the data they analysed, or that the number supports any conclusion.")
    elif result == "REFUTED":
        receipt["message"] = "Under the stated reading, the data file does not give the printed number."
        receipt["scope"] = (
            f"REFUTED, for {file_words} only: “{spec_reading}” This shows a mismatch between the printed number and "
            "this file under this reading. It does not show that the paper is wrong: the reading may be mistaken, or "
            "the authors may have analysed different rows or a different file version.")
    else:
        receipt["message"] = message
        math = q1.get("status")
        receipt["scope"] = ("Nothing is asserted about the paper’s statement."
                            + (f" (Arithmetic-only finding for the proposed reading: {math}; see q1_mathematics.)"
                               if math in ("PROVED", "REFUTED") else ""))
    receipt["receipt_sha256"] = sha256_hex(canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"}))
    return receipt


def verify_many(proposals: list[tuple[str, Any, str]], *, workers: int = 3, **kwargs) -> list[dict]:
    """Check several ``(claim_id, proposal, origin)`` triples; Lean runs in parallel processes."""
    def one(item):
        claim_id, proposal, origin = item
        return verify_proposal(proposal, claim_id=claim_id, origin=origin, **kwargs)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(one, proposals))
