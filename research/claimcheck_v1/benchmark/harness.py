"""Benchmark harness: documents, arms, verification cache and scoring.

Evaluation unit: one printed number (a token at a source offset) in one document.
Gold labels say, for selected tokens, whether the number is derivable from the document's data
table, under which typed reading(s), and whether the printed value is then right or wrong.

An arm is a way of producing untrusted proposals.  Every arm's proposals pass through the same
verifier (gates + Lean kernel).  Scoring never consults a model.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

from ..baseline import propose_rules, propose_search, sentences
from ..grounding import locate_token
from ..oracle import evaluate
from ..pipeline import verify_many
from ..spec import ClaimSpec, SpecError, canonical, sha256_hex, unit_factor

FAMILY = {"sd": "sd", "sd_sample": "sd", "sd_pop": "sd", "count": "count", "share": "share"}


class Document:
    def __init__(self, root: Path, variant: str = "original"):
        self.root, self.variant = root, variant
        self.slug = root.name
        meta = json.loads((root / "document.json").read_text(encoding="utf-8"))
        self.meta = meta
        name = "article.txt" if variant == "original" else f"article.{variant}.txt"
        self.text = (root / name).read_bytes().decode("utf-8")
        self.data = (root / meta["table"]).read_bytes()
        self.manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        gold_name = "gold.json" if variant == "original" else f"gold.{variant}.json"
        self.gold = json.loads((root / gold_name).read_text(encoding="utf-8"))["items"]
        for item in self.gold:
            item["start"], item["end"] = self._locate(item)

    @property
    def key(self) -> str:
        return f"{self.slug}:{self.variant}"

    def _locate(self, item: dict) -> tuple[int, int]:
        if "start" in item and "end" in item:        # variants carry explicit offsets
            printed = self.text[item["start"]:item["end"]].replace(",", "").replace("−", "-")
            if printed != item["token"].replace(",", ""):
                raise ValueError(f"{self.slug}/{item['id']}: token is not at the recorded offsets")
            return item["start"], item["end"]
        ctx = item["context"]
        pos = self.text.find(ctx)
        if pos == -1 or self.text.find(ctx, pos + 1) != -1:
            raise ValueError(f"{self.slug}/{item['id']}: context must occur exactly once")
        hits = locate_token(ctx, item["token"].replace(",", ""))
        which = item.get("occurrence", 0)
        if len(hits) <= which:
            raise ValueError(f"{self.slug}/{item['id']}: token {item['token']} not found in context")
        return pos + hits[which][0], pos + hits[which][1]


def spec_signature(doc: Document, spec_json: dict):
    """Extensional identity of a reading on this document's data: what it computes, not how it is written."""
    try:
        spec = ClaimSpec.from_json(spec_json, allow_unspecified_sd=True)
    except SpecError:
        return None
    family = FAMILY.get(spec.stat, spec.stat)
    data_unit = "fraction" if spec.stat == "share" else ((doc.manifest.get("columns") or {}).get(spec.column or "") or {}).get("unit")
    scale = unit_factor(data_unit, spec.reported_unit)
    if scale is None:
        return None
    from dataclasses import replace
    probe = replace(spec, stat="sd_sample") if spec.stat == "sd" else spec
    o = evaluate(doc.data, probe, tuple(doc.manifest.get("na_tokens") or ["", "NA"]), scale)
    if not o.defined:
        return (family, "undefined", o.reason)
    return (family, str(o.value), o.used, str(scale))


