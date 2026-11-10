"""Run the ClaimCheck benchmark arms on one split and write complete, replayable results.

    python -m research.claimcheck_v1.benchmark.run --split dev --out results/dev [--allow-network]

Arms (each is only a way of producing untrusted proposals; all share one verifier):

  rules               cue-word rules, no model, never looks at data values
  search              exhaustive data-matching search, no model (classic symbolic baseline)
  gemini / openrouter one model reads the whole document
  union               both models' proposals together
  agree               only readings that both models proposed independently
  gemini+critic       Gemini's proposals, minus those the OpenRouter model calls unfaithful
  openrouter+critic   the reverse
  cascade             rules first; Gemini is shown only sentences whose numbers the rules left unresolved

Model agreement, critic approval and model confidence are never verification authority: they
only decide which proposals are *sent* to the verifier or dropped before it.  Without
--allow-network the model arms run from cached responses only and fail closed if any is missing.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ..baseline import NUMBER, propose_rules, propose_search, sentences
from ..propose import DEFAULT_MODELS, critique, data_dictionary, propose_with_model, proposer_prompt, to_proposals, SYSTEM
from ..providers import Ledger, ProviderError, complete, extract_json
from .harness import Document, Verifier, dedupe, numeric_token_count, score, spec_signature, summarise, token_outcomes

HERE = Path(__file__).resolve().parent
MODEL_ARMS = ("gemini", "openrouter")


def load_split(split: str) -> list[Document]:
    docs = []
    for root in sorted((HERE / split).iterdir()):
        if not (root / "document.json").exists():
            continue
        docs.append(Document(root, "original"))
        for extra in sorted(root.glob("article.*.txt")):
            docs.append(Document(root, extra.name.split(".")[1]))
    return docs


def _token_starts(doc: Document, receipts: list[dict]) -> list:
    return [r.get("q2_correspondence", {}).get("reported_value", {}).get("start") for r in receipts]


def residual_text(doc: Document, resolved_starts: set[int]) -> str:
    """Sentences that contain at least one number the first stage did not resolve."""
    keep = []
    for start, sent in sentences(doc.text):
        if sent.startswith(("TITLE:", "SECTION:")):
            continue
        nums = [start + m.start() for m in NUMBER.finditer(sent)]
        if nums and any(n not in resolved_starts for n in nums):
            keep.append(sent)
    return "\n\n".join(keep) + "\n"


def run(split: str, out: Path, *, allow_network: bool, workers: int, max_gemini: int, max_openrouter: int,
        models: dict | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    models = dict(DEFAULT_MODELS, **(models or {}))
    ledger = Ledger(max_calls={"gemini": max_gemini, "openrouter": max_openrouter})
    cache = out / "model_responses"
    verifier = Verifier(out / "receipts", workers=workers)
    docs = load_split(split)
    per_doc, arm_scores, arm_cost, arm_ablation = [], {}, {}, {}
    t_start = time.monotonic()

    def record(doc, arm, proposals, cost):
        t0 = time.monotonic()
        before = verifier.kernel_claims
        receipts = verifier.verify(doc, proposals, arm)
        outcomes = token_outcomes(doc, proposals, receipts)
        sc = score(doc, outcomes)
        arm_scores.setdefault(arm, []).append(sc)
        ablation = score(doc, token_outcomes(doc, proposals, receipts, policy="no_cue_gate"))
        arm_ablation.setdefault(arm, []).append(ablation)
        c = arm_cost.setdefault(arm, {"proposals": 0, "verify_seconds": 0.0, "kernel_claims_new": 0, "model_calls": 0,
                                      "prompt_tokens": 0, "output_tokens": 0, "model_errors": 0})
        c["proposals"] += len(proposals)
        c["verify_seconds"] += time.monotonic() - t0
        c["kernel_claims_new"] += verifier.kernel_claims - before
        for k in ("model_calls", "prompt_tokens", "output_tokens", "model_errors"):
            c[k] += cost.get(k, 0)
        results = {r["receipt_sha256"]: r["result"] for r in receipts}
        return {"arm": arm, "proposals": len(proposals), "receipt_results": sorted(results.values()),
                "score_without_statistic_wording_gate": ablation,
                "token_outcomes": {str(k): v for k, v in sorted(outcomes.items())}, "score": sc, "cost": cost}, receipts, outcomes

    for doc in docs:
        entry = {"doc": doc.key, "numeric_tokens": numeric_token_count(doc), "gold_items": len(doc.gold), "arms": []}
        # ---- deterministic arms
        rules = dedupe(propose_rules(doc.text, doc.data, doc.manifest))
        e_rules, rec_rules, out_rules = record(doc, "rules", rules, {})
        entry["arms"].append(e_rules)
        search = dedupe(propose_search(doc.text, doc.data, doc.manifest))
        entry["arms"].append(record(doc, "search", search, {})[0])
        # ---- model arms
        model_props, model_meta = {}, {}
        for prov in MODEL_ARMS:
            props, meta = propose_with_model(prov, models[prov], doc.text, doc.data, doc.manifest, allow_network=allow_network,
                                             ledger=ledger, cache_dir=cache)
            props = dedupe(props)
            usage = meta.get("usage") or {}
            cost = {"model_calls": 1, "prompt_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
                    "model_errors": 1 if meta.get("error") else 0, "meta": {k: v for k, v in meta.items() if k != "usage"}}
            model_props[prov], model_meta[prov] = props, cost
            entry["arms"].append(record(doc, prov, props, cost)[0])
        both_cost = {k: sum(model_meta[p][k] for p in MODEL_ARMS) for k in ("model_calls", "prompt_tokens", "output_tokens", "model_errors")}
        union = dedupe(model_props["gemini"] + model_props["openrouter"])
        entry["arms"].append(record(doc, "union", union, both_cost)[0])
        # agreement: same token, extensionally the same reading, proposed by both
        def keyed(props):
            recs = verifier.verify(doc, props, "key")
            out = {}
            for p, r, s in zip(props, recs, _token_starts(doc, recs)):
                if s is not None and "claim" in r:
                    out.setdefault((s, spec_signature(doc, r["claim"]["spec"])), p)
            return out
        kg, ko = keyed(model_props["gemini"]), keyed(model_props["openrouter"])
        agree = [kg[k] for k in kg if k in ko]
        entry["arms"].append(record(doc, "agree", agree, both_cost)[0])
        # critics
        for prov, critic in (("gemini", "openrouter"), ("openrouter", "gemini")):
            props = model_props[prov]
            items = [{"id": i, "quote": p["quote"], "reading": p["spec"]} for i, p in enumerate(props)]
            reviews, cmeta = critique(critic, models[critic], doc.text, doc.data, doc.manifest, items,
                                      allow_network=allow_network, ledger=ledger, cache_dir=cache)
            kept = [p for i, p in enumerate(props) if reviews.get(str(i), {}).get("faithful", True)]
            cu = cmeta.get("usage") or {}
            cost = {"model_calls": model_meta[prov]["model_calls"] + (1 if items else 0),
                    "prompt_tokens": model_meta[prov]["prompt_tokens"] + cu.get("prompt_tokens", 0),
                    "output_tokens": model_meta[prov]["output_tokens"] + cu.get("output_tokens", 0),
                    "model_errors": model_meta[prov]["model_errors"] + (1 if cmeta.get("error") else 0),
                    "critic": {"reviews": len(reviews), "dropped": len(props) - len(kept), "error": cmeta.get("error"),
                               "flagged": [{"quote": props[int(i)]["quote"][:160], "spec": props[int(i)]["spec"], "problem": r["problem"]}
                                           for i, r in reviews.items() if not r["faithful"] and int(i) < len(props)]}}
            entry["arms"].append(record(doc, f"{prov}+critic", kept, cost)[0])
        # cascade: rules first, then Gemini on the residual sentences only
        resolved = {s for s, o in out_rules.items() if o["result"] in ("PROVED", "REFUTED")}
        residual = residual_text(doc, resolved)
        prompt = proposer_prompt(residual, data_dictionary(doc.data, doc.manifest))
        try:
            rec = complete("gemini", models["gemini"], prompt, system=SYSTEM, ledger=ledger, cache_dir=cache, allow_network=allow_network)
            extra, _dropped = to_proposals(extract_json(rec["text"]))
            usage = rec.get("usage") or {}
            cost = {"model_calls": 1, "prompt_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("output_tokens", 0), "model_errors": 0}
        except ProviderError as exc:
            extra, cost = [], {"model_calls": 1, "prompt_tokens": 0, "output_tokens": 0, "model_errors": 1, "error": str(exc)}
        cost["residual_chars"] = len(residual)
        cost["full_chars"] = len(doc.text)
        entry["arms"].append(record(doc, "cascade", dedupe(rules + extra), cost)[0])
        per_doc.append(entry)
        (out / "per_document.json").write_text(json.dumps(per_doc, indent=1, ensure_ascii=False), encoding="utf-8")

    summary = {
        "split": split, "documents": [d.key for d in docs], "models": models,
        "arms": {arm: {"classes": summarise(scs), "classes_without_statistic_wording_gate": summarise(arm_ablation[arm]),
                       **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in arm_cost[arm].items()}}
                 for arm, scs in arm_scores.items()},
        "gold": {"items": sum(len(d.gold) for d in docs),
                 "derivable_consistent": sum(1 for d in docs for g in d.gold if g["kind"] == "derivable" and g.get("truth") == "consistent"),
                 "derivable_inconsistent": sum(1 for d in docs for g in d.gold if g["kind"] == "derivable" and g.get("truth") == "inconsistent"),
                 "derivable_conditional": sum(1 for d in docs for g in d.gold if g["kind"] == "derivable" and g.get("truth") == "conditional"),
                 "not_derivable": sum(1 for d in docs for g in d.gold if g["kind"] == "not_derivable"),
                 "numeric_tokens_in_documents": sum(numeric_token_count(d) for d in docs)},
        "ledger": ledger.to_json(),
        "verifier": {"fresh_receipts": verifier.fresh, "cache_hits": verifier.hits, "kernel_checked_claims": verifier.kernel_claims,
                     "verify_wall_seconds": round(verifier.lean_seconds, 1)},
        "wall_seconds": round(time.monotonic() - t_start, 1),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-network", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-gemini-calls", type=int, default=80)
    ap.add_argument("--max-openrouter-calls", type=int, default=40)
    args = ap.parse_args(argv)
    summary = run(args.split, Path(args.out), allow_network=args.allow_network, workers=args.workers,
                  max_gemini=args.max_gemini_calls, max_openrouter=args.max_openrouter_calls)
    print(json.dumps({k: summary[k] for k in ("arms", "gold", "ledger", "verifier", "wall_seconds")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
