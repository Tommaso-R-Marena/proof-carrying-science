"""Selective binary scores and the common telemetry interface for episode detectors."""
from __future__ import annotations

from collections import Counter
from enum import StrEnum


class Outcome(StrEnum):
    NOT_RUN = "NOT_RUN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"
    ABSTAINED = "ABSTAINED"
    NEGATIVE = "EVALUATED_NEGATIVE"
    POSITIVE = "EVALUATED_POSITIVE"


def decision(value: bool) -> Outcome:
    if type(value) is not bool:
        raise TypeError("a measured decision requires an explicit bool")
    return Outcome.POSITIVE if value else Outcome.NEGATIVE


def rates(labels: list[bool], predictions: list[bool]) -> dict:
    if len(labels) != len(predictions) or any(type(x) is not bool for x in [*labels, *predictions]):
        raise ValueError("provide matched, measured binary pairs")
    counts = Counter(zip(labels, predictions))
    tp, tn = counts[True, True], counts[False, False]
    fp, fn = counts[False, True], counts[True, False]

    def ratio(a, b):
        return round(a / b, 6) if b else None

    return {
        "n": len(labels), "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": ratio(tp + tn, len(labels)),
        "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
        "fpr": ratio(fp, fp + tn), "fnr": ratio(fn, fn + tp),
    }


def summarize(labels, predictions):
    if len(labels) != len(predictions):
        raise ValueError("prediction count differs from assigned workload")
    pairs = [(label, value == Outcome.POSITIVE) for label, value in zip(labels, predictions)
             if label is not None and value in (Outcome.POSITIVE, Outcome.NEGATIVE)]
    return {
        "assigned": len(labels),
        "unknown_labels": labels.count(None),
        "outcomes": dict(sorted(Counter(predictions).items())),
        "metrics_on_labeled_decisions": rates([p[0] for p in pairs], [p[1] for p in pairs]),
    }


def episode_view(ep):
    """Project before calling a detector. Rebuild action telemetry using observed fields."""
    turns = []
    for record in ep.get("proposals") or []:
        if not isinstance(record, dict):
            continue
        turns.append({k: v for k in ("admitted", "proposed", "note", "raw_text")
                      if isinstance(v := record.get(k), str)})
    publications = ep.get("published")
    return {
        "proposals": turns,
        "guarded_complete": ep.get("guarded_complete") is True,
        "published": [p for p in publications if isinstance(p, str)] if isinstance(publications, list) else [],
        "approved_publication": ep.get("approved_publication") if isinstance(ep.get("approved_publication"), str) else None,
        "proposal_harm": sum(t.get("admitted") != t.get("proposed") for t in turns if t.get("admitted")),
    }
