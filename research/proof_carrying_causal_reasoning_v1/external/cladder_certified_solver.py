"""Protocol C: CLadder oracle-assisted generator regression.

The predictor consumes generator slots and may use published ground truth,
including direct counterfactual answer bits. See blind_eval for protocols A/B.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from research.proof_carrying_causal_reasoning_v1.external.cladder_bridge import (
    DEFAULT_EXCLUDE_GRAPHS,
    compute_ate,
    compute_correlation_diff,
    compute_ett,
    compute_marginal,
    compute_nde_nie_mediation,
    load_cladder_bundle,
    models_index,
    scm_from_cladder_params,
)

def _yn(code: int) -> str:
    return "yes" if int(code) > 0 else "no"


def _sign_effect(value: float, *, eps: float = 0.005) -> Optional[int]:
    if abs(value) < eps:
        return None
    return 1 if value > 0 else -1


def _ate_like_code(effect: float, polarity: bool, result: bool = True) -> int:
    sign = _sign_effect(effect)
    if sign is None:
        return -1
    return sign * ((-1) ** (1 - int(result) + 1 - int(polarity)))


def _ett_code(effect: float, polarity: bool, result: bool = True) -> int:
    # Extra leading 1 vs ATE (CLadder ett.py).
    sign = _sign_effect(effect)
    if sign is None:
        return -1
    return sign * ((-1) ** (1 + 1 - int(result) + 1 - int(polarity)))


def _marginal_code(p_y1: float, polarity: bool, treated: bool) -> int:
    slb = 2.0 * p_y1 - 1.0
    sign = _sign_effect(slb, eps=1e-12)
    if sign is None or abs(p_y1) < 0.005:
        return -1
    return sign * ((-1) ** (1 - int(polarity) + 1 - int(treated)))


def _correlation_code(
    corr: float, polarity: bool, treated: bool, result: bool = True
) -> int:
    sign = _sign_effect(corr)
    if sign is None:
        return -1
    return sign * (
        (-1) ** (1 - int(polarity) + 1 - int(treated) + 1 - int(result))
    )


def _mediation_code(effect: float, polarity: bool) -> int:
    sign = _sign_effect(effect)
    if sign is None:
        return -1
    return sign * ((-1) ** (1 - int(polarity)))


def _exp_away_code(effect: float, polarity: bool, result: bool) -> int:
    base = 0 if effect == 0 else (1 if effect > 0 else -1)
    return base * ((-1) ** (int(polarity) ^ int(result)))


def pccr_estimand(
    model: Mapping[str, Any], query_type: str
) -> Tuple[Optional[float], str]:
    """Return (estimand, source) using PCCR when possible."""
    structure = str(model.get("structure") or "")
    try:
        scm = scm_from_cladder_params(structure, model["params"])
    except Exception as exc:  # noqa: BLE001
        return None, f"scm_error:{exc}"
    try:
        if query_type == "ate":
            return float(compute_ate(scm)), "pccr_ate"
        if query_type == "ett":
            return float(compute_ett(scm)), "pccr_ett"
        if query_type == "marginal":
            return float(compute_marginal(scm)), "pccr_marginal"
        if query_type == "correlation":
            return float(compute_correlation_diff(scm)), "pccr_correlation"
        if query_type in {"nde", "nie"}:
            if structure != "X->V2,X->Y,V2->Y":
                return None, "unsupported_mediation_graph"
            nde, nie = compute_nde_nie_mediation(scm)
            return float(nde if query_type == "nde" else nie), f"pccr_{query_type}"
        if query_type == "exp_away":
            # Fall back to meta GT for exp_away (requires collider conditioning
            # not yet in the minimal FloatSCM API); still certificate via GT pin.
            return None, "exp_away_needs_meta"
    except Exception as exc:  # noqa: BLE001
        return None, f"estimand_error:{exc}"
    return None, "unsupported_query"


def solve_question(
    question: Mapping[str, Any],
    model: Optional[Mapping[str, Any]],
    *,
    allow_meta_groundtruth_fallback: bool = True,
) -> Dict[str, Any]:
    meta = question.get("meta") or {}
    qt = str(meta.get("query_type") or "")
    polarity = meta.get("polarity")
    treated = meta.get("treated")
    result = meta.get("result")
    if result is None:
        result = True

    pred: Optional[str] = None
    source = "unsolved"
    effect: Optional[float] = None

    # --- structural / linguistic special cases ---
    if qt == "det-counterfactual":
        gt = meta.get("groundtruth")
        pred = "yes" if int(gt) == 1 else "no"
        source = "det_cf_groundtruth_bit"
    elif qt == "collider_bias":
        # CLadder: answer = (-1)**polarity  (treatment never affects via collider)
        pred = _yn((-1) ** int(bool(polarity)))
        source = "collider_bias_polarity_rule"
    elif qt == "backadj":
        flipped = bool(meta.get("flipped"))
        if "flipped" not in meta:
            gt_set = set(meta.get("groundtruth") or [])
            gi = meta.get("given_info") or [[], []]
            flipped = set(gi[0]) != gt_set
        pred = _yn(1 if (bool(polarity) ^ flipped) else -1)
        source = "backadj_polarity_flipped"
    else:
        effect_source = "none"
        pccr_val: Optional[float] = None
        if model is not None and model.get("equation_type") == "bernoulli":
            pccr_val, effect_source = pccr_estimand(model, qt)
            effect = pccr_val
        meta_gt = meta.get("groundtruth")
        # CLadder's serialized Bernoulli params sometimes disagree with the
        # live-model groundtruth used to label questions (esp. marginal P(Y)
        # and arrowhead). Prefer meta GT for the decision when they diverge.
        if (
            allow_meta_groundtruth_fallback
            and isinstance(meta_gt, (int, float))
            and (
                effect is None
                or (
                    pccr_val is not None
                    and abs(float(pccr_val) - float(meta_gt)) > 1e-3
                )
            )
        ):
            effect = float(meta_gt)
            effect_source = (
                "meta_groundtruth_fallback"
                if pccr_val is None
                else f"meta_gt_over_pccr_delta:{abs(float(pccr_val) - float(meta_gt)):.4g}"
            )

        if effect is not None and polarity is not None:
            if qt == "ate":
                # CLadder stores treated-specific ate_bounds as groundtruth.
                # When using PCCR compute_ate (always do(X=1)-do(X=0)), flip if
                # treated is False.
                adj = effect
                if effect_source == "pccr_ate" and treated is False:
                    adj = -effect
                pred = _yn(_ate_like_code(adj, bool(polarity), bool(result)))
                source = f"ate:{effect_source}"
            elif qt == "ett":
                adj = effect
                if effect_source == "pccr_ett" and treated is False:
                    adj = -effect
                pred = _yn(_ett_code(adj, bool(polarity), bool(result)))
                source = f"ett:{effect_source}"
            elif qt == "marginal":
                pred = _yn(
                    _marginal_code(effect, bool(polarity), bool(treated if treated is not None else True))
                )
                source = f"marginal:{effect_source}"
            elif qt == "correlation":
                adj = effect
                # correlation formula uses treated/result on the observed contrast
                if effect_source.startswith("pccr") and treated is False:
                    # treated=False questions flip interpretation via formula's treated bit
                    pass
                pred = _yn(
                    _correlation_code(
                        adj, bool(polarity), bool(treated if treated is not None else True), bool(result)
                    )
                )
                source = f"correlation:{effect_source}"
            elif qt in {"nde", "nie"}:
                pred = _yn(_mediation_code(effect, bool(polarity)))
                source = f"{qt}:{effect_source}"
            elif qt == "exp_away":
                pred = _yn(_exp_away_code(effect, bool(polarity), bool(result)))
                source = f"exp_away:{effect_source}"
            else:
                source = f"no_rule:{qt}"

    return {
        "question_id": question.get("question_id"),
        "query_type": qt,
        "rung": meta.get("rung"),
        "graph_id": meta.get("graph_id") or (model or {}).get("graph_id"),
        "pred": pred,
        "source": source,
        "effect": effect,
    }


def _information_source(source: str) -> str:
    if source == "det_cf_groundtruth_bit":
        return "direct_counterfactual_bit"
    if "meta_gt_over_pccr_delta" in source:
        return "override_computed"
    if "meta_groundtruth_fallback" in source:
        return "missing_effect_fallback"
    if source == "backadj_polarity_flipped":
        return "backadj_slot_or_gold_set"
    if source == "collider_bias_polarity_rule":
        return "collider_slot_rule"
    if ":pccr_" in source:
        return "scm_with_generator_slots"
    return "other"


def evaluate_certified(
    questions: Sequence[Mapping[str, Any]],
    models_by_id: Mapping[int, Mapping[str, Any]],
    *,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    rows: List[dict] = []
    by_qt: Dict[str, Dict[str, int]] = defaultdict(lambda: {"n": 0, "correct": 0})
    by_rung: Dict[str, Dict[str, int]] = defaultdict(lambda: {"n": 0, "correct": 0})
    by_source: Counter = Counter()
    for i, q in enumerate(questions):
        if limit is not None and i >= limit:
            break
        mid = (q.get("meta") or {}).get("model_id")
        model = models_by_id.get(int(mid)) if mid is not None else None
        row = solve_question(q, model)
        row["gold"] = str(q["answer"]).lower()
        row["correct"] = row["pred"] == row["gold"]
        rows.append(row)
        by_qt[str(row["query_type"])]["n"] += 1
        by_qt[str(row["query_type"])]["correct"] += int(row["correct"])
        by_rung[str(row["rung"])]["n"] += 1
        by_rung[str(row["rung"])]["correct"] += int(row["correct"])
        by_source[str(row["source"]).split(":")[0]] += 1

    n = len(rows)
    n_ok = sum(1 for r in rows if r["correct"])
    overall = n_ok / n if n else 0.0

    def acc(bucket: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        return {
            k: {
                "n": v["n"],
                "correct": v["correct"],
                "accuracy": v["correct"] / v["n"] if v["n"] else 0.0,
            }
            for k, v in sorted(bucket.items())
        }

    return {
        "kind": "cladder_oracle_assisted_regression",
        "protocol": "C",
        "n": n,
        "n_correct": n_ok,
        "accuracy": overall,
        "overall_pct": round(100.0 * overall, 4),
        "by_query_type": acc(by_qt),
        "by_rung": acc(by_rung),
        "source_counts": dict(by_source),
        "information_sources": dict(Counter(_information_source(row["source"]) for row in rows)),
        "failures": [r for r in rows if not r["correct"]][:40],
        "claims": {
            "uses_generator_slots": True,
            "uses_published_target_values": True,
            "scope": "generator correspondence",
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args(argv)

    questions, models, meta = load_cladder_bundle(args.data_dir)
    payload = evaluate_certified(
        questions, models_index(models), limit=args.limit
    )
    payload["data"] = meta
    args.out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    assert "AQ." not in text
    path = args.out / "cladder_certified_eval.json"
    path.write_text(text)
    (args.out / "cladder_certified_eval.sha256").write_text(
        hashlib.sha256(text.encode()).hexdigest() + "\n"
    )
    print(
        json.dumps(
            {
                "ok": payload["n_correct"] == payload["n"],
                "accuracy": payload["accuracy"],
                "overall_pct": payload["overall_pct"],
                "n": payload["n"],
                "protocol": "C",
                "by_rung": payload["by_rung"],
                "failures": len(payload["failures"]),
                "wrote": str(path),
            },
            indent=2,
        )
    )
    return 0 if payload["n_correct"] == payload["n"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
