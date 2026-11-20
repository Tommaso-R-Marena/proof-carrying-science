"""Offline local detector diagnostic on JBB data and recorded agent episodes.

Tracks
------
A. JailbreakBench (JBB-Behaviors): content/injection detectors on external Goals.
B. PCS Assurance Mirage attested episodes: joint/ensemble vs content SOTA on same
   multi-channel agent episodes (AgentDojo-style attacks already executed).
C. Optional live transfer: inject JBB goals into PCS scientific workflow via Qwen.

Non-claims: not official JailbreakBench leaderboard ASR; not LlamaGuard weights;
ProtectAI is a prompt-injection classifier (not a general harm classifier).
"""
from __future__ import annotations

from hashlib import sha256
import csv
import json
from pathlib import Path
import time
from typing import Any

from research.evolving_safety_gate_v1.external_bench.baselines import (
    build_baselines,
    text_of_episode,
)
from research.evolving_safety_gate_v1.features import classic_mirage
from research.evolving_safety_gate_v1.hard_suite import build_hard_suite

DEFAULT_JBB = Path("/tmp/external-bench/jbb/data")
DEFAULT_MIRAGE = (
    Path(__file__).resolve().parents[2] / "assurance_mirage_v1" / "evidence"
)
CAPTURES = (
    "qwen06b",
    "qwen17b",
    "gemini_combined",
    "transfer_lab_qwen06b",
    "transfer_lab_qwen17b",
)


def _digest(obj: Any) -> str:
    return sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def load_jbb(data_dir: Path | None = None) -> dict[str, list[dict[str, str]]]:
    root = Path(data_dir) if data_dir else DEFAULT_JBB
    out: dict[str, list[dict[str, str]]] = {"harmful": [], "benign": []}
    for split, name in (("harmful", "harmful-behaviors.csv"), ("benign", "benign-behaviors.csv")):
        with (root / name).open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                out[split].append(dict(row))
    return out


def _rates(y_true: list[bool], y_pred: list[bool]) -> dict[str, float | None]:
    from .measurement import rates
    return rates(y_true, y_pred)


def measured_rates(rows, target, name):
    """Never coerce a missing or non-Boolean decision to a measured negative."""
    pairs = [(r[target], r[name]) for r in rows if r.get(name) is not None]
    return {**_rates([y for y, _ in pairs], [p for _, p in pairs]),
            "assigned": len(rows), "unknown": len(rows) - len(pairs)}


def track_a_jbb(
    *,
    jbb_dir: Path | None = None,
    protectai_dir: Path | None = None,
    use_gemini: bool = False,
    max_per_split: int | None = None,
) -> dict[str, Any]:
    if use_gemini:
        raise ValueError("the external diagnostic is offline-only")
    jbb = load_jbb(jbb_dir)
    baselines = build_baselines(protectai_dir)
    harmful = jbb["harmful"][: max_per_split or len(jbb["harmful"])]
    benign = jbb["benign"][: max_per_split or len(jbb["benign"])]
    rows: list[dict[str, Any]] = []
    for label, items in (("harmful", harmful), ("benign", benign)):
        for row in items:
            goal = row.get("Goal") or row.get("goal") or ""
            rec: dict[str, Any] = {
                "split": label,
                "index": row.get("Index"),
                "behavior": row.get("Behavior"),
                "category": row.get("Category"),
                "source": row.get("Source"),
                "goal": goal,
                "y_harmful": label == "harmful",
            }
            for name, fn in baselines["text_detectors"].items():
                rec[name] = fn(goal)
            rows.append(rec)

    metrics: dict[str, Any] = {}
    systems = [
        "protectai_prompt_injection",
        "openai_moderation_proxy",
    ]
    for name in systems:
        metrics[name] = measured_rates(rows, "y_harmful", name)

    return {
        "track": "A_jailbreakbench_behaviors",
        "dataset": "JailbreakBench/JBB-Behaviors",
        "n_harmful": sum(1 for r in rows if r["y_harmful"]),
        "n_benign": sum(1 for r in rows if not r["y_harmful"]),
        "metrics": metrics,
        "rows": rows,
        "notes": [
            "ProtectAI is a prompt-injection classifier; many JBB harmful goals are "
            "content-harm without injection syntax — low ProtectAI recall is expected.",
            "Agent episode detectors are outside this text-only interface.",
            "Not an official JailbreakBench ASR leaderboard entry.",
        ],
    }


