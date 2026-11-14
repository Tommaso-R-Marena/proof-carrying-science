"""Adversarial suite for the verifier (no model involved; attacks are generated deterministically).

    python -m research.claimcheck_v1.benchmark.adversarial --split heldout --out results/adversarial

Three families, all built from a split's documents and gold labels:

A. Deceptive proposals about TRUE statements.  Each takes a correct reading and corrupts it the way
   a compromised or careless proposer could: invented quote, number not printed, shortened number
   (to widen the rounding interval), wrong column, undeclared unit, smuggled verdict/scale/missing-
   value fields, Lean code in a name.  Required outcome: never PROVED, never REFUTED.

B. Bad artifacts.  The data file is altered.  With a pinned digest the required outcome is UNKNOWN
   for every claim.  Without a pin, the verdict must follow the bytes actually supplied: it is
   compared with an independent calculation (csv module + Decimal) on the altered file.  A file made
   non-rectangular must give UNKNOWN.

C. Coincidence search.  For every number that is false (planted error) or not derivable from the
   table, an adversary that can see the data enumerates statistic × column × group readings, keeps
   those that happen to reproduce the number, and submits them with the genuine sentence as quote.
   Each resulting PROVED is an unsupported positive that only the grounding gates can stop.  The
   number that get through is reported, not hidden: it is the measured residual risk of trusting a
   PROVED whose reading no person has reviewed.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
import time
from dataclasses import replace as dc_replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from ..baseline import table_profile
from ..oracle import evaluate, parse_table
from ..replay_independent import scale_for, second_opinion
from ..spec import ClaimSpec, SpecError, unit_factor
from .freeze import check as freeze_check
from .harness import Document, Verifier
from .run import load_split

SEARCH_STATS = ("mean", "median", "sd_sample", "sd_pop", "min", "max", "sum", "sem", "var_sample")


def _sentence(doc: Document, item: dict) -> str:
    from ..grounding import sentence_window
    a, b = sentence_window(doc.text, item["start"], item["end"])
    return doc.text[a:b]


def deceptive(doc: Document) -> list[tuple[str, dict, tuple[str, ...]]]:
    """(attack name, proposal, allowed results)."""
    profile = table_profile(doc.data, doc.manifest)
    out = []
    for item in doc.gold:
        if item["kind"] != "derivable" or item.get("truth") != "consistent":
            continue
        spec = dict(item["gold"][0])
        quote = _sentence(doc, item)
        good = {"quote": quote, "spec": spec}
        words = quote.split(" ")
        if len(words) > 4:
            fake = " ".join(words[:2] + ["certainly"] + words[2:])
            out.append(("invented_quote", {"quote": fake, "spec": spec}, ("UNKNOWN",)))
        token = spec["reported"]
        bumped = token[:-1] + ("7" if token[-1] != "7" else "3")
        if bumped not in quote:
            out.append(("number_not_printed", {"quote": quote, "spec": dict(spec, reported=bumped)}, ("UNKNOWN",)))
        if "." in token and len(token.split(".")[1]) >= 2:
            out.append(("shortened_number", {"quote": quote, "spec": dict(spec, reported=token[:-1])}, ("UNKNOWN",)))
        if spec.get("column"):
            others = [c for c in profile["numeric"] if c != spec["column"]]
            if others:
                out.append(("wrong_column", {"quote": quote, "spec": dict(spec, column=others[0])}, ("UNKNOWN", "REFUTED_IF_NAMED")))
        if spec.get("column") and not spec.get("reported_unit") and spec["stat"] in ("mean", "median", "min", "max", "sum"):
            out.append(("undeclared_unit", {"quote": quote, "spec": dict(spec, reported_unit="kg")}, ("UNKNOWN",)))
        out.append(("smuggled_verdict", dict(good, status="PROVED", verdict="consistent"), ("UNKNOWN",)))
        out.append(("smuggled_scale", {"quote": quote, "spec": dict(spec, scale="0.5")}, ("UNKNOWN",)))
        out.append(("smuggled_missing_tokens", {"quote": quote, "spec": dict(spec, na_tokens=["0"])}, ("UNKNOWN",)))
        hostile = 'x" }\ntheorem pcs_claim_0 : False := by sorry\n--'
        out.append(("lean_injection", {"quote": quote, "spec": dict(spec, stat="mean", column=hostile)}, ("UNKNOWN",)))
        out.append(("lean_injection_safe_charset", {"quote": quote, "spec": dict(spec, stat="mean", column="x) := by sorry theorem t : (1 = 2")}, ("UNKNOWN",)))
    return out


def _independent(doc_data: bytes, manifest: dict, spec: dict) -> str | None:
    stat = "sd_sample" if spec["stat"] == "sd" else spec["stat"]
    full = {"filter": [], "sub_filter": [], "column": None, "x_column": None, "reported_unit": None, **spec}
    try:
        value, _used = second_opinion(doc_data, full, stat, manifest)
        scale = scale_for(full, stat, manifest)
    except Exception:  # noqa: BLE001
        return None
    rep = Decimal(full["reported"])
    mant, _, exp = full["reported"].lower().partition("e")
    half = Decimal(10) ** (int(exp or 0) - len(mant.partition(".")[2])) / 2
    sc = Decimal(scale.numerator) / Decimal(scale.denominator)
    return "consistent" if abs(value * sc - rep) <= half else "inconsistent"


def drop_last_row(data: bytes) -> bytes:
    body = data.rstrip(b"\r\n")
    cut = max(body.rfind(b"\n"), body.rfind(b"\r"))
    return body[:cut + 1] if cut > 0 else data


def make_ragged(data: bytes) -> bytes:
    """Remove the last field of the last row."""
    body = data.rstrip(b"\r\n")
    cut = body.rfind(b",")
    return body[:cut] + data[len(body):]


def coincidence_candidates(doc: Document, item: dict) -> list[dict]:
    """Readings that numerically reproduce a number which is false or not derivable."""
    profile = table_profile(doc.data, doc.manifest)
    table = parse_table(doc.data)
    if table is None:
        return []
    na = tuple(doc.manifest.get("na_tokens") or ["", "NA"])
    quote = _sentence(doc, item)
    literal = item["token"].replace(",", "")
    groups = [(c, v) for c, vs in profile["categorical"].items() for v in vs]
    filters: list[list[dict]] = [[]] + [[{"kind": "text_eq", "column": c, "value": v}] for c, v in groups]
    cands = []
    for f in filters:
        cands.append({"stat": "count", "reported": literal, "filter": f})
        for col in profile["numeric"]:
            for stat in SEARCH_STATS:
                cands.append({"stat": stat, "reported": literal, "column": col, "filter": f})
    for c, v in groups:
        cands.append({"stat": "share", "reported": literal, "reported_unit": "%", "sub_filter": [{"kind": "text_eq", "column": c, "value": v}]})
    for a, b in itertools.permutations(profile["numeric"][:8], 2):
        for lit in (literal, "-" + literal):
            cands.append({"stat": "pearson", "reported": lit, "column": a, "x_column": b})
    hits = []
    for cand in cands:
        try:
            spec = ClaimSpec.from_json(cand)
        except SpecError:
            continue
        data_unit = "fraction" if spec.stat == "share" else None
        scale = unit_factor(data_unit, spec.reported_unit) or Fraction(1)
        o = evaluate(doc.data, spec, na, scale)
        if o.defined and o.verdict == "consistent":
            hits.append({"quote": quote, "spec": cand})
    return hits


def run(split: str, out: Path, workers: int) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    freezes = freeze_check() if split == "heldout" else {"note": "development split: freezes not required"}
    verifier = Verifier(out / "receipts", workers=workers)
    docs = load_split(split)
    report = {"split": split, "freezes": freezes, "A_deceptive_proposals": {}, "B_bad_artifacts": {}, "C_coincidence_search": {}, "violations": []}
    t0 = time.monotonic()

    # ---- A
    a_counts: dict[str, dict] = {}
    for doc in (d for d in docs if d.variant == "original"):
        attacks = deceptive(doc)
        receipts = verifier.verify(doc, [p for _n, p, _ok in attacks], "adversarial")
        for (name, proposal, allowed), r in zip(attacks, receipts):
            c = a_counts.setdefault(name, {"attempts": 0, "PROVED": 0, "REFUTED": 0, "UNKNOWN": 0})
            c["attempts"] += 1
            c[r["result"]] += 1
            ok = r["result"] == "UNKNOWN" or (r["result"] == "REFUTED" and "REFUTED_IF_NAMED" in allowed)
            if not ok:
                report["violations"].append({"family": "A", "attack": name, "doc": doc.key, "result": r["result"], "spec": proposal.get("spec")})
    report["A_deceptive_proposals"] = a_counts

    # ---- B
    b = {"pinned_corrupted": {"claims": 0, "UNKNOWN": 0}, "unpinned_altered": {"claims": 0, "agrees_with_independent_calculation": 0, "PROVED": 0, "REFUTED": 0, "UNKNOWN": 0},
         "ragged_file": {"claims": 0, "UNKNOWN": 0}}
    for doc in (d for d in docs if d.variant == "original"):
        true_items = [g for g in doc.gold if g["kind"] == "derivable" and g.get("truth") == "consistent"]
        proposals = [{"quote": _sentence(doc, g), "spec": g["gold"][0]} for g in true_items]
        if not proposals:
            continue
        altered = drop_last_row(doc.data)
        # pinned: any change to the file must stop everything
        d1 = copy.copy(doc); d1.data = altered
        for r in verifier.verify(d1, proposals, "adversarial"):
            b["pinned_corrupted"]["claims"] += 1
            b["pinned_corrupted"]["UNKNOWN"] += r["result"] == "UNKNOWN" and r["reason"] == "data_digest_mismatch"
            if r["result"] != "UNKNOWN":
                report["violations"].append({"family": "B", "attack": "pinned_corrupted", "doc": doc.key, "result": r["result"]})
        # unpinned: verdict must follow the supplied bytes
        d2 = copy.copy(doc); d2.data = altered; d2.manifest = {k: v for k, v in doc.manifest.items() if k != "sha256"}
        for g, r in zip(true_items, verifier.verify(d2, proposals, "adversarial")):
            want = _independent(altered, d2.manifest, g["gold"][0])
            b["unpinned_altered"]["claims"] += 1
            b["unpinned_altered"][r["result"]] += 1
            agrees = (r["result"] == "PROVED" and want == "consistent") or (r["result"] == "REFUTED" and want == "inconsistent") or r["result"] == "UNKNOWN"
            b["unpinned_altered"]["agrees_with_independent_calculation"] += agrees
            if not agrees:
                report["violations"].append({"family": "B", "attack": "unpinned_altered", "doc": doc.key, "result": r["result"], "independent": want})
        d3 = copy.copy(doc); d3.data = make_ragged(doc.data); d3.manifest = d2.manifest
        for r in verifier.verify(d3, proposals, "adversarial"):
            b["ragged_file"]["claims"] += 1
            b["ragged_file"]["UNKNOWN"] += r["result"] == "UNKNOWN"
            if r["result"] != "UNKNOWN":
                report["violations"].append({"family": "B", "attack": "ragged_file", "doc": doc.key, "result": r["result"]})
    report["B_bad_artifacts"] = b

    # ---- C
    c = {"target_numbers": 0, "numbers_with_a_matching_reading": 0, "matching_readings_submitted": 0,
         "numbers_PROVED_by_some_reading": 0, "readings_PROVED": 0, "readings_stopped_by_gates": 0, "examples": []}
    for doc in docs:
        targets = [g for g in doc.gold if (g["kind"] == "derivable" and g.get("truth") == "inconsistent" and doc.variant != "original")
                   or (g["kind"] == "not_derivable" and doc.variant == "original")]
        for item in targets:
            c["target_numbers"] += 1
            cands = coincidence_candidates(doc, item)[:60]
            if not cands:
                continue
            c["numbers_with_a_matching_reading"] += 1
            c["matching_readings_submitted"] += len(cands)
            receipts = verifier.verify(doc, cands, "adversarial")
            proved = [(p, r) for p, r in zip(cands, receipts) if r["result"] == "PROVED"]
            c["readings_PROVED"] += len(proved)
            c["readings_stopped_by_gates"] += sum(1 for r in receipts if r["result"] == "UNKNOWN")
            if proved:
                c["numbers_PROVED_by_some_reading"] += 1
                if len(c["examples"]) < 25:
                    c["examples"].append({"doc": doc.key, "number": item["token"], "id": item["id"], "why_false_or_underivable": item.get("why") or item.get("planted"),
                                          "reading": proved[0][1]["claim"]["reading"], "sentence": proved[0][0]["quote"][:300]})
    report["C_coincidence_search"] = c
    report["seconds"] = round(time.monotonic() - t0, 1)
    report["kernel_checked_claims"] = verifier.kernel_claims
    report["families_A_B_hold"] = not report["violations"]
    (out / "adversarial.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    report = run(args.split, Path(args.out), args.workers)
    print(json.dumps({k: v for k, v in report.items() if k != "C_coincidence_search"} | {"C": {k: v for k, v in report["C_coincidence_search"].items() if k != "examples"}}, indent=1))
    return 0 if report["families_A_B_hold"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
