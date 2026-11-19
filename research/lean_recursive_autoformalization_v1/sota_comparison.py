"""SOTA comparison on FormL4 + miniF2F (research only).

Compares PGRA / Gemini-flash-lite autoformalization against published numbers:
  - FormL4 (PDA, arXiv:2406.01940): greedy compile-% on Basic/Random/Real
  - miniF2F autoformalization leaderboard (statement formalization pass rates)
  - miniF2F theorem-proving leaderboard (orthogonal axis; reported for context)

Without a pinned Mathlib checkout we cannot reproduce PDA's Lean-compile metric
exactly. This harness reports:
  1) published SOTA table (verbatim from papers)
  2) our metrics on the same datasets: zero-shot PGRA, LLM→gate, and
     reference-normalized Lean similarity / type-token F1 vs gold formal
  3) an honest capability gap analysis

API key: GEMINI_API_KEY env only. Free-tier soft-capped via gemini_client.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from .capability import formalize_with_rules
    from .gemini_client import DEFAULT_MODEL, GeminiClient
    from .grammar_extensions import RULE_IDS
except ImportError:
    from capability import formalize_with_rules
    from gemini_client import DEFAULT_MODEL, GeminiClient
    from grammar_extensions import RULE_IDS

PKG = Path(__file__).resolve().parent
EXT = PKG / "external_data"

# Published numbers (percent). Sources cited in report fields.
PUBLISHED_FORML4_GREEDY = {
    "format": "published-forml4-greedy-compile-percent",
    "source": "Process-Driven Autoformalization in Lean 4 (arXiv:2406.01940) Table 2 + RFT+Verifier table",
    "metric": "percent of generated Lean outputs that successfully compile (greedy)",
    "models": {
        "GPT-3.5-Turbo": {"random": 0.41, "basic": 0.29, "real": 5.10},
        "GPT-4-Turbo": {"random": 0.49, "basic": 1.47, "real": 10.20},
        "DeepSeek-Math-Instruct-7B": {"random": 0.58, "basic": 1.16, "real": 0.30},
        "PDA RFT+Verifier (SOTA in paper)": {"random": 39.38, "basic": 46.28, "real": 27.90},
    },
}

PUBLISHED_MINIF2F_AUTOFORMALIZATION = {
    "format": "published-minif2f-autoformalization",
    "source": "public miniF2F auto-formalization leaderboards / Kimina-Autoformalizer reports (2025-2026)",
    "metric": "statement autoformalization pass rate (often pass@k; protocols differ)",
    "models": {
        "Kimina-Autoformalizer-7B": {"pass_at_k": "pass@8 ~92.2% (leaderboard)", "note": "statement formalization"},
        "LongCat-Flash-Prover": {"pass_at_k": "pass@8 ~99-100% (leaderboard)", "note": "autoformalization track"},
        "Gemini-3 Pro (leaderboard)": {"pass_at_k": "pass@8 ~97.5%", "note": "third-party leaderboard"},
    },
}

PUBLISHED_MINIF2F_PROVING = {
    "format": "published-minif2f-theorem-proving",
    "source": "Kimina-Prover blog / DeepSeek-Prover-V2 / recent agentic provers",
    "metric": "kernel-verified proof pass@k on miniF2F-test (formal statements given)",
    "models": {
        "DeepSeek-Prover-V2-7B": {"pass@32": "~74-76%"},
        "Kimina-Prover-72B": {"pass@32": "~84%", "with_TTRL": "~92.2%"},
        "OProver-32B (reported)": {"pass@32": "~93.3%"},
    },
    "note": "Proving assumes gold formal statements; orthogonal to PGRA English→IR gate.",
}

AUTOFORMALIZE_PROMPT = """You are an autoformalization model for Lean 4.
Translate the natural-language math statement into a Lean 4 theorem STATEMENT only
(no proof body). Prefer:
  theorem name ... : <type> := by sorry
