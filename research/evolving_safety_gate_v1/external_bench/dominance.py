"""Offline measurement audit. Run from the repository root with a fresh output path."""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

from ..catalog import SEED_CANDIDATES, detector_for
from .adjudicate import off_policy_reply
from .baselines import agentdojo_tool_filter
from .composed import episode_route
from .measurement import Outcome, decision, episode_view, summarize
from .run_bakeoff import CAPTURES, DEFAULT_MIRAGE

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence" / "external-bakeoff-v1"
# Protocol order is fixed before evaluation. The adjudicator does not read a
# producer's per-turn "admitted", "proposed", case ID, labels, or score.
SCIENCE = (("start", "load_evidence"), ("loaded", "review_claim"),
           ("reviewed", "publish_summary"), ("published", "finish"))
NOTEBOOK = (("empty", "open_draft"), ("drafted", "annotate"),
            ("annotated", "archive_public"), ("archived", "close"))


def emit_predictions(ep, *, hidden, ensemble):
    obs = episode_view(ep)
    turns = ep.get("proposals")
    complete = (not hidden and isinstance(turns, list) and len(turns) == 4
                and all(isinstance(p, dict) and "proposed" in p and
                        isinstance(p.get("admitted"), str) and bool(p["admitted"])
                        for p in turns))
    if hidden:
        obs["proposals"] = []
        obs["proposal_harm"] = 0
    # The execution-only control always consumes the recorded completion bit.
    complete_trace = ep.get("guarded_complete")
    return {
        "executed_completion": decision(not complete_trace) if type(complete_trace) is bool else Outcome.UNKNOWN,
        "flag_all": Outcome.POSITIVE,
        "flag_none": Outcome.NEGATIVE,
        "proposal_disagreement": decision(agentdojo_tool_filter(obs)) if complete else Outcome.ABSTAINED,
        "projected_episode_route": decision(episode_route(obs, ensemble).flag) if complete else Outcome.ABSTAINED,
    }


def rows_summary(rows):
    result = {}
    for name in rows[0]["predictions"] if rows else ():
        result[name] = summarize([r["label"] for r in rows],
                                 [r["predictions"][name] for r in rows])
    return result


def run_audit(evidence=EVIDENCE, captures=DEFAULT_MIRAGE):
    sources = {}

    def read(path, name):
        raw = path.read_bytes()
        sources[name] = sha256(raw).hexdigest()
        return json.loads(raw)

    content = read(evidence / "track_a_jbb.json", "track_a_jbb.json")["rows"]
    labels = [r["y_harmful"] for r in content]
    if any(type(v) is not bool for v in labels):
        raise ValueError("invalid JBB label")
    specialists = {}
    for name in ["gemini_moderator", "openai_moderation_proxy"]:
        preds = [decision(r[name]) if type(r.get(name)) is bool else Outcome.UNKNOWN for r in content]
        specialists[name] = summarize(labels, preds)
    for name in ["agent_tool_filter", "prompt_injection_classifier"]:
        specialists[name] = summarize(labels, [Outcome.NOT_APPLICABLE] * len(labels))
    specialists["fresh_gemini"] = summarize(labels, [Outcome.NOT_RUN] * len(labels))

    old_b = read(evidence / "track_b_mirage.json", "track_b_mirage.json")["rows"]
    old_c = read(evidence / "live-transfer" / "summary.json", "live-transfer/summary.json")["rows"]
    old = read(evidence / "dominance" / "dominance.json", "dominance/dominance.json")
    ensemble = detector_for(next(c for c in SEED_CANDIDATES if c.id == "ensemble-v1"))
    rows = []
    for capture in CAPTURES:
        items = read(captures / capture / "summary.json", capture + "/summary.json")["episodes"]
        steps = NOTEBOOK if capture.startswith("transfer_lab_") else SCIENCE
        for i, episode in enumerate(items):
            label = off_policy_reply(episode, steps)
            for hidden in (False, True):
                rows.append({"capture": capture, "index": i, "condition": "masked" if hidden else "visible",
                             "label": label, "predictions": emit_predictions(episode, hidden=hidden, ensemble=ensemble)})
    by_condition = defaultdict(list)
    by_capture = defaultdict(list)
    for row in rows:
        by_condition[row["condition"]].append(row)
        by_capture[row["capture"] + "/" + row["condition"]].append(row)
    return {
        "format": "pcs-esg-measurement-audit-v2", "sha256_inputs": sources,
        "new_model_calls": 0, "production_authority": False,
        "specialist_protocol": {
            "task": "archived JBB Goal intent classification", "source": "retained predictions",
            "label": "JBB harmful/benign split", "systems": specialists,
        },
        "matched_episode_protocol": {
            "task": "any invalid or off-policy JSON action across four ordered turns",
            "target": "strict reply-format and proposal-policy compliance",
            "family": "two deterministic correcting workflows; paired visibility interventions",
            "systems": {k: rows_summary(v) for k, v in by_condition.items()},
            "per_capture": {k: rows_summary(v) for k, v in by_capture.items()},
            "rows": rows,
        },
        "historical_diagnostics": {
            "reported_composed_geo_mean": old["multi_track"]["composed_stack"]["geo_mean_f1"],
            "track_b_positive": sum(r["y_should_flag"] for r in old_b), "track_b_n": len(old_b),
            "track_c_positive": sum(r["mirage"] for r in old_c), "track_c_n": len(old_c),
            "track_c_negative": sum(not r["mirage"] for r in old_c),
        },
        "cross_modality_comparison": {"status": Outcome.NOT_RUN, "pareto": None, "geometric_mean": None,
                                      "reason": "Missing matched systems, tasks and independently assigned labels."},
    }


def run_dominance(out: Path, *, use_gemini: bool = False):
    """Replay the archived comparison's audit; live inference has a separate runner."""
    if use_gemini:
        raise ValueError("this audit replays retained model outputs")
    result = run_audit()
    out.mkdir(parents=True, exist_ok=False)
    (out / "dominance.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--no-gemini", action="store_true", help="audit always runs offline")
    args = parser.parse_args()
    r = run_dominance(args.out)
    print(json.dumps(r["cross_modality_comparison"]))


if __name__ == "__main__":
    main()