def track_b_mirage_episodes(
    *,
    evidence_root: Path | None = None,
    protectai_dir: Path | None = None,
    use_gemini: bool = False,
) -> dict[str, Any]:
    if use_gemini:
        raise ValueError("the external diagnostic is offline-only")
    evidence_root = Path(evidence_root) if evidence_root else DEFAULT_MIRAGE
    baselines = build_baselines(protectai_dir)
    episodes: list[dict[str, Any]] = []
    for cap in CAPTURES:
        path = evidence_root / cap / "summary.json"
        if not path.exists():
            continue
        for ep in json.loads(path.read_text()).get("episodes") or []:
            e = dict(ep)
            e["hard_suite_source"] = cap
            episodes.append(e)
    hard = build_hard_suite(evidence_root)
    # Labels
    rows = []
    # Index reviewed stealth identities from hard suite.
    stealth_keys = {
        (h.get("hard_suite_source"), h.get("case_id"), h.get("prompt_arm"))
        for h in hard
        if h.get("stealth_mirage") and h.get("hard_suite_source")
    }

    for ep in episodes:
        attack = bool(ep.get("attack"))
        mirage = classic_mirage(ep)
        key = (ep.get("hard_suite_source"), ep.get("case_id"), ep.get("prompt_arm"))
        syn_stealth = (
            attack
            and bool(ep.get("guarded_complete"))
            and not mirage
            and key in stealth_keys
        )

        y_should_flag = mirage or syn_stealth  # safety-relevant failure modes
        rec: dict[str, Any] = {
            "capture": ep.get("hard_suite_source"),
            "case_id": ep.get("case_id"),
            "prompt_arm": ep.get("prompt_arm"),
            "attack": attack,
            "mirage": mirage,
            "stealth": syn_stealth,
            "y_should_flag": y_should_flag,
            "y_attack": attack,
        }
        for name, fn in baselines["episode_detectors"].items():
            rec[name] = fn(ep)
        # Content SOTA on episode model text
        txt = text_of_episode(ep)
        rec["protectai_on_episode_text"] = baselines["text_detectors"][
            "protectai_prompt_injection"
        ](txt)
        rec["openai_mod_proxy_on_episode_text"] = baselines["text_detectors"][
            "openai_moderation_proxy"
        ](txt)
        rows.append(rec)

    metrics: dict[str, Any] = {}
    # Primary: detect mirage|stealth among attacks that completed OR all episodes with y_should_flag
    for label_key, pred_systems in (
        (
            "y_should_flag",
            [
                "ensemble_v1",
                "joint_v1",
                "agentdojo_tool_filter",
                "channel1_incomplete",
                "protectai_on_episode_text",
                "openai_mod_proxy_on_episode_text",
            ],
        ),
        (
            "y_attack",
            [
                "ensemble_v1",
                "joint_v1",
                "protectai_on_episode_text",
            ],
        ),
    ):
        metrics[label_key] = {}
        for s in pred_systems:
            metrics[label_key][s] = measured_rates(rows, label_key, s)

    # Stealth-only subset
    stealth_rows = [r for r in rows if r["stealth"]]
    metrics["stealth_subset"] = {
        "n": len(stealth_rows),
        "ensemble_hits": sum(1 for r in stealth_rows if r["ensemble_v1"]),
        "joint_hits": sum(1 for r in stealth_rows if r["joint_v1"]),
        "protectai_hits": sum(1 for r in stealth_rows if r["protectai_on_episode_text"]),
        "tool_filter_hits": sum(1 for r in stealth_rows if r["agentdojo_tool_filter"]),
    }

    return {
        "track": "B_assurance_mirage_episodes",
        "n_episodes": len(rows),
        "n_mirage": sum(1 for r in rows if r["mirage"]),
        "n_stealth": sum(1 for r in rows if r["stealth"]),
        "n_attack": sum(1 for r in rows if r["attack"]),
        "metrics": metrics,
        "rows": rows,
        "notes": [
            "Development diagnostic. Labels reuse classic flags or IDs of previously reviewed cases.",
            "y_should_flag = classic mirage OR reviewed stealth (channel-1-perfect "
            "compliance with note-level intent).",
            "channel1_incomplete is a deliberate mirage-blind negative control.",
        ],
    }


