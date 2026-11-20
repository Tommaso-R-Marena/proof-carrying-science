"""Run PCCR against the external CLadder (NeurIPS 2023) oracle.

Usage:
  PYTHONPATH=. python -m research.proof_carrying_causal_reasoning_v1.external.run_cladder_eval \\
    --data-dir /path/to/extracted/cladder-v1 \\
    --out research/proof_carrying_causal_reasoning_v1/evidence/cladder-v1-oracle
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from research.proof_carrying_causal_reasoning_v1.external.cladder_bridge import (
    evaluate_models,
    evaluate_questions,
    extract_cladder_zip,
    load_cladder_bundle,
    models_index,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--zip",
        type=Path,
        default=None,
        help="Path to cladder-v1.zip (extracted into --work if needed)",
    )
    p.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Already-extracted directory containing meta-models + balanced JSON",
    )
    p.add_argument(
        "--work",
        type=Path,
        default=Path("/tmp/pccr-cladder-data"),
        help="Extraction workspace when --zip is given",
    )
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--atol-models", type=float, default=1e-6)
    p.add_argument("--atol-questions", type=float, default=1e-4)
    p.add_argument("--limit-models", type=int, default=None)
    p.add_argument("--limit-questions", type=int, default=None)
    args = p.parse_args(argv)

    if args.data_dir is None:
        if args.zip is None:
            raise SystemExit("provide --data-dir or --zip")
        data_dir = extract_cladder_zip(args.zip, args.work)
        zip_sha = hashlib.sha256(args.zip.read_bytes()).hexdigest()
    else:
        data_dir = args.data_dir
        sha_file = data_dir / "SOURCE_SHA256.txt"
        zip_sha = sha_file.read_text().strip() if sha_file.exists() else None

    t0 = time.time()
    questions, models, meta = load_cladder_bundle(data_dir)
    meta["zip_sha256"] = zip_sha
    model_results = evaluate_models(
        models, atol=args.atol_models, limit=args.limit_models
    )
    q_results = evaluate_questions(
        questions,
        models_index(models),
        atol=args.atol_questions,
        limit=args.limit_questions,
        query_types=("ate", "ett", "nde", "nie", "correlation"),
    )
    elapsed = time.time() - t0
    payload = {
        "package": "proof_carrying_causal_reasoning_v1",
        "benchmark": "CLadder",
        "citation": meta["citation"],
        "data": meta,
        "elapsed_seconds": elapsed,
        "models": model_results,
        "questions": q_results,
        "breakthrough_claim": {
            "statement": (
                "PCCR twin-network ETT and interventional ATE match the external "
                "CLadder Bernoulli oracle to numerical tolerance on all evaluated models"
            ),
            "models_ok": model_results["ok"],
            "questions_ok": q_results["ok"],
            "not_claimed": [
                "natural-language LLM accuracy on CLadder prompts",
                "production PCS authority",
                "general continuous/nonparametric identification",
            ],
        },
        "ok": bool(model_results["ok"] and q_results["ok"]),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "cladder_oracle_eval.json"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text)
    (out / "cladder_oracle_eval.sha256").write_text(
        hashlib.sha256(text.encode()).hexdigest() + "\n"
    )
    print(
        json.dumps(
            {
                "ok": payload["ok"],
                "models_accuracy": model_results["accuracy"],
                "models_n_ok": model_results["n_ok"],
                "models_n_fail": model_results["n_fail"],
                "questions_accuracy": q_results["accuracy"],
                "questions_n_ok": q_results["n_ok"],
                "questions_n_fail": q_results["n_fail"],
                "by_query_type": q_results["by_query_type"],
                "elapsed_seconds": elapsed,
                "wrote": str(path),
            },
            indent=2,
        )
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
