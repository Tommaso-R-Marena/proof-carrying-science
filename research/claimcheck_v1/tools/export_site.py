"""Export recorded held-out examples and the benchmark summary for the public website page.

    python -m research.claimcheck_v1.tools.export_site --bundles benchmark/results/bundles \
        --summary benchmark/results/heldout/summary.json --adversarial benchmark/results/adversarial/adversarial.json \
        --site ../proof-carrying-science-site/public

Reporting tool only (not part of the frozen software; it calls the frozen pipeline unchanged).
For each document it selects the decided readings of an exported bundle plus a few instructive
UNKNOWNs, verifies that selection afresh so that it forms one obligation file, and writes one JSON
per example.  The website rebuilds the obligation bytes from that JSON in the browser and compares
the SHA-256, so a recorded result cannot be shown for different data or readings.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import json
import shutil
import tempfile
from pathlib import Path

from ..lean import CHECKER_PATH, checker_sha256
from ..pipeline import verify_many
from ..spec import sha256_hex

LABELS = {"rules": "Cue-word rules (no model)", "search": "Data-matching search (no model)", "gemini": "Gemini model",
          "openrouter": "Nemotron model (via OpenRouter)", "union": "Both models, all proposals", "agree": "Only readings both models proposed",
          "gemini+critic": "Gemini, filtered by Nemotron as critic", "openrouter+critic": "Nemotron, filtered by Gemini as critic"}


def select(receipts: list[dict], max_unknown: int = 5) -> list[dict]:
    chosen, seen, reasons = [], set(), {}
    for r in receipts:
        rv = r.get("q2_correspondence", {}).get("reported_value")
        if r["result"] in ("PROVED", "REFUTED") and rv:
            key = (rv["start"], r["result"], json.dumps(r["claim"]["spec"], sort_keys=True))
            if key not in seen:
                seen.add(key)
                chosen.append(r)
    for r in receipts:
        if r["result"] == "UNKNOWN" and "claim" in r and r.get("q2_correspondence", {}).get("quote") and reasons.get(r["reason"], 0) < 2 \
                and sum(reasons.values()) < max_unknown and r["reason"] in ("binding_not_grounded", "ambiguous_convention", "statistic_undefined", "not_kernel_checked"):
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
            chosen.append(r)
    chosen.sort(key=lambda r: (r.get("q2_correspondence", {}).get("reported_value", {}).get("start", 10**9)))
    return chosen


def export(bundles: Path, summary_path: Path, adversarial_path: Path | None, site: Path) -> dict:
    out_dir = site / "claim-check" / "examples"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    shutil.copy(CHECKER_PATH, site / "claim-check" / "ClaimCheck.lean")
    catalog, skipped = [], []
    for bundle in sorted(p for p in bundles.iterdir() if (p / "bundle.json").exists()):
        index = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
        doc = index["extra"]["document"]
        receipts = json.loads((bundle / "receipts.json").read_text(encoding="utf-8"))
        data = (bundle / "data.csv").read_bytes()
        source = (bundle / "source.txt").read_bytes().decode("utf-8")
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        origins_all = sorted({r["proposal_origin"] for r in receipts if r["result"] in ("PROVED", "REFUTED")})
        meta = {"name": doc["slug"], "license": doc["article_license"], "citation": doc["citation"]}

        def attempt(chosen: list[dict]):
            """Verify one selection afresh; None unless it forms exactly one accepted obligation file."""
            with tempfile.TemporaryDirectory() as tmp:
                out = verify_many(
                    [(f"e{i + 1:03d}", {"quote": r["q2_correspondence"]["quote"]["text"], "quote_start": r["q2_correspondence"]["quote"]["start"],
                                        "spec": r["claim"]["spec"]}, r["proposal_origin"]) for i, r in enumerate(chosen)],
                    source_text=source, source_meta=meta, data=data, manifest=manifest, keep_dir=Path(tmp), batch_size=128, workers=1,
                    lean_timeout=1800, lean_when_ungrounded=False)
                files = sorted(Path(tmp).glob("*.lean"))
                if len(files) != 1:
                    return None
                if [r["result"] for r in out] != [r["result"] for r in chosen]:
                    raise SystemExit(f"{doc['slug']}: fresh verification disagrees with the bundle")
                return out, files[0].read_bytes()

        full = select(receipts)
        if not full:
            continue
        # A large table can make Lean reject an obligation file that holds many claims although it
        # accepts the same claims one or two per file.  The website shows one file per example, so
        # fall back to a smaller selection (proved readings first) and say so in the example.
        decided = sorted((r for r in full if r["result"] in ("PROVED", "REFUTED")), key=lambda r: r["result"] != "PROVED")
        ungrounded = [r for r in full if r["result"] == "UNKNOWN" and r["reason"] == "binding_not_grounded"][:2]
        by_position = lambda rs: sorted(rs, key=lambda r: r.get("q2_correspondence", {}).get("reported_value", {}).get("start", 10**9))
        result, picked, selection_note = None, full, None
        for cap in (None, 4, 2):
            picked = full if cap is None else by_position(decided[:cap] + ungrounded)
            result = attempt(picked)
            if result is not None:
                if cap is not None:
                    selection_note = (f"This table is large: Lean accepts its checks only a few per proof file. {len(picked)} of the "
                                      f"{len(full)} selected readings are shown here; all of them are in the evidence bundle in the core repository.")
                break
        if result is None:
            skipped.append({"id": doc["slug"], "reason": "no selection of readings formed one accepted obligation file"})
            continue
        fresh, obligation = result
        origins = sorted({r["proposal_origin"] for r in picked}) or origins_all
        example = {
            "id": doc["slug"], "title": doc["citation"].split(")")[1].split(".")[0].strip() if ")" in doc["citation"] else doc["slug"],
            "citation": doc["citation"], "article_license": doc["article_license"].upper(), "article_doi": doc["article_doi"],
            "data_license": doc["data_license"], "data_name": manifest.get("data_name"), "data_origin": f"Zenodo record {doc['zenodo_record']}",
            "data_sha256": sha256_hex(data), "data_base64": base64.b64encode(data).decode("ascii"),
            "na_tokens": manifest.get("na_tokens") or ["", "NA"],
            "column_units": {k: v.get("unit") for k, v in (manifest.get("columns") or {}).items() if v.get("unit")},
            "obligation_sha256": sha256_hex(obligation), "proposed_by": " and ".join(origins) or "the benchmark arms",
            "selection_note": selection_note, "receipts": fresh,
        }
        (out_dir / f"{doc['slug']}.json").write_text(json.dumps(example, ensure_ascii=False), encoding="utf-8")
        catalog.append({"id": doc["slug"], "title": example["title"], "data_sha256": example["data_sha256"],
                        "counts": {k: sum(1 for r in fresh if r["result"] == k) for k in ("PROVED", "REFUTED", "UNKNOWN")}})
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    arms = []
    docs = summary["documents"]
    # Fixed by the protocol before the run: Gemini is not sent the prompt-injection copies, and
    # critics run on original articles only.  Rows with different coverage are not comparable.
    covered = {"gemini": [d for d in docs if not d.endswith(":injected")], "openrouter+critic": [d for d in docs if d.endswith(":original")]}
    covered.update({"union": covered["gemini"], "agree": covered["gemini"], "gemini+critic": covered["openrouter+critic"]})
    for arm, v in summary["arms"].items():
        c = v["classes"]
        arms.append({"label": LABELS.get(arm, arm), "arm": arm, "document_copies": len(covered.get(arm, docs)), "document_copies_total": len(docs),
                     "correct_verification": c.get("correct_verification", 0),
                     "correct_refutation": c.get("correct_refutation", 0),
                     "unsupported_positive": c.get("unsupported_positive", 0) + c.get("unannotated_proved", 0),
                     "unsupported_refutation": c.get("unsupported_refutation", 0) + c.get("wrong_refutation", 0) + c.get("unannotated_refuted", 0),
                     "abstained": c.get("abstained", 0) + c.get("conditional_only", 0),
                     # a model arm whose calls failed is published as failed, never as a row of zeros
                     "model_calls": v.get("model_calls", 0), "model_errors": v.get("model_errors", 0),
                     "complete": not v.get("model_errors", 0)})
    gold = summary["gold"]
    adv = json.loads(adversarial_path.read_text(encoding="utf-8")) if adversarial_path and adversarial_path.exists() else None
    notes = ("Counts are printed numbers, over original, planted-error and prompt-injection copies of the held-out articles. Rows that cover "
             "fewer copies cannot be compared with rows that cover more. “Wrongly” columns include every "
             "result on a number that had no gold label, before any hand adjudication. Gold labels are AI-assisted annotations, not expert "
             "review. In this evaluation a proved match was reliable when the proposer had not seen the data, and a refutation was often a wrong "
             "reading of the sentence, so read “refuted” as “this reading does not hold for this file”. "
             "The full report, receipts and replay instructions are in the PCS core repository under research/claimcheck_v1.")
    failed = [a["label"] for a in arms if not a["complete"]]
    if failed:
        notes += (" Arms marked incomplete had model calls that failed (provider quota or outage); a failed call contributes no proposal, "
                  "so those rows understate what the arm would do and are not a measurement of it: " + "; ".join(failed) + ".")
    if adv:
        a = sum(v["attempts"] for v in adv["A_deceptive_proposals"].values())
        ap = sum(v["PROVED"] + v["REFUTED"] for v in adv["A_deceptive_proposals"].values())
        c = adv["C_coincidence_search"]
        notes += (f" Adversarial suite: {a} deceptive proposals, {ap} accepted; coincidence search submitted {c['matching_readings_submitted']} "
                  f"numerically matching readings for {c['target_numbers']} false or underivable numbers, {c['readings_PROVED']} were proved.")
    benchmark = {
        "summary": (f"Frozen held-out evaluation on {len([d for d in summary['documents'] if d.endswith(':original')])} open-access articles with deposited data "
                    f"({gold['derivable_consistent']} true statements, {gold['derivable_inconsistent']} false ones including planted errors, "
                    f"{gold['not_derivable']} numbers that cannot be derived from the table). Every proposer feeds the same verifier."),
        "arms": arms, "notes": notes,
        "freezes": summary.get("freezes"),
    }
    cat = {"format": "pcs-claimcheck-site-examples-v1", "authority": "RESEARCH_ONLY_NOT_PCS_V06_AUTHORITY",
           "toolchain": "Lean 4.28.0", "checker_sha256": checker_sha256(),
           "recorded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "examples": catalog, "not_published_as_examples": skipped, "benchmark": benchmark}
    (site / "claim-check" / "examples.json").write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")
    loaders = "".join(f"  '{e['id']}': () => fetch('claim-check/examples/{e['id']}.json'),\n" for e in catalog)
    (site / "claim-check-examples.mjs").write_text(
        "// Generated by research/claimcheck_v1/tools/export_site.py in the PCS core repository; literal same-origin paths only.\n"
        "export const EXAMPLE_LOADERS = Object.freeze({\n" + loaders + "});\n", encoding="utf-8")
    return cat


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bundles", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--adversarial")
    ap.add_argument("--site", required=True)
    args = ap.parse_args(argv)
    cat = export(Path(args.bundles), Path(args.summary), Path(args.adversarial) if args.adversarial else None, Path(args.site))
    print(json.dumps({"examples": cat["examples"], "arms": cat["benchmark"]["arms"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
