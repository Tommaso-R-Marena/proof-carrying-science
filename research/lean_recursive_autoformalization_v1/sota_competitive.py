"""Historical FormL4 model pipeline with a pinned, zero-demo statement-elaboration protocol."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from . import forml4_protocol as protocol
    from .gemini_client import DEFAULT_MODEL, GeminiClient
    from .kimina_autoformalizer import DEFAULT_GGUF, autoformalize as kimina_autoformalize
    from .lean_compile_oracle import compile_lean
except ImportError:
    import forml4_protocol as protocol
    from gemini_client import DEFAULT_MODEL, GeminiClient
    from kimina_autoformalizer import DEFAULT_GGUF, autoformalize as kimina_autoformalize
    from lean_compile_oracle import compile_lean

PKG = Path(__file__).resolve().parent
MINIF2F_SAMPLE = PKG / "external_data" / "minif2f_informal" / "SAMPLE.json"

PUBLISHED = {
    "forml4_basic_compile_pct": {
        "GPT-4-Turbo": 1.47,
        "PDA_RFT_Verifier_SOTA": 46.28,
    },
    "minif2f_af_pass8_approx": {
        "Kimina-Autoformalizer-7B": 92.2,
        "LongCat-Flash-Prover": 99.0,
    },
}

def _statement_prompt(english: str) -> str:
    return ("Return a single elementary Lean theorem statement or ABSTAIN. "
            "Use explicit Nat, Int, Bool or Prop binders and basic arithmetic or logic. "
            "Omit proof text. Preserve the mathematical meaning.\n\n" + english)


def _repair_prompt(english: str, previous: str, error: str) -> str:
    return (_statement_prompt(english) + "\n\nPrevious candidate:\n" + previous
            + "\n\nChecker diagnostic:\n" + error)


def _load_minif2f(n: int) -> list[dict[str, Any]]:
    items = json.loads(MINIF2F_SAMPLE.read_text()) if MINIF2F_SAMPLE.is_file() else []
    return items[:n]


def _try_candidates(
    *,
    english: str,
    theorem_name: str,
    client: GeminiClient | None,
    max_repairs: int,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []

    # 1) Kimina
    try:
        k = kimina_autoformalize(english, theorem_name=theorem_name, temperature=0.15)
        code = k.get("text") or ""
        c = compile_lean(code)
        attempts.append({"source": "kimina", "compiled": c.get("compiled"), "code": code, "checker_status": c["status"], "error": c.get("error")})
        if c.get("compiled"):
            return {"compiled": True, "winner": "kimina", "code": c.get("normalized"), "attempts": attempts}
        last_code, last_err = code, c.get("error") or ""
    except Exception as ex:  # noqa: BLE001
        attempts.append({"source": "kimina", "compiled": False, "error": str(ex)})
        last_code, last_err = "", str(ex)

    # 2) Gemini zero-shot
    if client is not None:
        prompt = _statement_prompt(english)
        resp = client.generate(prompt, max_output_tokens=700)
        code = resp.get("text") or ""
        c = compile_lean(code)
        attempts.append(
            {
                "source": "gemini_zeroshot",
                "compiled": c.get("compiled"),
                "code": code, "checker_status": c["status"],
                "error": c.get("error"),
                "llm_ok": resp.get("ok"),
            }
        )
        if c.get("compiled"):
            return {
                "compiled": True,
                "winner": "gemini_zeroshot",
                "code": c.get("normalized"),
                "attempts": attempts,
            }
        last_code, last_err = code, c.get("error") or last_err

        # 3) Process-driven repairs
        for i in range(max_repairs):
            if not last_code:
                break
            rprompt = _repair_prompt(english, last_code[:2500], (last_err or "")[-1500])
            resp = client.generate(rprompt, max_output_tokens=700)
            code = resp.get("text") or ""
            c = compile_lean(code)
            attempts.append(
                {
                    "source": f"gemini_repair_{i+1}",
                    "compiled": c.get("compiled"),
                    "code": code, "checker_status": c["status"],
                    "error": c.get("error"),
                }
            )
            if c.get("compiled"):
                return {
                    "compiled": True,
                    "winner": f"gemini_repair_{i+1}",
                    "code": c.get("normalized"),
                    "attempts": attempts,
                }
            last_code, last_err = code, c.get("error") or last_err

    return {"compiled": False, "winner": None, "code": last_code, "attempts": attempts}


def run(
    *,
    output: Path,
    forml4_n: int = 40,
    minif2f_n: int = 16,
    max_repairs: int = 2,
    skip_gemini: bool = True,
    forml4_path: Path = protocol.DEFAULT_DATA,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("choose an empty output directory to preserve prior evidence")
    if max_repairs < 0 or minif2f_n < 0:
        raise ValueError("negative budget")
    forml4 = protocol.select(forml4_path, forml4_n)
    plan = protocol.protocol(forml4)
    plan.update(max_repairs=max_repairs, kimina_temperature=0.15, gemini_model=None if skip_gemini else model,
                stopping_rule="first elaborated proposition", candidate_limit=1 if skip_gemini else 2 + max_repairs,
                oracle="closed arithmetic/logic statement fragment, Lean Std", mini_n=minif2f_n)
    (output / "protocol.json").write_text(json.dumps(plan, indent=2) + "\n")
    if not DEFAULT_GGUF.is_file():
        raise FileNotFoundError("Kimina weights unavailable; protocol frozen, generation did not run")
    client = None
    if not skip_gemini:
        client = GeminiClient(
            model=model,
            ledger_path=output / "gemini_usage_ledger.json",
        )

    form_rows = []
    for item in forml4:
        result = _try_candidates(
            english=str(item["english"]),
            theorem_name=item["id"],
            client=client,
            max_repairs=max_repairs,
        )
        form_rows.append(
            {
                "id": item["id"],
                "english": str(item["english"])[:300],
                "compiled": bool(result["compiled"]),
                "winner": result.get("winner"),
                "n_attempts": len(result.get("attempts") or []),
                "attempts": result.get("attempts"),
            }
        )
        # checkpoint progress
        (output / "forml4_partial.json").write_text(
            json.dumps({"done": len(form_rows), "compiled": sum(1 for r in form_rows if r["compiled"])}, indent=2)
            + "\n"
        )

    mini = _load_minif2f(minif2f_n)
    mini_rows = []
    for i, item in enumerate(mini):
        english = str(item.get("english") or "")
        result = _try_candidates(
            english=english,
            theorem_name=f"minif2f_{item.get('problem_name', i)}".replace("-", "_")[:40],
            client=client,
            max_repairs=max_repairs if client else 0,
        )
        mini_rows.append(
            {
                "id": item.get("id"),
                "compiled": bool(result["compiled"]),
                "winner": result.get("winner"),
                "n_attempts": len(result.get("attempts") or []),
            }
        )

    form_rate = sum(1 for r in form_rows if r["compiled"]) / max(1, len(form_rows))
    mini_rate = sum(1 for r in mini_rows if r["compiled"]) / max(1, len(mini_rows))
    summary = {
        "format": "pgra-bounded-statement-elaboration-v2",
        "components": [
            "Kimina-Autoformalizer-7B-GGUF",
            "Lean 4.28 Std bounded elaboration probe",
            None if skip_gemini else f"Gemini {model} zero-shot + repair",
        ],
        "published": PUBLISHED,
        "forml4_basic": {
            "n": len(form_rows),
            "compile_rate_pct": round(100 * form_rate, 2),
            "compiled": sum(1 for r in form_rows if r["compiled"]),
            "rows_with_checker_result": sum(any(a.get("checker_status") for a in r["attempts"]) for r in form_rows),
            "first_candidate_compiled": sum(bool(r["attempts"][0]["compiled"]) for r in form_rows),
            "interval_wilson95_descriptive": protocol.wilson(sum(r["compiled"] for r in form_rows), len(form_rows)),
            "semantically_evaluated": 0, "proofs_checked": 0,
            "comparison": "Unmatched sample, search budget and oracle; no rank inference",
            "winner_counts": _counts(form_rows),
            "rows": form_rows,
        },
        "minif2f": {
            "n": len(mini_rows),
            "compile_rate_pct": round(100 * mini_rate, 2),
            "compiled": sum(1 for r in mini_rows if r["compiled"]),
            "winner_counts": _counts(mini_rows),
            "rows": mini_rows,
            "note": "Compile-% is a proxy; Kimina SOTA is verified AF pass@k on miniF2F protocol",
        },
        "usage_ledger": None if client is None else client.ledger.as_dict(),
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
    }
    (output / "sota_competitive_summary.json").write_text(
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


def _counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        w = r.get("winner") or "none"
        out[w] = out.get(w, 0) + 1
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--forml4-n", type=int, default=40)
    p.add_argument("--minif2f-n", type=int, default=16)
    p.add_argument("--max-repairs", type=int, default=2)
    p.add_argument("--forml4-path", type=Path, default=protocol.DEFAULT_DATA)
    api = p.add_mutually_exclusive_group()
    api.add_argument("--use-gemini", dest="use_gemini", action="store_true")
    api.add_argument("--skip-gemini", dest="use_gemini", action="store_false")
    p.set_defaults(use_gemini=False)
    p.add_argument("--model", default=DEFAULT_MODEL)
    args = p.parse_args(argv)
    summary = run(
        output=args.output,
        forml4_n=args.forml4_n,
        minif2f_n=args.minif2f_n,
        max_repairs=args.max_repairs,
        skip_gemini=not args.use_gemini,
        forml4_path=args.forml4_path,
        model=args.model,
    )
    print(
        json.dumps(
            {
                "forml4_basic_compile_pct": summary["forml4_basic"]["compile_rate_pct"],
                "forml4_winners": summary["forml4_basic"]["winner_counts"],
                "minif2f_compile_pct": summary["minif2f"]["compile_rate_pct"],
                "minif2f_winners": summary["minif2f"]["winner_counts"],
                "published": summary["published"],
                "pcs_scientific_authority": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
