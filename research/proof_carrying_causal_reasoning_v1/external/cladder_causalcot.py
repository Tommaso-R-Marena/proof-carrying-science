"""CausalCoT + critic debate on CLadder NL with a strong Gemini model.

Faithful multi-step protocol adapted from Jin et al. (CLadder / CausalCoT),
plus a short critic pass (CRAwDAD-inspired) and optional PCCR numeric assist
when the model emits a parseable estimand JSON block.

API key via ``GEMINI_API_KEY`` only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from research.proof_carrying_causal_reasoning_v1.external.cladder_bridge import (
    load_cladder_bundle,
    models_index,
)
from research.proof_carrying_causal_reasoning_v1.external.cladder_llm_eval import (
    PUBLISHED_SOTA,
    parse_yes_no as _parse_yes_no_basic,
    stratified_sample,
)
from research.proof_carrying_causal_reasoning_v1.gemini_eval import generate_text


def parse_yes_no(text: str) -> Optional[str]:
    t = (text or "").strip()
    m = re.search(r"FINAL:\s*(yes|no)\b", t, flags=re.I)
    if m:
        return m.group(1).lower()
    jm = re.search(
        r"\{[^{}]*\"answer\"\s*:\s*\"(yes|no)\"[^{}]*\}", t, flags=re.I
    )
    if jm:
        return jm.group(1).lower()
    return _parse_yes_no_basic(t)


QUERY_TYPES = [
    "marginal",
    "correlation",
    "ate",
    "ett",
    "nde",
    "nie",
    "backadj",
    "det-counterfactual",
    "exp_away",
    "collider_bias",
]


def _var_notions(model: dict) -> str:
    vm = (model or {}).get("variable_mapping") or {}
    parts = []
    for k, v in vm.items():
        if str(k).endswith("name"):
            sym = str(k)[: -len("name")]
            parts.append(f'Use "{sym}" to denote "{v}".')
    return " ".join(parts)


def build_causalcot_prompt(question: dict, model: dict) -> str:
    background = (model or {}).get("background") or ""
    given = question.get("given_info") or ""
    q = question.get("question") or ""
    notions = _var_notions(model)
    qt_list = ", ".join(f'"{t}"' for t in QUERY_TYPES)
    return f"""{background}

{given}

{q}

{notions}

Hint: answer by following these subquestions:

Step 1) Extract the causal graph: list edges as "A -> B", comma-separated.

Step 2) Identify the query type: choose one of {qt_list}.

Step 3) Translate the query to a formal estimand (use do(·) or counterfactuals).

Step 4) Collect available probabilities from the text as P(...)=... ; ...

Step 5) Solve the estimand with causal inference (do-calculus / counterfactuals / probability).

Step 6) On the last line, write exactly: FINAL: yes   or   FINAL: no
"""


def build_critic_prompt(question: dict, model: dict, draft: str) -> str:
    background = (model or {}).get("background") or ""
    given = question.get("given_info") or ""
    q = question.get("question") or ""
    return f"""You are a critical causal-inference reviewer.

Context:
{background}

{given}

Question: {q}

Draft solution:
{draft}

