"""Optional FormalizationRanker feedback cycle gated by PGRA preserve/expand/loss.

Uses ``pcs.experimental.prover.formalization_model.FormalizationRanker`` on a
frozen discrete labeling set (supported domain labels + abstain). Candidates
never auto-promote. If torch is missing, skip gracefully with a clear status.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

try:
    from .gate import digest
except ImportError:  # flat sys.path research execution
    from gate import digest

AUTOMATIC_DEPLOYMENT = False
PCS_SCIENTIFIC_AUTHORITY = False


@dataclass(frozen=True)
class RankerDecision:
    accepted: bool
    reason: str
    old_accuracy: int
    new_accuracy: int
    old_correct: tuple[str, ...]
    new_correct: tuple[str, ...]
    gained: tuple[str, ...]
    automatic_deployment: bool = False
    pcs_scientific_authority: bool = False


def _labeling_set() -> list[dict[str, Any]]:
    """Frozen discrete labels: 0=Prop, 1=Nat, 2=Int, 3=abstain."""
    return [
        {
            "id": "lab_prop",
            "text": "For all propositions A, A implies A.",
            "label": 0,
        },
        {
            "id": "lab_nat",
            "text": "For all natural numbers n, n + 0 equals n.",
            "label": 1,
        },
        {
            "id": "lab_int",
            "text": "For all integers x, x equals x.",
            "label": 2,
        },
        {
            "id": "lab_abstain_a",
            "text": "Prove everything.",
            "label": 3,
        },
        {
            "id": "lab_abstain_b",
            "text": "Every graph is connected.",
            "label": 3,
        },
        {
            "id": "lab_nat_b",
            "text": "For all natural numbers m, m equals m.",
            "label": 1,
        },
    ]


def _predict_label(ranker: Any, text: str) -> int:
    import torch

    with torch.no_grad():
        return int(ranker(text).argmax().item())


def evaluate_ranker(ranker: Any, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = items if items is not None else _labeling_set()
    correct: list[str] = []
    outcomes: dict[str, bool] = {}
    for item in data:
        pred = _predict_label(ranker, item["text"])
        ok = pred == item["label"]
        outcomes[item["id"]] = ok
        if ok:
            correct.append(item["id"])
    # Exact integer "loss" = number of incorrect labels.
    loss = len(data) - len(correct)
    return {
        "correct": frozenset(correct),
        "accuracy_count": len(correct),
        "loss": loss,
        "outcomes": outcomes,
        "n": len(data),
    }


def accept_ranker(old_ranker: Any, new_ranker: Any, items: list[dict[str, Any]] | None = None) -> RankerDecision:
    """Same preserve/expand/loss idea on discrete label accuracy."""
    data = items if items is not None else _labeling_set()
    old = evaluate_ranker(old_ranker, data)
    new = evaluate_ranker(new_ranker, data)
    old_c, new_c = old["correct"], new["correct"]
    if not old_c <= new_c:
        reason = "REJECT:certified_capability_regression"
    elif not (new_c - old_c):
        reason = "REJECT:no_new_certified_capability"
    elif not new["loss"] < old["loss"]:
        reason = "REJECT:loss_not_strictly_lower"
    else:
        reason = "ACCEPT:reference_only_ranker_candidate"
    return RankerDecision(
        accepted=reason.startswith("ACCEPT"),
        reason=reason,
        old_accuracy=old["accuracy_count"],
        new_accuracy=new["accuracy_count"],
        old_correct=tuple(sorted(old_c)),
        new_correct=tuple(sorted(new_c)),
        gained=tuple(sorted(new_c - old_c)),
        automatic_deployment=False,
        pcs_scientific_authority=False,
    )


def run_ranker_cycle(output_dir: Path | None = None, *, epochs: int = 40, seed: int = 19) -> dict[str, Any]:
    """Train a candidate FormalizationRanker; never auto-promote."""
    try:
        import torch
        from torch import nn
        from pcs.experimental.prover.formalization_model import FormalizationRanker
    except ImportError as ex:
        status = {
            "format": "pcs-pgra-ranker-cycle-v1",
            "status": "skipped_torch_unavailable",
            "detail": str(ex),
            "automatic_deployment": False,
            "pcs_scientific_authority": False,
            "candidate_promoted": False,
        }
        if output_dir is not None:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            (Path(output_dir) / "ranker_cycle.json").write_text(
                json.dumps(status, indent=2, sort_keys=True) + "\n"
            )
        return status

    items = _labeling_set()
    torch.manual_seed(seed)
    baseline = FormalizationRanker()
    candidate = FormalizationRanker()
    # Clone baseline weights into candidate then train candidate only.
    candidate.load_state_dict(baseline.state_dict())
    optimizer = torch.optim.Adam(candidate.parameters(), lr=0.05)
    for _ in range(epochs):
        for i in torch.randperm(len(items)).tolist():
            example = items[i]
            loss = nn.functional.cross_entropy(
                candidate(example["text"]).unsqueeze(0),
                torch.tensor([example["label"]]),
            )
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    decision = accept_ranker(baseline, candidate, items)
    report = {
        "format": "pcs-pgra-ranker-cycle-v1",
        "status": "completed",
        "labeling_sha256": digest(items),
        "decision": asdict(decision),
        "candidate_promoted": False,
        "automatic_promotion": False,
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
        "note": (
            "Candidate is scored by the PGRA-style discrete gate but never "
            "written into any production registry."
        ),
    }
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "ranker_cycle.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n"
        )
        if decision.accepted:
            sha = candidate.save(out / "ranker_candidate.json")
            report["candidate_sha256"] = sha
            (out / "ranker_cycle.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n"
            )
    return report


__all__ = [
    "AUTOMATIC_DEPLOYMENT",
    "PCS_SCIENTIFIC_AUTHORITY",
    "RankerDecision",
    "accept_ranker",
    "evaluate_ranker",
    "run_ranker_cycle",
]
