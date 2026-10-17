"""Unified residual-trust rollup across sibling OPEN_TRUST_ASSUMPTIONS.md files.

Reads sibling files from the working tree when present, otherwise via
``git show origin/<branch>:<path>`` (read-only). Never invents assumption
closures or claims that residual TCB is empty.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .paths import REPO_ROOT, SIBLING_BRANCHES

ASSUMPTION_ID = re.compile(
    r"`(?P<id>[A-Za-z][A-Za-z0-9_./-]{1,80})`|"
    r"^\|\s*`?(?P<id2>[A-Za-z][A-Za-z0-9_./-]{1,80})`?\s*\|",
    re.MULTILINE,
)

# Known locations of trust inventories (path relative to repo root → preferred branch).
TRUST_SOURCES: tuple[dict[str, str], ...] = (
    {
        "path": "independent_eval/repro_tcb/OPEN_TRUST_ASSUMPTIONS.md",
        "branch": "feature/independent-eval-repro-tcb-c8bb",
        "workstream": "repro_tcb",
    },
    {
        "path": "independent_eval/scientific_falsification/TECHNICAL_REPORT.md",
        "branch": "feature/independent-eval-scientific-falsification-c8bb",
        "workstream": "scientific_falsification",
        "section_hint": "Non-claims",
    },
    {
        "path": "independent_eval/protocol_adversarial/TECHNICAL_REPORT.md",
        "branch": "feature/independent-eval-protocol-adversarial-c8bb",
        "workstream": "protocol_adversarial",
    },
    {
        "path": "independent_eval/reviewer_adoption/TECHNICAL_REPORT.md",
        "branch": "feature/independent-eval-reviewer-adoption-c8bb",
        "workstream": "reviewer_adoption",
    },
)


def _read_working_tree(repo: Path, rel: str) -> str | None:
    path = repo / rel
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def _git_show(repo: Path, branch: str, rel: str) -> str | None:
    for ref in (f"origin/{branch}", branch):
        proc = subprocess.run(
            ["git", "show", f"{ref}:{rel}"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
    return None


def extract_assumption_ids(text: str) -> list[str]:
    """Extract likely assumption / theorem IDs from markdown tables and backticks."""
    found: list[str] = []
    seen: set[str] = set()
    for match in ASSUMPTION_ID.finditer(text):
        value = match.group("id") or match.group("id2")
        if not value:
            continue
        # Filter common markdown noise.
        if value.lower() in {"id", "meaning", "path", "task", "status", "title"}:
            continue
        if value not in seen:
            seen.add(value)
            found.append(value)
    return found


def rollup_residual_trust(repo: Path | None = None) -> dict[str, Any]:
    root = repo or REPO_ROOT
    sources: list[dict[str, Any]] = []
    present = 0
    missing = 0
    all_ids: list[str] = []
    id_seen: set[str] = set()

    for spec in TRUST_SOURCES:
        rel = spec["path"]
        text = _read_working_tree(root, rel)
        origin = "working_tree"
        if text is None:
            text = _git_show(root, spec["branch"], rel)
            origin = "git_show"
        if text is None:
            missing += 1
            sources.append(
                {
                    "path": rel,
                    "branch": spec["branch"],
                    "workstream": spec["workstream"],
                    "status": "MISSING",
                    "origin": None,
                    "assumption_ids": [],
                }
            )
            continue
        present += 1
        ids = extract_assumption_ids(text)
        for item in ids:
            if item not in id_seen:
                id_seen.add(item)
                all_ids.append(item)
        sources.append(
            {
                "path": rel,
                "branch": spec["branch"],
                "workstream": spec["workstream"],
                "status": "PRESENT",
                "origin": origin,
                "assumption_ids": ids,
                "assumption_id_count": len(ids),
            }
        )

    return {
        "format": "pcs-independent-residual-trust-rollup-v1",
        "sources_present": present,
        "sources_missing": missing,
        "assumption_id_count": len(all_ids),
        "assumption_ids": all_ids,
        "sources": sources,
        "sibling_branches_known": list(SIBLING_BRANCHES),
        "tcb_closed": False,
        "disclaimer": (
            "Informational rollup only. Presence of assumption IDs does not mean "
            "they are discharged. tcb_closed is always false in this harness."
        ),
    }


def write_residual_trust_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