Check for: wrong causal graph, wrong rung/query type, arithmetic errors,
confusing correlation with intervention, and polarity mistakes (increase vs decrease).
Then on the last line write exactly: FINAL: yes   or   FINAL: no
"""


def _call(prompt: str, model: str, max_tokens: int, min_interval: float, last: list) -> dict:
    wait = min_interval - (time.monotonic() - last[0])
    if last[0] > 0 and wait > 0:
        time.sleep(wait)
    attempt = 0
    while True:
        attempt += 1
        last[0] = time.monotonic()
        result = generate_text(
            prompt, model=model, max_output_tokens=max_tokens, timeout_sec=240
        )
        if result.get("ok"):
            result["attempt"] = attempt
            return result
        if result.get("status") in (429, 503, 598, 599) and attempt < 6:
            time.sleep(20.0 * attempt)
            continue
        result["attempt"] = attempt
        return result


def evaluate_causalcot_sample(
    questions: Sequence[dict],
    models_by_id: Dict[int, dict],
    *,
    model_name: str,
    critic_model: Optional[str],
    min_interval_sec: float,
    out_dir: Path,
) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)
    last = [0.0]
    rows: List[dict] = []
    for q in questions:
        mid = (q.get("meta") or {}).get("model_id")
        m = models_by_id.get(int(mid)) if mid is not None else None
        prompt = build_causalcot_prompt(q, m or {})
        r1 = _call(prompt, model_name, 8192, min_interval_sec, last)
        draft = r1.get("text") or ""
        pred = parse_yes_no(draft)
        critic_text = ""
        if critic_model and draft:
            r2 = _call(
                build_critic_prompt(q, m or {}, draft),
                critic_model,
                512,
                min_interval_sec,
                last,
            )
            critic_text = r2.get("text") or ""
            cpred = parse_yes_no(critic_text)
            if cpred is not None:
                pred = cpred
        gold = str(q.get("answer") or "").lower()
        meta = q.get("meta") or {}
        row = {
            "question_id": q.get("question_id"),
            "rung": meta.get("rung"),
            "query_type": meta.get("query_type"),
            "gold": gold,
            "pred": pred,
            "correct": pred == gold if pred is not None else False,
            "draft_sha256": r1.get("response_sha256"),
            "ok_call": bool(r1.get("ok")),
            "status": r1.get("status"),
            "usage": r1.get("usage"),
        }
        rows.append(row)
        (out_dir / f"draft_{q.get('question_id')}.txt").write_text(draft)
        if critic_text:
            (out_dir / f"critic_{q.get('question_id')}.txt").write_text(critic_text)
        (out_dir / f"call_{q.get('question_id')}.json").write_text(
            json.dumps(row, indent=2) + "\n"
        )

    n = len(rows)
    n_ok = sum(1 for r in rows if r["correct"])
    by_rung: Dict[str, Dict[str, int]] = {}
    for r in rows:
        b = by_rung.setdefault(str(r["rung"]), {"n": 0, "correct": 0})
        b["n"] += 1
        b["correct"] += int(r["correct"])
    return {
        "kind": "cladder_causalcot_critic",
        "model": model_name,
        "critic_model": critic_model,
        "n": n,
        "n_correct": n_ok,
        "accuracy": n_ok / n if n else 0.0,
        "by_rung": {
            k: {
                "n": v["n"],
                "correct": v["correct"],
                "accuracy": v["correct"] / v["n"] if v["n"] else 0.0,
            }
            for k, v in sorted(by_rung.items())
        },
        "rows": rows,
        "published_sota_reference": PUBLISHED_SOTA,
        "claims": {
            "full_10112_eval": False,
            "protocol": "CausalCoT multi-step + optional critic (CRAwDAD-inspired)",
            "api_key_not_stored": True,
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", default="gemini-3.5-flash")
    p.add_argument("--critic-model", default="gemini-3.5-flash")
    p.add_argument("--no-critic", action="store_true")
    p.add_argument("--per-rung", type=int, default=12)
    p.add_argument("--seed", type=int, default=20251118)
    p.add_argument("--min-interval", type=float, default=12.0)
    args = p.parse_args(argv)

    questions, models, meta = load_cladder_bundle(args.data_dir)
    sample = stratified_sample(questions, per_rung=args.per_rung, seed=args.seed)
    critic = None if args.no_critic else args.critic_model
    payload = evaluate_causalcot_sample(
        sample,
        models_index(models),
        model_name=args.model,
        critic_model=critic,
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
    our = 100.0 * payload["accuracy"]
    payload["comparison"] = {
        "our_overall_pct": round(our, 2),
        "delta_pp_vs_published": {
            name: round(our - info["overall"], 2)
            for name, info in PUBLISHED_SOTA["methods"].items()
        },
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    assert "AQ." not in text
    path = Path(args.out) / "cladder_causalcot_eval.json"
    path.write_text(text)
    (Path(args.out) / "cladder_causalcot_eval.sha256").write_text(
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
                "delta_pp_vs_Qwen3_CRAwDAD": payload["comparison"][
                    "delta_pp_vs_published"
                ]["Qwen3 (CRAwDAD final)"],
                "wrote": str(path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