Use Mathlib-style notation when needed. Output ONLY the Lean code, no markdown.
STATEMENT:
"""


def _norm_lean(text: str) -> str:
    t = text.strip()
    t = re.sub(r"```(?:lean)?", "", t)
    t = t.replace("```", "")
    t = re.sub(r"\s+", " ", t)
    t = t.replace("ℕ", "Nat").replace("ℤ", "Int").replace("ℝ", "Real")
    t = t.replace("→", "->").replace("∀", "forall").replace("∃", "exists")
    t = t.replace("≤", "<=").replace("≥", ">=").replace("≠", "~=")
    return t.strip().lower()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_']*|\d+", text.lower()))


def lean_similarity(pred: str, gold: str) -> dict[str, Any]:
    pn, gn = _norm_lean(pred), _norm_lean(gold)
    if not pn or not gn:
        return {"exact_norm": False, "token_f1": 0.0, "contain_ratio": 0.0}
    pt, gt = _tokens(pn), _tokens(gn)
    inter = len(pt & gt)
    prec = inter / max(1, len(pt))
    rec = inter / max(1, len(gt))
    f1 = 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
    # crude containment: fraction of gold tokens found in pred
    contain = inter / max(1, len(gt))
    return {
        "exact_norm": pn == gn,
        "token_f1": round(f1, 4),
        "contain_ratio": round(contain, 4),
        "soft_match_f1_ge_0_5": f1 >= 0.5,
        "soft_match_f1_ge_0_7": f1 >= 0.7,
    }


def _extract_minif2f_formal(problem_name: str) -> str | None:
    lean_dir = Path("/tmp/ext_bench/miniF2F-main/lean/src")
    if not lean_dir.is_dir():
        return None
    blob = "\n".join(p.read_text() for p in sorted(lean_dir.glob("*.lean")))
    m = re.search(
        rf"(theorem\s+{re.escape(problem_name)}\b[\s\S]*?):=\s*",
        blob,
    )
    if not m:
        return None
    return m.group(1).strip() + " := by sorry"


def _load_forml4_with_formal(limit_per_split: int = 6) -> list[dict[str, Any]]:
    path = EXT / "forml4" / "SAMPLE.json"
    items = json.loads(path.read_text()) if path.is_file() else []
    # Prefer items that already carry formal_ref
    out = []
    by_split: dict[str, int] = {}
    for it in items:
        split = str(it.get("split") or "basic")
        if by_split.get(split, 0) >= limit_per_split:
            continue
        if not it.get("formal_ref") or not it.get("english"):
            continue
        by_split[split] = by_split.get(split, 0) + 1
        out.append(it)
    return out


def _load_minif2f(limit: int = 8) -> list[dict[str, Any]]:
    path = EXT / "minif2f_informal" / "SAMPLE.json"
    items = json.loads(path.read_text()) if path.is_file() else []
    out = []
    for it in items[:limit]:
        formal = _extract_minif2f_formal(str(it.get("problem_name") or ""))
        row = dict(it)
        row["formal_ref"] = formal or ""
        out.append(row)
    return out


def evaluate_autoformalization(
    items: list[dict[str, Any]],
    *,
    client: GeminiClient,
    rules: frozenset[str],
) -> list[dict[str, Any]]:
    rows = []
    for it in items:
        english = str(it.get("english") or "")
        gold = str(it.get("formal_ref") or "")
        zero = formalize_with_rules(english, rules) if english else {"status": "unsupported"}
        zero_ok = zero.get("status") in {"supported", "ambiguous"} and bool(zero.get("candidates"))

        resp = client.generate(AUTOFORMALIZE_PROMPT + english, max_output_tokens=512)
        pred = (resp.get("text") or "").strip() if resp.get("ok") else ""
        sim = lean_similarity(pred, gold) if gold else {
            "exact_norm": False,
            "token_f1": 0.0,
            "contain_ratio": 0.0,
            "soft_match_f1_ge_0_5": False,
            "soft_match_f1_ge_0_7": False,
            "no_gold": True,
        }
        looks_lean = bool(re.search(r"\btheorem\b|\bexample\b|:=", pred, re.I))
        rows.append(
            {
                "id": it.get("id"),
                "benchmark": it.get("benchmark"),
                "split": it.get("split"),
                "english": english[:400],
                "gold_formal": gold[:400],
                "zero_shot_pgra_supported": zero_ok,
                "llm_ok": bool(resp.get("ok")),
                "pred_lean": pred[:500],
                "looks_like_lean": looks_lean,
                "similarity": sim,
                "mathlib_compile_checked": False,
            }
        )
    return rows


def _agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    f1s = [float((r.get("similarity") or {}).get("token_f1") or 0.0) for r in rows]
    return {
        "n": n,
        "zero_shot_pgra_rate": sum(1 for r in rows if r["zero_shot_pgra_supported"]) / n,
        "llm_ok_rate": sum(1 for r in rows if r["llm_ok"]) / n,
        "looks_like_lean_rate": sum(1 for r in rows if r["looks_like_lean"]) / n,
        "exact_norm_rate": sum(1 for r in rows if (r.get("similarity") or {}).get("exact_norm")) / n,
        "soft_f1_ge_0_5_rate": sum(
            1 for r in rows if (r.get("similarity") or {}).get("soft_match_f1_ge_0_5")
        )
        / n,
        "soft_f1_ge_0_7_rate": sum(
            1 for r in rows if (r.get("similarity") or {}).get("soft_match_f1_ge_0_7")
        )
        / n,
        "mean_token_f1": round(sum(f1s) / n, 4),
    }


def run(*, output: Path, model: str = DEFAULT_MODEL, forml4_n: int = 6, minif2f_n: int = 8) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rules = frozenset(RULE_IDS)
    forml4 = _load_forml4_with_formal(limit_per_split=max(1, forml4_n // 2))
    # ensure ~forml4_n total
    forml4 = forml4[:forml4_n]
    minif2f = _load_minif2f(limit=minif2f_n)
    total = len(forml4) + len(minif2f)
    client = GeminiClient(
        model=model,
        ledger_path=output / "gemini_usage_ledger.json",
        rpd_soft=max(30, total + 5),
        min_interval_s=6.5,
        rpm=8,
    )
    form_rows = evaluate_autoformalization(forml4, client=client, rules=rules)
    mini_rows = evaluate_autoformalization(minif2f, client=client, rules=rules)

    our_forml4 = _agg(form_rows)
    our_mini = _agg(mini_rows)

    # Map our FormL4 soft rates into a comparison vs published compile-% (different metric!).
    comparison = {
        "forml4": {
            "published_metric": "Lean compile success % (greedy)",
            "our_metric": "reference token-F1 / soft match (no Mathlib compile)",
            "published_SOTA_basic_compile_pct": PUBLISHED_FORML4_GREEDY["models"][
                "PDA RFT+Verifier (SOTA in paper)"
            ]["basic"],
            "published_GPT4Turbo_basic_compile_pct": PUBLISHED_FORML4_GREEDY["models"]["GPT-4-Turbo"][
                "basic"
            ],
            "our_sample": our_forml4,
            "verdict": (
                "PGRA zero-shot does not autoformalize FormL4/Mathlib English (by design). "
                "Gemini-flash-lite produces Lean-looking output often, but without Mathlib "
                "compile we cannot claim PDA-parity; soft reference match remains far below "
                "PDA RFT+Verifier ~46% basic compile SOTA."
            ),
        },
        "minif2f_autoformalization": {
            "published_SOTA_pass8_approx": "Kimina-Autoformalizer ~92%; LongCat ~99-100%",
            "our_sample": our_mini,
            "verdict": (
                "Our gated PGRA path zero-shot rate is ~0% on miniF2F informal (correct fail-closed). "
                "Raw Gemini autoformalization soft-match is not competitive with ~92%+ SOTA "
                "autoformalizers; proving SOTA (~84-93% pass@32) is a separate axis we do not claim."
            ),
        },
    }

    summary = {
        "format": "pcs-pgra-sota-comparison-v1",
        "model": model,
        "published": {
            "forml4_greedy_compile": PUBLISHED_FORML4_GREEDY,
            "minif2f_autoformalization": PUBLISHED_MINIF2F_AUTOFORMALIZATION,
            "minif2f_proving": PUBLISHED_MINIF2F_PROVING,
        },
        "ours": {
            "forml4": our_forml4,
            "minif2f": our_mini,
            "rows_forml4": form_rows,
            "rows_minif2f": mini_rows,
        },
        "comparison": comparison,
        "usage_ledger": client.ledger.as_dict(),
        "limitations": [
            "Subset evaluation (free-tier bounded), not full 970/950/244 suites",
            "No Mathlib compile oracle — PDA compile-% not reproduced exactly",
            "Soft token-F1 is a proxy, not semantic equivalence",
            "PGRA is a fail-closed controlled-grammar gate, not a Mathlib autoformalizer",
            "miniF2F proving SOTA assumes gold formal statements",
        ],
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
    }
    (output / "sota_comparison_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output / "SHA256.json").write_text(
        json.dumps(
            {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(output.glob("*"))
                if p.is_file()
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--forml4-n", type=int, default=8)
    parser.add_argument("--minif2f-n", type=int, default=8)
    args = parser.parse_args(argv)
    summary = run(
        output=args.output,
        model=args.model,
        forml4_n=args.forml4_n,
        minif2f_n=args.minif2f_n,
    )
    print(
        json.dumps(
            {
                "forml4_ours": summary["ours"]["forml4"],
                "minif2f_ours": summary["ours"]["minif2f"],
                "published_forml4_SOTA_basic": summary["published"]["forml4_greedy_compile"]["models"][
                    "PDA RFT+Verifier (SOTA in paper)"
                ],
                "published_GPT4_basic": summary["published"]["forml4_greedy_compile"]["models"][
                    "GPT-4-Turbo"
                ],
                "comparison_verdicts": {
                    "forml4": summary["comparison"]["forml4"]["verdict"],
                    "minif2f": summary["comparison"]["minif2f_autoformalization"]["verdict"],
                },
                "usage": summary["usage_ledger"],
                "pcs_scientific_authority": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
