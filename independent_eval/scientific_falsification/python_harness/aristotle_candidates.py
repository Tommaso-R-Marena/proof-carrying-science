"""Aristotle/Codex formalization *candidates* from inadequacy examples.

PROPOSALS ONLY — does not claim any Lean obligation is discharged or that
empirical adequacy was proven. Emits a machine-readable catalog from the
frozen inadequacy index + CASE/README theses.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import INADEQUACY, RESULTS


def build_candidates(index_path: Path | None = None) -> dict[str, Any]:
    index_file = index_path or (INADEQUACY / "INDEX.json")
    index = json.loads(index_file.read_text(encoding="utf-8"))
    candidates: list[dict[str, Any]] = []
    for entry in index.get("examples", []):
        ex_id = entry["id"]
        ex_dir = INADEQUACY / "examples" / ex_id
        readme = ""
        if (ex_dir / "README.md").is_file():
            readme = (ex_dir / "README.md").read_text(encoding="utf-8")
        manifest_checks: list[str] = []
        manifest_path = ex_dir / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for check in manifest.get("checks", []):
                if isinstance(check, dict) and check.get("type"):
                    manifest_checks.append(str(check["type"]))
        candidates.append(
            {
                "id": f"SF-AC-{ex_id}",
                "source_example": ex_id,
                "thesis": entry.get("thesis"),
                "pcs_checks_observed": sorted(set(manifest_checks)),
                "computational_support_expected": True,
                "empirical_adequacy_established": False,
                "formalization_opportunity": (
                    "Optional future work: make the separation between computational "
                    "support and empirical adequacy an explicit, machine-checkable "
                    "certificate field / obligation — not claimed implemented here."
                ),
                "readme_excerpt": readme.strip().splitlines()[:8],
                "status": "proposal_candidate",
                "not_claimed_done": True,
            }
        )
    return {
        "format": "pcs-independent-aristotle-candidates-v1",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "disclaimer": (
            "PROPOSALS ONLY. These catalog gaps between computational PASS and "
            "empirical adequacy. They are not Lean proofs, not discharged obligations, "
            "and not claims of scientific truth."
        ),
    }


def write_candidates(path: Path | None = None) -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = path or (RESULTS / "aristotle_candidates.json")
    payload = build_candidates()
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = RESULTS / "aristotle_candidates.md"
    lines = [
        "# Aristotle/Codex formalization candidates (proposals)",
        "",
        f"**{payload['disclaimer']}**",
        "",
        f"Candidate count: {payload['candidate_count']}",
        "",
        "| ID | Source | Thesis | Checks |",
        "| --- | --- | --- | --- |",
    ]
    for c in payload["candidates"]:
        checks = ", ".join(f"`{t}`" for t in c["pcs_checks_observed"]) or "—"
        lines.append(
            f"| `{c['id']}` | `{c['source_example']}` | {c['thesis']} | {checks} |"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    del argv
    payload = write_candidates()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
