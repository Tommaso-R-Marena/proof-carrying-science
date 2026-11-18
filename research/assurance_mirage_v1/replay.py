"""Replay recorded campaign metrics without reloading model weights."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from .channels import EpisodeResult, ProposalRecord, mirage_gap
from .formal_check import check_formal


def digest(b: bytes) -> str:
    return sha256(b).hexdigest()


def _episode_from_json(d: dict) -> EpisodeResult:
    ep = EpisodeResult(
        case_id=d["case_id"],
        family=d["family"],
        attack=d["attack"],
        prompt_arm=d["prompt_arm"],
        tools=[tuple(t) for t in d["tools"]],
        proposals=[ProposalRecord(**p) for p in d["proposals"]],
        published=list(d.get("published", [])),
        raw_leak=d.get("raw_leak", False),
        split_leak=d.get("split_leak", False),
        scope_escalation=d.get("scope_escalation", False),
    )
    ep.finalize()
    return ep


def replay_campaign(capture: Path, out: Path) -> dict:
    capture = Path(capture)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    summary = json.loads((capture / "summary.json").read_text())
    formal = check_formal(out / "formal-build")
    if formal["source_sha256"] != summary["formal"]["source_sha256"]:
        raise ValueError("Formal source digest drifted from captured campaign")
    episodes = [_episode_from_json(e) for e in summary["episodes"]]
    gap = mirage_gap(episodes)
    # Channel-1 perfection under mirages must match the recorded boolean if present.
    recomputed = {
        "format": "pcs-assurance-mirage-replay-v1",
        "capture_summary_sha256": digest((capture / "summary.json").read_bytes()),
        "formal": formal,
        "n_episodes": len(episodes),
        "mirage_gap": gap,
        "matches_capture_mirage_gap": gap == summary["mirage_gap"],
        "production_authority": False,
    }
    if not recomputed["matches_capture_mirage_gap"]:
        # Allow joint_score field drift only if core counters match.
        keys = [
            "n_episodes",
            "guarded_complete",
            "proposal_harm_episodes",
            "raw_or_split_leak_episodes",
            "scope_escalation_episodes",
            "mirage_episodes",
        ]
        if any(gap[k] != summary["mirage_gap"][k] for k in keys):
            raise ValueError("Recomputed mirage gap diverges from capture")
    (out / "replay.json").write_text(json.dumps(recomputed, indent=2) + "\n")
    return recomputed
