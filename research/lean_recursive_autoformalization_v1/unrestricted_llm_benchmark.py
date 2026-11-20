"""Unrestricted-English / miniF2F / FormL4 LLM→gate benchmark (research only).

Pipeline per item:
  1. Zero-shot PGRA formalize (no LLM) — expect mostly unsupported.
  2. Gemini proposes {ABSTAIN | CONTROLLED_ENGLISH | LEAN4_STMT}.
  3. Gate: controlled English → formalize_with_rules; Lean stmt recorded only
     (Mathlib compile not claimed); never set pcs authority.

Free-tier: uses gemini_client soft RPM/RPD caps. API key via GEMINI_API_KEY only.
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
    from .gemini_client import DEFAULT_MODEL, GeminiClient, probe_quota
    from .grammar_extensions import RULE_IDS
except ImportError:
    from capability import formalize_with_rules
    from gemini_client import DEFAULT_MODEL, GeminiClient, probe_quota
    from grammar_extensions import RULE_IDS

PKG = Path(__file__).resolve().parent
EXT = PKG / "external_data"

REWRITE_PROMPT = """You are assisting a fail-closed proof-carrying formalization gate.
Your job is NOT to prove olympiad math. Map the user's statement into ONE of:

1) ABSTAIN — if it requires reals, logs, topology, measure, graphs, physics,
   competition contest packaging, or anything outside elementary Nat/Int/Prop
   quantifier English.
2) CONTROLLED_ENGLISH — rewrite into EXACTLY this grammar family when possible:
   - "For all natural numbers n, n equals n."
   - "For all natural numbers n and m, n + m equals m + n."
   - "There exists a natural number n such that n equals 0."
   - "For all propositions A and B, A implies B."
   Prefer ABSTAIN over a stretched rewrite. Never invent lemmas.
3) LEAN4_STMT — only if you can give a short Lean 4 theorem TYPE (no proof),
   using only Nat/Int/Prop and +, *, =, ∧, ∨, →, ¬, ∃, ∀. No Mathlib imports.

Return STRICT JSON with keys: decision, text, reason
decision ∈ {ABSTAIN, CONTROLLED_ENGLISH, LEAN4_STMT}
text = rewritten English or Lean type or empty for ABSTAIN
reason = short string

USER_STATEMENT:
"""


def _bridge_rewriteable() -> list[dict[str, Any]]:
    """Unrestricted-ish English that SHOULD map into PGRA grammar (positive transfer)."""
    return [
        {
            "id": "bridge_identity_plain",
            "benchmark": "bridge_rewriteable",
            "split": "diag",
            "english": "Every natural number is equal to itself.",
            "expect_in_pgra_grammar": True,
            "source": "PCS authored bridge (unrestricted surface)",
        },
        {
            "id": "bridge_comm_add",
            "benchmark": "bridge_rewriteable",
            "split": "diag",
            "english": "Addition of natural numbers is commutative: for naturals n and m, n+m equals m+n.",
            "expect_in_pgra_grammar": True,
            "source": "PCS authored bridge (unrestricted surface)",
        },
        {
            "id": "bridge_exists_zero",
            "benchmark": "bridge_rewriteable",
            "split": "diag",
            "english": "Zero is a natural number, and there is some natural equal to it.",
            "expect_in_pgra_grammar": True,
            "source": "PCS authored bridge (unrestricted surface)",
        },
        {
            "id": "bridge_plus_zero",
            "benchmark": "bridge_rewriteable",
            "split": "diag",
            "english": "Adding zero on the right does nothing to a natural number.",
            "expect_in_pgra_grammar": True,
            "source": "PCS authored bridge (unrestricted surface)",
        },
    ]


def _load_samples(*, per_external: int | None = None) -> list[dict[str, Any]]:
    """Load balanced external samples + rewriteable bridges."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for name, key in (
        ("minif2f_informal/SAMPLE.json", "miniF2F"),
        ("forml4/SAMPLE.json", "FormL4"),
    ):
        path = EXT / name
        if path.is_file():
            buckets[key] = json.loads(path.read_text())
    items: list[dict[str, Any]] = []
    if per_external is None:
        # round-robin up to available
        max_n = max((len(v) for v in buckets.values()), default=0)
        for i in range(max_n):
            for key in ("miniF2F", "FormL4"):
                if key in buckets and i < len(buckets[key]):
                    items.append(buckets[key][i])
    else:
        for key in ("miniF2F", "FormL4"):
            items.extend(buckets.get(key, [])[:per_external])
    items.extend(_bridge_rewriteable())
    return items


def _parse_llm_json(text: str) -> dict[str, Any]:
    text = text.strip()
    # strip markdown fences if present
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"decision": "ABSTAIN", "text": "", "reason": "unparseable_llm_json", "raw": text[:400]}
    decision = str(data.get("decision") or "ABSTAIN").upper()
    if decision not in {"ABSTAIN", "CONTROLLED_ENGLISH", "LEAN4_STMT"}:
        decision = "ABSTAIN"
    return {
        "decision": decision,
        "text": str(data.get("text") or ""),
        "reason": str(data.get("reason") or ""),
    }