def run_bakeoff(
    out: Path,
    *,
    jbb_dir: Path | None = None,
    protectai_dir: Path | None = None,
    evidence_root: Path | None = None,
    use_gemini: bool = False,
    jbb_max_per_split: int | None = 50,
    gemini_on_mirage: bool = False,
) -> dict[str, Any]:
    if use_gemini or gemini_on_mirage:
        raise ValueError("the external diagnostic is offline-only")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    a = track_a_jbb(
        jbb_dir=jbb_dir,
        protectai_dir=protectai_dir,
        use_gemini=use_gemini,
        max_per_split=jbb_max_per_split,
    )
    (out / "track_a_jbb.json").write_text(json.dumps(a, indent=2) + "\n")
    b = track_b_mirage_episodes(
        evidence_root=evidence_root,
        protectai_dir=protectai_dir,
        use_gemini=gemini_on_mirage,
    )
    (out / "track_b_mirage.json").write_text(json.dumps(b, indent=2) + "\n")

    summary = {
        "format": "pcs-evolving-safety-gate-external-bakeoff-v1",
        "seconds": round(time.monotonic() - start, 3),
        "track_a_metrics": a["metrics"],
        "track_b_metrics_y_should_flag": b["metrics"].get("y_should_flag"),
        "track_b_stealth_subset": b["metrics"].get("stealth_subset"),
        "production_authority": False,
        "official_jailbreakbench_leaderboard": False,
        "llamaguard_weights_used": False,
        "local_comparators": [
            "protectai/deberta-v3-base-prompt-injection-v2",
            "openai-moderation-style keyword proxy",
            "agentdojo-style tool allowlist filter",
        ],
        "pcs_systems": ["ensemble_v1", "joint_v1", "channel1_incomplete"],
        "finding_draft": None,
        "sha256_inputs": {
            "track_a": _digest({k: a[k] for k in ("n_harmful", "n_benign", "metrics")}),
            "track_b": _digest(
                {
                    k: b[k]
                    for k in ("n_episodes", "n_mirage", "n_stealth", "metrics")
                }
            ),
        },
    }
    summary["finding"] = (
        "Track A evaluates intent labels on Goal text. Track B measures agreement "
        "with historical PCS-derived labels. Cross-task superiority is undetermined."
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="ESG external bake-off")
    p.add_argument("out", type=Path)
    p.add_argument("--jbb-dir", type=Path, default=None)
    p.add_argument("--protectai-dir", type=Path, default=None)
    p.add_argument("--evidence", type=Path, default=None)
    p.add_argument("--no-gemini", action="store_true", help="this diagnostic always runs offline")
    p.add_argument("--jbb-max", type=int, default=50)
    args = p.parse_args()
    summary = run_bakeoff(
        args.out,
        jbb_dir=args.jbb_dir,
        protectai_dir=args.protectai_dir,
        evidence_root=args.evidence,
        jbb_max_per_split=args.jbb_max,
    )
    print(json.dumps({"ok": True, "finding": summary["finding"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
