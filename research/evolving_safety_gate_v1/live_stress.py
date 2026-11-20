"""Optional live stress of the evolved champion against hosted Gemini.

Uses the Assurance Mirage gemini arm with a hard request cap. Never stores API keys.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research.assurance_mirage_v1.gemini_arm import run_gemini_arm

from .catalog import Candidate, detector_for


def stress_champion_gemini(
    champion: Candidate,
    out: Path,
    *,
    case_ids: list[str] | None = None,
    prompt_arm: str = "instruction_boundary",
    max_requests: int = 12,
) -> dict[str, Any]:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    ids = case_ids or ["direct-exfil", "many-shot-jailbreak", "policy-puppetry"]
    summary = run_gemini_arm(
        out / "gemini-wave",
        case_ids=ids,
        prompt_arm=prompt_arm,
        turns=4,
        max_requests=max_requests,
        min_interval_sec=6.0,
    )
    detect = detector_for(champion)
    flagged = [e for e in summary.get("episodes") or [] if detect(e)]
    report = {
        "format": "pcs-evolving-safety-gate-live-stress-v1",
        "champion_id": champion.id,
        "n_episodes": summary.get("n_episodes_complete"),
        "champion_flags": len(flagged),
        "mirage_gap": summary.get("mirage_gap"),
        "requests_used": (summary.get("free_tier_policy") or {}).get(
            "requests_used_this_session"
        ),
        "interpretation": (
            "Zero champion flags on Gemini with zero mirages is consistent; "
            "flags without mirage labels would be false positives."
        ),
        "api_key_not_stored": True,
        "production_authority": False,
    }
    (out / "live_stress.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
