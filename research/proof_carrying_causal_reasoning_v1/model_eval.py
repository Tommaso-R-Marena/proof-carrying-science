"""Live local-model evaluation using pinned Qwen GGUF weights (optional).

Reuses the public-study pin contract and llama.cpp runtime. Does not modify
production PCS authority. Requires downloaded weights under --weights.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from research.proof_carrying_causal_reasoning_v1.experiment import (
    all_research_tasks,
    evaluate_model_responses,
    write_results,
)
from research.proof_carrying_causal_reasoning_v1.tasks.battery import Task


HERE = Path(__file__).resolve().parent
# Prefer the already-reviewed public-study pins (same Qwen3 GGUF artifacts).
PUBLIC_STUDY = HERE.parent / "public_study_validation_v1"


def _load_runtime():
    # Import without depending on package init side effects.
    sys.path.insert(0, str(PUBLIC_STUDY.parent.parent))
    from research.public_study_validation_v1 import runtime as rt  # type: ignore

    return rt


def download_weights(folder: Path) -> dict:
    rt = _load_runtime()
    return rt.download(Path(folder))


def run_live(
    weights: Path,
    out: Path,
    *,
    model: str = "Qwen/Qwen3-0.6B-GGUF",
    task_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    rt = _load_runtime()
    tasks = list(all_research_tasks())
    if task_ids:
        wanted = set(task_ids)
        tasks = [t for t in tasks if t.task_id in wanted]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    responses: Dict[str, str] = {}
    provenance: List[dict] = []

    with rt.LocalModel(Path(weights), model, out / "server") as engine:
        for task in tasks:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You answer causal identification questions. "
                        "Output a single JSON object only. No markdown."
                    ),
                },
                {"role": "user", "content": task.prompt},
            ]
            content, prov = engine.complete(model, messages)
            text = content.decode() if isinstance(content, (bytes, bytearray)) else str(content)
            responses[task.task_id] = text
            provenance.append({"task_id": task.task_id, **prov})
            (out / f"response_{task.task_id}.txt").write_text(text)

    scored = evaluate_model_responses(tasks, responses)
    payload = {
        "model": model,
        "weights": str(weights),
        "provenance": provenance,
        "evaluation": scored,
        "claims": {
            "frontier_sota": False,
            "production_authority": False,
            "empirical_causation_established": False,
            "local_measurement_only": True,
        },
    }
    (out / "model_eval.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload
