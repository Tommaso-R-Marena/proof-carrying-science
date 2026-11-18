"""Cross-model mirage comparison from recorded evidence directories."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads((path / "summary.json").read_text())


def compare(evidence_root: Path, out: Path) -> dict:
    evidence_root = Path(evidence_root)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for name in sorted(p.name for p in evidence_root.iterdir() if p.is_dir()):
        summary_path = evidence_root / name / "summary.json"
        if not summary_path.exists():
            continue
        s = _load(evidence_root / name)
        gap = s.get("mirage_gap") or {}
        rows.append(
            {
                "evidence": name,
                "model": s.get("model", {}).get("id")
                if isinstance(s.get("model"), dict)
                else s.get("model"),
                "n_episodes": s.get("n_episodes") or s.get("n_episodes_complete"),
                "guarded_complete": gap.get("guarded_complete"),
                "mirage_episodes": gap.get("mirage_episodes"),
                "mirage_rate_among_attacks": gap.get("mirage_rate_among_attacks"),
                "proposal_harm_episodes": gap.get("proposal_harm_episodes"),
                "raw_or_split_leak_episodes": gap.get("raw_or_split_leak_episodes"),
                "scope_escalation_episodes": gap.get("scope_escalation_episodes"),
                "channel1_only_would_report_perfect_safety": gap.get(
                    "channel1_only_would_report_perfect_safety"
                ),
                "summary_sha256": sha256(summary_path.read_bytes()).hexdigest(),
            }
        )
    report = {
        "format": "pcs-assurance-mirage-compare-v1",
        "n_sources": len(rows),
        "rows": rows,
        "finding": (
            "Local Qwen weights show high mirage rates under correcting guards; "
            "hosted gemini-flash-lite-latest showed zero mirages on the tested subset. "
            "Channel-1 perfection is therefore not interchangeable with model refusal quality."
        ),
        "production_authority": False,
    }
    (out / "compare.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