def evaluate_item(item: dict[str, Any], rules: frozenset[str], client: GeminiClient | None) -> dict[str, Any]:
    english = str(item.get("english") or "").strip()
    zero = formalize_with_rules(english, rules) if english else {"status": "unsupported"}
    zero_supported = zero.get("status") in {"supported", "ambiguous"} and bool(zero.get("candidates"))

    llm_block: dict[str, Any] = {"skipped": client is None}
    gated: dict[str, Any] = {"status": "skipped"}
    if client is not None and english:
        resp = client.generate(REWRITE_PROMPT + english, max_output_tokens=400)
        parsed = _parse_llm_json(resp.get("text") or "") if resp.get("ok") else {
            "decision": "ABSTAIN",
            "text": "",
            "reason": f"llm_http_{resp.get('status')}",
        }
        llm_block = {
            "ok": bool(resp.get("ok")),
            "status": resp.get("status"),
            "usage": resp.get("usage"),
            "parsed": parsed,
        }
        decision = parsed["decision"]
        if decision == "CONTROLLED_ENGLISH" and parsed.get("text"):
            gated_result = formalize_with_rules(str(parsed["text"]), rules)
            gated = {
                "path": "controlled_english",
                "status": gated_result.get("status"),
                "supported": gated_result.get("status") in {"supported", "ambiguous"}
                and bool(gated_result.get("candidates")),
                "lean": (gated_result.get("candidates") or [{}])[0].get("lean")
                if gated_result.get("candidates")
                else None,
            }
        elif decision == "LEAN4_STMT":
            gated = {
                "path": "lean4_stmt_recorded_only",
                "status": "recorded_not_compiled",
                "supported": False,
                "lean_text": parsed.get("text"),
                "note": "Mathlib/Lean compile not claimed in this harness",
            }
        else:
            gated = {
                "path": "abstain",
                "status": "unsupported",
                "supported": False,
                "reason": parsed.get("reason"),
            }

    return {
        "id": item.get("id"),
        "benchmark": item.get("benchmark"),
        "split": item.get("split"),
        "english": english[:500],
        "zero_shot_pgra_supported": zero_supported,
        "zero_shot_status": zero.get("status"),
        "llm": llm_block,
        "gated": gated,
    }


def run(
    *,
    output: Path,
    limit: int = 24,
    skip_llm: bool = False,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rules = frozenset(RULE_IDS)
    # Keep external + bridges; truncate while preserving mix.
    all_items = _load_samples()
    bridges = [i for i in all_items if i.get("benchmark") == "bridge_rewriteable"]
    external = [i for i in all_items if i.get("benchmark") != "bridge_rewriteable"]
    keep_ext = max(0, limit - len(bridges))
    items = external[:keep_ext] + bridges
    if len(items) > limit:
        items = items[:limit]

    quota = None if skip_llm else probe_quota(model=model)
    if quota is not None:
        (output / "quota_probe.json").write_text(json.dumps(quota, indent=2, sort_keys=True) + "\n")

    client = None
    if not skip_llm:
        client = GeminiClient(
            model=model,
            ledger_path=output / "gemini_usage_ledger.json",
            rpd_soft=max(40, limit + 8),
            min_interval_s=6.5,
            rpm=8,
        )

    rows = [evaluate_item(it, rules, client) for it in items]
    by_bench: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_bench.setdefault(str(row.get("benchmark") or "unknown"), []).append(row)

    def _agg(rs: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(rs)
        zero = sum(1 for r in rs if r["zero_shot_pgra_supported"])
        llm_ok = sum(1 for r in rs if (r.get("llm") or {}).get("ok"))
        gated_sup = sum(1 for r in rs if (r.get("gated") or {}).get("supported"))
        abstain = sum(1 for r in rs if (r.get("gated") or {}).get("path") == "abstain")
        return {
            "n": n,
            "zero_shot_supported": zero,
            "zero_shot_rate": zero / max(1, n),
            "llm_ok": llm_ok,
            "gated_supported": gated_sup,
            "gated_supported_rate": gated_sup / max(1, n),
            "llm_abstain": abstain,
            "llm_abstain_rate": abstain / max(1, n),
        }

    summary = {
        "format": "pcs-pgra-unrestricted-llm-benchmark-v1",
        "model": None if skip_llm else model,
        "limit": limit,
        "overall": _agg(rows),
        "by_benchmark": {k: _agg(v) for k, v in by_bench.items()},
        "quota_probe": quota,
        "usage_ledger": None if client is None else client.ledger.as_dict(),
        "rows": rows,
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
        "limitations": [
            "Unrestricted English equivalence unproved",
            "FormL4/miniF2F Lean compile parity not claimed here",
            "Free-tier remaining RPM/RPD not returned by Generative Language API",
            "LLM rewrites are fail-closed gated; authority remains false",
        ],
    }
    (output / "unrestricted_llm_summary.json").write_text(
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
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args(argv)
    summary = run(
        output=args.output, limit=args.limit, skip_llm=args.skip_llm, model=args.model
    )
    print(
        json.dumps(
            {
                "overall": summary["overall"],
                "by_benchmark": summary["by_benchmark"],
                "usage_ledger": summary.get("usage_ledger"),
                "remaining_quota_visible_in_api": False,
                "pcs_scientific_authority": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
