"""CLadder natural-language LLM accuracy eval (compare to published SOTA).

This is the *LLM yes/no* protocol from Jin et al. (NeurIPS 2023), not the
structural oracle match in ``cladder_bridge.py``.

Free-tier courtesy: stratified sample, ≥10s between calls, capped requests.
API key via ``GEMINI_API_KEY`` only — never written to artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from research.proof_carrying_causal_reasoning_v1.external.cladder_bridge import (
    load_cladder_bundle,
    models_index,
)
from research.proof_carrying_causal_reasoning_v1.gemini_eval import generate


# Published numbers (CLadder v1.5 balanced) for side-by-side reporting.
PUBLISHED_SOTA = {
    "source": "Jin et al., CLadder, NeurIPS 2023, Table 2 (v1.5); CRAwDAD arXiv:2511.22854 Table 1",
    "dataset": "CLadder v1.5",
    "methods": {
        "random": {"overall": 49.27, "rung1": 50.28, "rung2": 48.40, "rung3": 49.12},
        "GPT-3.5": {"overall": 52.18, "rung1": 51.80, "rung2": 54.78, "rung3": 50.32},
        "GPT-4": {"overall": 62.03, "rung1": 63.01, "rung2": 62.82, "rung3": 60.55},
        "GPT-4 + CausalCoT": {
            "overall": 70.40,
            "rung1": 83.35,
            "rung2": 67.47,
            "rung3": 62.05,
        },
        "Qwen3 (CRAwDAD initial)": {
            "overall": 84.16,
            "rung1": 93.77,
            "rung2": 89.80,
            "rung3": 71.53,
        },
        "DeepSeek-R1 (CRAwDAD final)": {
            "overall": 87.45,
            "rung1": 94.62,
            "rung2": 89.06,
            "rung3": 80.04,
        },
        "Qwen3 (CRAwDAD final)": {
            "overall": 89.41,
            "rung1": 96.24,
            "rung2": 93.51,
            "rung3": 80.35,
        },
    },
    "notes": [
        "CRAwDAD numbers are on CLadder (paper Table 1); dual-agent debate, not single-call.",
        "This harness evaluates a single Gemini call with a yes/no instruction (vanilla).",
    ],
}


def build_prompt(question: dict, model: dict) -> str:
    background = (model or {}).get("background") or ""
    given = question.get("given_info") or ""
    q = question.get("question") or ""
    return (
        f"{background}\n\n{given}\n\n{q}\n\n"
        "Answer with a single word: yes or no."
    )


def parse_yes_no(text: str) -> Optional[str]:
    t = (text or "").strip().lower()
    # Prefer explicit final token.
    m = re.search(r"\b(yes|no)\b", t)
    if not m:
        return None
    # If both appear, take the last occurrence.
    hits = re.findall(r"\b(yes|no)\b", t)
    return hits[-1] if hits else None


def stratified_sample(
    questions: Sequence[dict],
    *,
    per_rung: int,
    seed: int = 20251118,
    exclude_graph_ids: Optional[set] = None,
) -> List[dict]:
    rng = random.Random(seed)
    by_rung: Dict[int, List[dict]] = defaultdict(list)
    exclude_graph_ids = exclude_graph_ids or set()
    for q in questions:
        meta = q.get("meta") or {}
        if meta.get("graph_id") in exclude_graph_ids:
            continue
        rung = int(meta.get("rung", -1))
        if rung in (1, 2, 3):
            by_rung[rung].append(q)
    out: List[dict] = []
    for rung in (1, 2, 3):
        pool = list(by_rung[rung])
        rng.shuffle(pool)
        out.extend(pool[:per_rung])
    rng.shuffle(out)
    return out


def evaluate_llm_sample(
    questions: Sequence[dict],
    models_by_id: Dict[int, dict],
    *,
    model_name: str,
    min_interval_sec: float,
    out_dir: Path,
) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)
    rows: List[dict] = []
    last = 0.0
    for i, q in enumerate(questions):
        wait = min_interval_sec - (time.monotonic() - last)
        if i > 0 and wait > 0:
            time.sleep(wait)
        mid = (q.get("meta") or {}).get("model_id")
        m = models_by_id.get(int(mid)) if mid is not None else None
        prompt = build_prompt(q, m or {})
        attempt = 0
        result: Dict[str, Any]
        while True:
            attempt += 1
            last = time.monotonic()
            result = generate(prompt, model=model_name, max_output_tokens=64)
            if result.get("ok"):
                break
            if result.get("status") in (429, 503) and attempt < 3:
                time.sleep(20.0 * attempt)
                continue
            break
        pred = parse_yes_no(result.get("text") or "")
        gold = str(q.get("answer") or "").strip().lower()
        correct = pred == gold if pred is not None else False
        meta = q.get("meta") or {}
        row = {
            "question_id": q.get("question_id"),
            "rung": meta.get("rung"),
            "query_type": meta.get("query_type"),
            "graph_id": meta.get("graph_id"),
            "gold": gold,
            "pred": pred,
            "correct": correct,
            "ok_call": bool(result.get("ok")),
            "status": result.get("status"),
            "usage": result.get("usage"),
            "attempt": attempt,
            "error": result.get("error"),
            "response_sha256": result.get("response_sha256"),
            "request_sha256": result.get("request_sha256"),
        }
        rows.append(row)
        (out_dir / f"response_{q.get('question_id')}.txt").write_text(
            result.get("text") or ""
        )
        (out_dir / f"call_{q.get('question_id')}.json").write_text(
            json.dumps(row, indent=2) + "\n"
        )

    return _summarize(rows, model_name=model_name, min_interval_sec=min_interval_sec)


def _summarize(
    rows: List[dict], *, model_name: str, min_interval_sec: float
) -> Dict[str, Any]:
    n = len(rows)
    n_correct = sum(1 for r in rows if r["correct"])
    n_parsed = sum(1 for r in rows if r["pred"] is not None)
    by_rung: Dict[str, Dict[str, int]] = {}
    by_qt: Dict[str, Dict[str, int]] = {}
    for r in rows:
        for key, bucket in (("rung", by_rung), ("query_type", by_qt)):
            k = str(r.get(key))
            b = bucket.setdefault(k, {"n": 0, "correct": 0})
            b["n"] += 1
            b["correct"] += int(r["correct"])
    def acc(b):
        return {k: {"n": v["n"], "correct": v["correct"], "accuracy": v["correct"] / v["n"] if v["n"] else 0.0} for k, v in sorted(b.items())}

    return {
        "kind": "cladder_llm_yes_no",
        "model": model_name,
        "min_interval_sec": min_interval_sec,
        "n": n,
        "n_parsed": n_parsed,
        "n_correct": n_correct,
        "accuracy": n_correct / n if n else 0.0,
        "parse_rate": n_parsed / n if n else 0.0,
        "by_rung": acc(by_rung),
        "by_query_type": acc(by_qt),
        "answer_balance_gold": dict(Counter(r["gold"] for r in rows)),
        "rows": rows,
        "published_sota_reference": PUBLISHED_SOTA,
        "claims": {
            "full_10112_eval": False,
            "frontier_sota": False,
            "api_key_not_stored": True,
            "rate_limited": True,
            "local_measurement_stratified_sample": True,
            "protocol": "vanilla yes/no single call (not CausalCoT / not multi-agent debate)",
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", default="gemini-3.5-flash-lite")
    p.add_argument("--per-rung", type=int, default=12, help="questions per rung (1/2/3)")
    p.add_argument("--seed", type=int, default=20251118)
    p.add_argument("--min-interval", type=float, default=12.0)
    args = p.parse_args(argv)

    questions, models, meta = load_cladder_bundle(args.data_dir)
    models_by_id = models_index(models)
    sample = stratified_sample(questions, per_rung=args.per_rung, seed=args.seed)
    # include arrowhead in LLM eval (NL protocol); exclusion was only for params CPT oracle
    payload = evaluate_llm_sample(
        sample,
        models_by_id,
        model_name=args.model,
        min_interval_sec=args.min_interval,
        out_dir=args.out,
    )
    payload["data"] = meta
    payload["sample"] = {
        "per_rung": args.per_rung,
        "seed": args.seed,
        "n": len(sample),
        "question_ids": [q.get("question_id") for q in sample],
    }
    # Comparison deltas vs published (percentage points on overall)
    our = 100.0 * payload["accuracy"]
    deltas = {
        name: round(our - info["overall"], 2)
        for name, info in PUBLISHED_SOTA["methods"].items()
    }
    payload["comparison"] = {
        "our_overall_pct": round(our, 2),
        "delta_pp_vs_published": deltas,
        "interpretation": (
            "Positive delta means this sample scored higher than the published "
            "full-set overall for that method — sample variance applies; this is "
            "not a claim of beating SOTA on the full 10k."
        ),
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    # scrub
    assert "AQ." not in text
    path = Path(args.out) / "cladder_llm_eval.json"
    path.write_text(text)
    (Path(args.out) / "cladder_llm_eval.sha256").write_text(
        hashlib.sha256(text.encode()).hexdigest() + "\n"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "accuracy": payload["accuracy"],
                "n": payload["n"],
                "by_rung": payload["by_rung"],
                "our_overall_pct": payload["comparison"]["our_overall_pct"],
                "delta_pp_vs_GPT-4": deltas["GPT-4"],
                "delta_pp_vs_CausalCoT": deltas["GPT-4 + CausalCoT"],
                "delta_pp_vs_Qwen3_CRAwDAD": deltas["Qwen3 (CRAwDAD final)"],
                "wrote": str(path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