class Verifier:
    """Caches receipts by (document, proposal) so identical proposals from different arms cost one Lean run."""

    def __init__(self, cache_dir: Path, workers: int = 3, lean_timeout: int = 900):
        self.cache_dir, self.workers, self.lean_timeout = cache_dir, workers, lean_timeout
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.lean_seconds = 0.0   # wall time spent in verify_many (gates + kernel)
        self.fresh = 0
        self.hits = 0
        self.kernel_claims = 0
        self.batch_size = 16

    def _key(self, doc: Document, proposal: dict) -> str:
        return sha256_hex(canonical({"doc": doc.key, "text": sha256_hex(doc.text.encode()), "data": sha256_hex(doc.data),
                                     "manifest": doc.manifest, "proposal": proposal}))

    def verify(self, doc: Document, proposals: list[dict], origin: str) -> list[dict]:
        cleaned, keys, out = [], [], {}
        for proposal in proposals:
            clean = proposal      # passed to the verifier exactly as proposed: rejecting junk is its job
            key = self._key(doc, clean)
            cleaned.append(clean)
            keys.append(key)
            path = self.cache_dir / f"{key[:40]}.json"
            if path.exists():
                out[key] = json.loads(path.read_text(encoding="utf-8"))
                self.hits += 1
        todo = [(k, c) for k, c in zip(keys, cleaned) if k not in out]
        todo = list({k: (k, c) for k, c in todo}.values())
        if todo:
            start = time.monotonic()
            receipts = verify_many(
                [(k[:12], c, "benchmark") for k, c in todo], source_text=doc.text,
                source_meta={"name": doc.key, "license": doc.meta.get("article_license"), "citation": doc.meta.get("citation")},
                data=doc.data, manifest=doc.manifest, lean_timeout=self.lean_timeout, workers=self.workers,
                batch_size=self.batch_size, lean_when_ungrounded=False, kernel_if_only_cue_missing=True)
            self.lean_seconds += time.monotonic() - start
            for (k, _c), r in zip(todo, receipts):
                out[k] = r
                self.fresh += 1
                self.kernel_claims += sum(1 for v in r.get("q1_mathematics", {}).get("variants", []) if v.get("lean", {}).get("kernel_accepted"))
                (self.cache_dir / f"{k[:40]}.json").write_text(json.dumps(r, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return [out[k] for k in keys]


def effective_result(r: dict, policy: str) -> str:
    """The receipt's result, or (ablation only) what it would be without the statistic-wording gate."""
    if policy == "strict" or r["result"] != "UNKNOWN":
        return r["result"]
    q1 = r.get("q1_mathematics", {}).get("status")
    if r.get("reason") == "binding_not_grounded" and r.get("q2_correspondence", {}).get("grounded_except_statistic_wording") \
            and q1 in ("PROVED", "REFUTED"):
        return q1
    return "UNKNOWN"


def token_outcomes(doc: Document, proposals: list[dict], receipts: list[dict], policy: str = "strict") -> dict:
    """Collapse receipts to one outcome per printed number.

    If distinct grounded readings of the same number reach different verdicts, the outcome is
    UNKNOWN (conflicting readings): a system must not pick whichever reading happens to match.
    ``policy="no_cue_gate"`` is an ablation that ignores the statistic-wording gate.
    """
    by_token: dict[int, list] = {}
    for proposal, r in zip(proposals, receipts):
        rv = r.get("q2_correspondence", {}).get("reported_value")
        if not rv:
            continue
        by_token.setdefault(rv["start"], []).append((proposal, dict(r, result=effective_result(r, policy))))
    out = {}
    for start, pairs in by_token.items():
        decided = [(p, r) for p, r in pairs if r["result"] in ("PROVED", "REFUTED")]
        sigs = {}
        for p, r in decided:
            sigs.setdefault(spec_signature(doc, r["claim"]["spec"]), (p, r))
        verdicts = {r["result"] for _, r in sigs.values()}
        if len(verdicts) == 1:
            p, r = next(iter(sigs.values()))
            entry = {"result": r["result"], "spec": r["claim"]["spec"], "readings": len(sigs), "receipt": r["receipt_sha256"]}
            if len(sigs) > 1:
                entry["note"] = "several distinct readings, same verdict"
        elif len(verdicts) > 1:
            entry = {"result": "UNKNOWN", "reason": "conflicting_readings", "readings": len(sigs)}
        else:
            reasons = sorted({r["reason"] for _, r in pairs})
            entry = {"result": "UNKNOWN", "reason": "+".join(reasons), "readings": 0}
            cond = [r for _, r in pairs if r["reason"] == "ambiguous_convention"]
            if cond:
                entry["conditional"] = True
                entry["spec"] = cond[0]["claim"]["spec"]
            math = sorted({r.get("q1_mathematics", {}).get("status") for _, r in pairs if r["reason"] == "binding_not_grounded"})
            if math:
                entry["ungrounded_math"] = math
        out[start] = entry
    return out


def score(doc: Document, outcomes: dict) -> dict:
    """Compare per-token outcomes with gold.  Tokens without a gold label count as *unannotated*."""
    rows = []
    labelled = {item["start"]: item for item in doc.gold}
    for item in doc.gold:
        o = outcomes.get(item["start"], {"result": "UNKNOWN", "reason": "no_proposal", "readings": 0})
        gold_sigs = {spec_signature(doc, g) for g in item.get("gold", [])}
        match = o.get("spec") is not None and spec_signature(doc, o["spec"]) in gold_sigs
        kind, truth = item["kind"], item.get("truth")
        if kind == "derivable" and truth == "consistent":
            if o["result"] == "PROVED":
                cls = "correct_verification" if match else "unsupported_positive"
            elif o["result"] == "REFUTED":
                cls = "wrong_refutation" if match else "unsupported_refutation"
            else:
                cls = "conditional_only" if (o.get("conditional") and match) else "abstained"
        elif kind == "derivable" and truth == "inconsistent":
            if o["result"] == "REFUTED":
                cls = "correct_refutation" if match else "unsupported_refutation"
            elif o["result"] == "PROVED":
                cls = "unsupported_positive"
            else:
                cls = "abstained"
        elif kind == "derivable" and truth == "conditional":
            # true only under one SD convention: the right answer is a conditional result, never PROVED
            if o["result"] == "PROVED":
                cls = "unsupported_positive"
            elif o["result"] == "REFUTED":
                cls = "unsupported_refutation"
            else:
                cls = "correct_conditional" if (o.get("conditional") and match) else "abstained"
        else:  # not_derivable
            cls = {"PROVED": "unsupported_positive", "REFUTED": "unsupported_refutation"}.get(o["result"], "correct_abstention")
        rows.append({"id": item["id"], "kind": kind, "truth": truth, "token": item["token"], "outcome": o["result"],
                     "reason": o.get("reason"), "class": cls, "binding_matches_gold": bool(match)})
    extra = []
    for start, o in sorted(outcomes.items()):
        if start not in labelled and o["result"] in ("PROVED", "REFUTED"):
            extra.append({"start": start, "printed": doc.text[start:start + 16].split()[0] if doc.text[start:start + 16].split() else "",
                          "outcome": o["result"], "spec": o.get("spec"), "class": "unannotated_" + o["result"].lower()})
    return {"rows": rows, "unannotated": extra}


def numeric_token_count(doc: Document) -> int:
    from ..baseline import NUMBER
    return sum(1 for _s, sent in sentences(doc.text) for _m in NUMBER.finditer(sent))


def dedupe(proposals: list[dict]) -> list[dict]:
    seen, out = set(), []
    for p in proposals:
        k = canonical({"q": " ".join(str(p.get("quote", "")).split()), "s": p.get("spec")})
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def summarise(scored: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for s in scored:
        for row in s["rows"]:
            counts[row["class"]] = counts.get(row["class"], 0) + 1
        for row in s["unannotated"]:
            counts[row["class"]] = counts.get(row["class"], 0) + 1
    return dict(sorted(counts.items()))


__all__ = ["Document", "Verifier", "token_outcomes", "score", "summarise", "dedupe", "spec_signature",
           "propose_rules", "propose_search", "numeric_token_count", "Fraction", "time"]
