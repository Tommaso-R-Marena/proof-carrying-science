"""Proposals -> v1 gates and Lean kernel (unchanged) -> v1.1 semantic policy -> three-layer records.

One record per proposed reading.  Each record keeps three statements apart:

  mathematical    what the kernel established about the typed statement and the exact file bytes
  source_reading  whether there is enough support to say the sentence makes that statement
  scientific      never assessed

and gives one outward verdict that is never stronger than the weakest of the first two.
"""
from __future__ import annotations

import datetime
import html
import json
import platform
from pathlib import Path
from typing import Any

from ..claimcheck_v1.bundle import write_bundle
from ..claimcheck_v1.lean import checker_sha256
from ..claimcheck_v1.pipeline import validate_manifest, verify_many
from ..claimcheck_v1.spec import canonical, sha256_hex
from . import AUTHORITY, VERSION
from .policy import assess_document, policy_parameters, sibling_proposals
from .space import SourceContext

RECORD_SCHEMA = "pcs-claimcheck-record-v1.1"
BUNDLE_SCHEMA = "pcs-claimcheck-bundle-v1.1"
SIBLING_ORIGIN = "claimcheck-v1.1 automatic sibling search (has seen the data; untrusted)"
MAX_SIBLINGS = 12

OUTWARD_TEXT = {
    "CONFIRMATION": (
        "The printed number is reproduced from this file under the stated reading. The wording attached to the number fits the "
        "statistic, no other statistic or column named in the sentence reproduces it, and a chance match is unlikely even for "
        "someone who chose the reading after seeing the data. No person has reviewed the reading."),
    "DISCREPANCY_FOR_REVIEW": (
        "Under the stated reading, this file does not give the printed number, and another number in the same sentence is "
        "reproduced from the same column and rows, which supports the reading. This is a discrepancy for a person to look at. "
        "It does not show that the paper is wrong: the authors may have analysed other rows, another version of the file, or "
        "a statistic this tool does not compute."),
    "REQUIRE_HUMAN_REVIEW": (
        "A mathematical result exists and is preserved below, but support for the reading is not sufficient for an automatic "
        "statement about the paper. A person has to decide whether the sentence means this."),
    "UNKNOWN": "No mathematical result could be attached to a number in the source.",
}
MATH_TEXT = {
    "MATCH_PROVED": "Proved by the Lean kernel: the typed statement below is TRUE of the exact bytes of this file.",
    "MISMATCH_PROVED": "Proved by the Lean kernel: the typed statement below is FALSE of the exact bytes of this file.",
    "CONDITIONAL_ON_CONVENTION": "Proved by the Lean kernel under each standard-deviation convention separately: true under one, false under the other.",
    "UNDEFINED_PROVED": "Proved by the Lean kernel: the statistic is undefined for this file under the stated reading.",
    "NOT_ESTABLISHED": "Nothing was established by the Lean kernel.",
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_record(receipt: dict, decision: dict, *, selection: dict | None, kernel_run: dict | None,
                 human_review: dict | None = None, auxiliary: bool = False) -> dict:
    q1 = receipt.get("q1_mathematics") or {}
    variants = q1.get("variants") or []
    accepted = bool(variants) and all((v.get("lean") or {}).get("kernel_accepted") for v in variants)
    math = decision["mathematical_status"]
    verdict = decision["verdict"]
    record = {
        "schema": RECORD_SCHEMA, "version": VERSION, "authority": AUTHORITY, "claim_id": receipt.get("claim_id"),
        "auxiliary": auxiliary,
        "outward": {"verdict": verdict, "statement": OUTWARD_TEXT[verdict], "reasons": decision["reasons"],
                    "never_means": "that the paper is right or wrong, that this is the data the authors analysed, or that any conclusion follows"},
        "mathematical": {
            "status": math, "statement": (receipt.get("claim") or {}).get("reading"), "meaning": MATH_TEXT[math],
            "kernel_accepted_every_theorem": accepted,
            "theorems": [{"statistic": v.get("stat"), "assumption": v.get("assumption"), "status": v.get("status"),
                          "obligation_sha256": (v.get("lean") or {}).get("obligation_sha256"), "obligation_file": (v.get("lean") or {}).get("obligation_file"),
                          "theorem": (v.get("lean") or {}).get("theorem"), "axioms": (v.get("lean") or {}).get("axioms"),
                          "toolchain": (v.get("lean") or {}).get("toolchain"), "checker_sha256": (v.get("lean") or {}).get("checker_sha256"),
                          "outcome": v.get("predicted_outcome")} for v in variants],
            "assumptions": q1.get("assumptions") or [],
            "kernel_run": kernel_run if accepted else None,
            "scope": "Only the typed statement and the exact bytes named by the SHA-256 below. Not the sentence, not the paper.",
            "data_sha256": (receipt.get("data") or {}).get("sha256"),
        },
        "source_reading": {
            "status": {"CONFIRMATION": "SUPPORTED_BY_AUTOMATIC_CHECKS", "DISCREPANCY_FOR_REVIEW": "SUPPORTED_BY_AUTOMATIC_CHECKS",
                       "REQUIRE_HUMAN_REVIEW": "REQUIRE_HUMAN_REVIEW", "UNKNOWN": "NOT_ATTACHED"}[verdict],
            "reviewed_by_a_person": False,
            "human_review_on_record": human_review,
            "human_review_note": ("A statement by a named person is recorded as supplied. PCS does not verify who wrote it, and it does not change "
                                  "the automatic verdict.") if human_review else None,
            "selection": selection or {"proposed_by": receipt.get("proposal_origin"), "saw_the_data": "unknown"},
            "selection_note": "The policy assumes the reading may have been chosen after looking at the data, whoever proposed it.",
            "findings": decision["findings"], "corroborated_by": decision["corroborated_by"],
            "lexical_checks": (receipt.get("q2_correspondence") or {}).get("checks"),
            "lexical_failures": (receipt.get("q2_correspondence") or {}).get("failures"),
            "sentence": (receipt.get("q2_correspondence") or {}).get("sentence"),
            "printed_number": (receipt.get("q2_correspondence") or {}).get("reported_value"),
            "policy": decision["policy"],
        },
        "scientific": {
            "status": "NOT_ASSESSED",
            "open_questions": list((receipt.get("q3_interpretation") or {}).get("open_obligations") or []) + [
                "Whether the deposited file is the version, subset and transformation of the data that the printed number was computed from.",
                "Whether the statistic, as defined here (missing values, rounding, denominator), is the one the authors computed."],
            "interpretive_wording_in_sentence": (receipt.get("q3_interpretation") or {}).get("interpretive_wording_in_sentence") or [],
        },
        "v1_receipt_sha256": receipt.get("receipt_sha256"),
        "v1_result": receipt.get("result"),
    }
    record["record_sha256"] = sha256_hex(canonical(record))
    return record


def verify(proposals: list[tuple[str, Any, str]], *, source_text: str, source_meta: dict, data: bytes, manifest: dict,
           selection: dict | None = None, human_review: dict | None = None, run_lean: bool = True, lean_timeout: int = 900,
           keep_dir: Path | None = None, workers: int = 2, batch_size: int = 4, find_siblings: bool = True) -> dict:
    """Verify ``(claim_id, proposal, origin)`` triples about one source and one data file."""
    started = _now()
    common = dict(source_text=source_text, source_meta=source_meta, data=data, manifest=manifest, run_lean=run_lean,
                  lean_timeout=lean_timeout, keep_dir=keep_dir, workers=workers, batch_size=batch_size, lean_when_ungrounded=True)
    usable = isinstance(manifest, dict) and validate_manifest(manifest) is None
    ctx = SourceContext(source_text, data, manifest) if usable else None
    extra: list[dict] = []
    if ctx is not None and find_siblings:
        # Gates and oracle only (no kernel): which other numbers of the same sentence could corroborate a reading?
        prelim = verify_many(proposals, **{**common, "run_lean": False, "keep_dir": None})
        seen = {canonical({"q": " ".join(str(p.get("quote", "")).split()), "s": p.get("spec")}) for _i, p, _o in proposals if isinstance(p, dict)}
        for r in prelim:
            if (r.get("q2_correspondence") or {}).get("status") == "GROUNDED" and r.get("claim"):
                for prop in sibling_proposals(ctx, r):
                    key = canonical({"q": " ".join(prop["quote"].split()), "s": prop["spec"]})
                    if key not in seen and len(extra) < MAX_SIBLINGS:
                        seen.add(key)
                        extra.append(prop)
    # One kernel pass over the submitted readings and the automatically found siblings together.
    everything = verify_many(list(proposals) + [(f"s{i + 1:03d}", p, SIBLING_ORIGIN) for i, p in enumerate(extra)], **common)
    receipts = everything[:len(proposals)]
    if ctx is not None:
        decisions = assess_document(ctx, everything)
    else:
        decisions = [{"verdict": "UNKNOWN", "mathematical_status": "NOT_ESTABLISHED", "reasons": ["The dataset manifest is not usable."],
                      "findings": [], "corroborated_by": [], "policy": policy_parameters()} for _ in everything]
    lean_versions = sorted({(v.get("lean") or {}).get("toolchain") for r in everything for v in (r.get("q1_mathematics") or {}).get("variants", [])
                            if (v.get("lean") or {}).get("kernel_accepted")})
    kernel_run = {"fresh": True, "started_utc": started, "finished_utc": _now(), "lean": lean_versions, "checker_sha256": checker_sha256(),
                  "host": platform.platform(), "note": "The kernel ran in this invocation. A copy of this record is not a new run."} if run_lean else None
    records = [build_record(r, d, selection=selection if i < len(receipts) else {"proposed_by": SIBLING_ORIGIN, "saw_the_data": "yes"},
                            kernel_run=kernel_run, human_review=human_review if i < len(receipts) else None, auxiliary=i >= len(receipts))
               for i, (r, d) in enumerate(zip(everything, decisions))]
    return {"records": records, "v1_receipts": everything, "kernel_run": kernel_run}


# ---- bundle and report ---------------------------------------------------------------------------
_COLOUR = {"CONFIRMATION": "#1b6e3c", "DISCREPANCY_FOR_REVIEW": "#8a4b00", "REQUIRE_HUMAN_REVIEW": "#4a4a8a", "UNKNOWN": "#555"}
_LABEL = {"CONFIRMATION": "Number reproduced", "DISCREPANCY_FOR_REVIEW": "Discrepancy for a person to review",
          "REQUIRE_HUMAN_REVIEW": "A person must review the reading", "UNKNOWN": "Unknown"}


def _e(x) -> str:
    return html.escape(str(x), quote=True)


def render_report(records: list[dict], *, source_name: str, data_name: str) -> str:
    """Static, script-free HTML.  Every string from a paper, a data file or a proposer is escaped."""
    parts = [
        "<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>",
        "<title>ClaimCheck v1.1 report</title>",
        "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:62rem;margin:2rem auto;padding:0 1rem;color:#1a1a1a}"
        "h1{font-size:1.5rem}h2{font-size:1.15rem;margin:.2rem 0}h3{font-size:1rem;margin:.8rem 0 .2rem}"
        "article{border:1px solid #bbb;border-radius:8px;padding:1rem;margin:1.2rem 0}"
        ".b{display:inline-block;color:#fff;border-radius:4px;padding:.15rem .6rem;font-weight:700}"
        ".g{display:grid;grid-template-columns:repeat(auto-fit,minmax(17rem,1fr));gap:.8rem}.g>div{border:1px solid #ddd;border-radius:6px;padding:.6rem}"
        "blockquote{margin:.5rem 0;padding:.25rem .75rem;border-left:4px solid #999;background:#f6f6f6}"
        "li.no{color:#7a1f1f}small{color:#555}ul{margin:.2rem 0 .2rem 1.1rem;padding:0}code{background:#f0f0f0;padding:0 .2rem}</style>",
        "<h1>ClaimCheck v1.1 report</h1>",
        f"<p>Source: <code>{_e(source_name)}</code>. Data: <code>{_e(data_name)}</code>. Research tool, no production authority. "
        "Each result has three separate parts. Only the first is a proof, and it is a proof about the file, not about the paper.</p>",
    ]
    for r in records:
        o, m, s = r["outward"], r["mathematical"], r["source_reading"]
        sentence = (s.get("sentence") or {}).get("text") or ""
        parts.append(f"<article><h2><span class=b style='background:{_COLOUR[o['verdict']]}'>{_e(_LABEL[o['verdict']])}</span> "
                     f"<small>{_e(r.get('claim_id'))}{' · found automatically as supporting evidence' if r.get('auxiliary') else ''}</small></h2>")
        parts.append(f"<p>{_e(o['statement'])}</p>")
        if o["reasons"]:
            parts.append("<ul>" + "".join(f"<li class=no>{_e(x)}</li>" for x in o["reasons"]) + "</ul>")
        if sentence:
            parts.append(f"<blockquote>{_e(sentence)}</blockquote>")
        parts.append("<div class=g>")
        parts.append(f"<div><h3>1. Mathematics: {_e(m['status'].replace('_', ' ').lower())}</h3><p>{_e(m['meaning'])}</p>"
                     f"<p><em>{_e(m['statement'] or 'No typed statement.')}</em></p>")
        for t in m["theorems"]:
            po = t.get("outcome") or {}
            if po.get("defined"):
                parts.append(f"<p><small>{_e(t['statistic'])}: file value ≈ {po.get('approximate_in_reported_units'):.10g}, {po.get('rows_used')} rows used, "
                             f"{po.get('rows_skipped_as_missing')} skipped as missing. Proof file SHA-256 {_e((t.get('obligation_sha256') or '')[:16])}…</small></p>")
        run = m.get("kernel_run")
        parts.append(f"<p><small>{'Kernel run in this invocation: ' + _e(run['finished_utc']) + ', ' + _e('; '.join(run['lean'])) if run else 'No kernel run is recorded for this result.'}"
                     f" Data SHA-256 {_e((m.get('data_sha256') or '')[:16])}…</small></p></div>")
        parts.append(f"<div><h3>2. Reading of the sentence: {_e(s['status'].replace('_', ' ').lower())}</h3><ul>")
        for f in s["findings"]:
            parts.append(f"<li class={'yes' if f['passed'] else 'no'}>{'✓' if f['passed'] else '✗'} {_e(f['detail'])}</li>")
        for x in s.get("lexical_failures") or []:
            parts.append(f"<li class=no>✗ {_e(x)}</li>")
        parts.append("</ul><p><small>These checks are mechanical. None of them is a person reading the paper.</small></p>")
        if s.get("human_review_on_record"):
            parts.append(f"<p><small>Statement on record (not verified by PCS): {_e(json.dumps(s['human_review_on_record'], ensure_ascii=False))}</small></p>")
        parts.append("</div>")
        parts.append("<div><h3>3. Science: not assessed</h3><ul>" + "".join(f"<li>{_e(x)}</li>" for x in r["scientific"]["open_questions"]) + "</ul></div>")
        parts.append("</div></article>")
    return "".join(parts)


def write_bundle_v11(out: Path, result: dict, *, source_text: str, data: bytes, manifest: dict, source_name: str, data_name: str) -> dict:
    """``out/v1`` is an ordinary v1 bundle (replayable by the v1 replayer); the v1.1 records sit beside it."""
    out.mkdir(parents=True, exist_ok=True)
    write_bundle(out / "v1", source_text=source_text, data=data, manifest=manifest, receipts=result["v1_receipts"],
                 source_name=source_name, data_name=data_name, extra={"wrapped_by": VERSION})
    records = result["records"]
    (out / "records.json").write_text(json.dumps(records, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    (out / "report.html").write_text(render_report(records, source_name=source_name, data_name=data_name), encoding="utf-8")
    files = {name: sha256_hex((out / name).read_bytes()) for name in ("records.json", "report.html", "v1/bundle.json")}
    index = {"schema": BUNDLE_SCHEMA, "version": VERSION, "authority": AUTHORITY, "policy": policy_parameters(),
             "checker_sha256": checker_sha256(), "kernel_run": result["kernel_run"], "files": files,
             "counts": {v: sum(1 for r in records if r["outward"]["verdict"] == v and not r["auxiliary"]) for v in OUTWARD_TEXT},
             "replay": "python replay_independent_v1_1.py <this directory> --checker-sha256 <digest of the reviewed ClaimCheck.lean>"}
    (out / "claimcheck_v1_1.json").write_text(json.dumps(index, indent=1, sort_keys=True), encoding="utf-8")
    return index
