"""Post-run analysis of the frozen held-out results (reporting only; changes no result).

    python -m research.claimcheck_v1.tools.analyze --results benchmark/results/heldout --out benchmark/results/heldout/analysis.json

1. Rebuilds every arm's proposals (deterministic proposers and cached model responses) and reads
   their receipts back from the receipt cache.  No Lean run, no network: a missing receipt aborts.
2. Reports, per arm, how often a PROVED and a REFUTED were right, split by statistic.
3. Applies the hand adjudication of results on numbers that had no gold label
   (``ADJUDICATION.json``), keeping the automatic counts alongside.
4. POST HOC, exploratory: recomputes outcomes under two alternative refutation policies that were
   NOT part of the frozen system, to size a hypothesis for a future frozen evaluation:
     * ``no_bare_count_refutation``  a count of all rows (no column, no row condition) may confirm
       but may not refute;
     * ``corroborated_refutation``   a REFUTED stands only if, in the same sentence, a different
       number is PROVED under a reading on the same column and the same row conditions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..baseline import propose_rules, propose_search
from ..benchmark.harness import Document, Verifier, dedupe, score, spec_signature, summarise, token_outcomes
from ..benchmark.run import load_split
from ..propose import DEFAULT_MODELS, propose_with_model
from ..providers import Ledger
from ..grounding import sentence_window


class _CacheOnly(Verifier):
    def verify(self, doc, proposals, origin):
        out = []
        for p in proposals:
            path = self.cache_dir / f"{self._key(doc, p)[:40]}.json"
            if not path.exists():
                raise SystemExit(f"missing receipt for {doc.key}; run the benchmark first")
            out.append(json.loads(path.read_text(encoding="utf-8")))
        return out


def arm_proposals(doc: Document, results: Path) -> dict[str, list[dict]]:
    ledger = Ledger(max_calls={"gemini": 0, "openrouter": 0})
    arms = {"rules": dedupe(propose_rules(doc.text, doc.data, doc.manifest)),
            "search": dedupe(propose_search(doc.text, doc.data, doc.manifest))}
    for prov in ("gemini", "openrouter"):
        if doc.variant == "injected" and prov == "gemini":
            continue
        props, meta = propose_with_model(prov, DEFAULT_MODELS[prov], doc.text, doc.data, doc.manifest, allow_network=False,
                                         ledger=ledger, cache_dir=results / "model_responses")
        if not meta.get("error"):
            arms[prov] = dedupe(props)
    if "gemini" in arms and "openrouter" in arms:
        arms["union"] = dedupe(arms["gemini"] + arms["openrouter"])
    return arms


def _mask(text: str) -> str:
    return "".join("#" if ch.isdigit() else ch for ch in text)


def _same_scope(a: dict, b: dict) -> bool:
    key = lambda s: (s.get("column"), json.dumps(s.get("filter") or [], sort_keys=True))
    if key(a) == key(b):
        return True
    # a count has no column: it corroborates / is corroborated by a statistic over the same rows
    if "count" in (a["stat"], b["stat"]):
        return json.dumps(a.get("filter") or [], sort_keys=True) == json.dumps(b.get("filter") or [], sort_keys=True) and bool(a.get("filter"))
    return False


def apply_policy(doc: Document, receipts: list[dict], policy: str) -> list[dict]:
    if policy == "frozen":
        return receipts
    out = []
    proved = [r for r in receipts if r["result"] == "PROVED"]
    for r in receipts:
        if r["result"] == "REFUTED":
            spec = r["claim"]["spec"]
            demote = False
            if policy == "no_bare_count_refutation":
                demote = spec["stat"] == "count" and not spec.get("column") and not spec.get("filter")
            elif policy == "corroborated_refutation":
                rv = r["q2_correspondence"]["reported_value"]
                w = sentence_window(doc.text, rv["start"], rv["end"])
                demote = not any(
                    p["q2_correspondence"]["reported_value"]["start"] != rv["start"]
                    and w[0] <= p["q2_correspondence"]["reported_value"]["start"] < w[1]
                    and _same_scope(spec, p["claim"]["spec"]) for p in proved)
            if demote:
                r = dict(r, result="UNKNOWN", reason=f"posthoc_{policy}")
        out.append(r)
    return out


def analyse(split: str, results: Path) -> dict:
    verifier = _CacheOnly(results / "receipts")
    docs = load_split(split)
    adjudication = {}
    adj_path = results / "ADJUDICATION.json"
    if adj_path.exists():
        for item in json.loads(adj_path.read_text(encoding="utf-8"))["items"]:
            adjudication[(item["slug"], item["outcome"], item["stat"], _mask(item["sentence_fragment"]))] = item
    policies = ("frozen", "no_bare_count_refutation", "corroborated_refutation")
    table = {p: {} for p in policies}
    by_stat: dict = {}
    adjudicated: dict = {}
    for doc in docs:
        for arm, props in arm_proposals(doc, results).items():
            receipts = verifier.verify(doc, props, arm)
            for policy in policies:
                sc = score(doc, token_outcomes(doc, props, apply_policy(doc, receipts, policy)))
                table[policy].setdefault(arm, []).append(sc)
                if policy != "frozen":
                    continue
                labelled = {g["start"]: g for g in doc.gold}
                outcomes = token_outcomes(doc, props, receipts)
                for row in sc["rows"]:
                    if row["outcome"] in ("PROVED", "REFUTED"):
                        g = next(x for x in doc.gold if x["id"] == row["id"])
                        stat = outcomes[g["start"]]["spec"]["stat"]
                        ok = row["class"] in ("correct_verification", "correct_refutation")
                        c = by_stat.setdefault(arm, {}).setdefault(row["outcome"], {}).setdefault(stat, {"right": 0, "wrong": 0})
                        c["right" if ok else "wrong"] += 1
                for u in sc["unannotated"]:
                    c = by_stat.setdefault(arm, {}).setdefault(u["outcome"], {}).setdefault(u["spec"]["stat"], {"right": 0, "wrong": 0, "unlabelled": 0})
                    c["unlabelled"] = c.get("unlabelled", 0) + 1
                    # an adjudication applies to the same position in the same sentence (digits masked, so
                    # that it also applies to the planted-error copy of the document)
                    frag = _mask(doc.text[max(0, u["start"] - 45):u["start"] + 12])
                    item = adjudication.get((doc.slug, u["outcome"], u["spec"]["stat"], frag))
                    verdict = item["verdict"] if item else None
                    a = adjudicated.setdefault(arm, {"PROVED": {"faithful": 0, "not_faithful": 0, "not_adjudicated": 0},
                                                     "REFUTED": {"faithful": 0, "not_faithful": 0, "not_adjudicated": 0}})
                    a[u["outcome"]][verdict or "not_adjudicated"] += 1
    out = {"split": split, "policies": {p: {arm: summarise(scs) for arm, scs in arms.items()} for p, arms in table.items()},
           "frozen_by_statistic": by_stat, "unlabelled_results_after_hand_adjudication": adjudicated,
           "note": "Only the 'frozen' policy is a result of the frozen system. The other two are post hoc, exploratory and unvalidated."}
    # precision summaries
    prec = {}
    for arm, classes in out["policies"]["frozen"].items():
        adj = adjudicated.get(arm, {})
        cv, up = classes.get("correct_verification", 0), classes.get("unsupported_positive", 0)
        cr = classes.get("correct_refutation", 0)
        ur = classes.get("unsupported_refutation", 0) + classes.get("wrong_refutation", 0)
        un_p, un_r = classes.get("unannotated_proved", 0), classes.get("unannotated_refuted", 0)
        prec[arm] = {
            "PROVED_total": cv + up + un_p, "PROVED_matching_gold": cv,
            "PROVED_unlabelled_faithful_after_adjudication": adj.get("PROVED", {}).get("faithful", 0),
            "PROVED_unlabelled_not_faithful_after_adjudication": adj.get("PROVED", {}).get("not_faithful", 0),
            "PROVED_gold_unsupported": up,
            "REFUTED_total": cr + ur + un_r, "REFUTED_matching_gold": cr, "REFUTED_gold_unsupported": ur, "REFUTED_unlabelled": un_r,
        }
    out["frozen_precision"] = prec
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", default="heldout")
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = analyse(args.split, Path(args.results))
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for policy, arms in out["policies"].items():
        print("==", policy)
        for arm, classes in arms.items():
            print(f"  {arm:11s}", {k: v for k, v in classes.items() if k not in ("abstained", "correct_abstention")})
    print(json.dumps(out["frozen_precision"], indent=1))
    print(json.dumps(out["unlabelled_results_after_hand_adjudication"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
