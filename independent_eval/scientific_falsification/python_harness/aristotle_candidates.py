"""Aristotle/Codex formalization *candidates* from inadequacy examples.

PROPOSALS ONLY — does not claim any Lean obligation is discharged or that
empirical adequacy was proven. Emits a machine-readable catalog from the
frozen inadequacy index + CASE/README theses.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical_seal import seal_artifact
from .paths import INADEQUACY, RESULTS

# Keyword → proposed obligation family (still proposal_candidate only).
_OBLIGATION_HINTS: tuple[tuple[str, str, str], ...] = (
    (
        "unit",
        "obligation_units_vs_quantity_adequacy",
        "Separate unit-compatibility checks from quantity/adequacy claims.",
    ),
    (
        "cohort",
        "obligation_cohort_representativeness",
        "Make train/test disjointness insufficient for sampling adequacy.",
    ),
    (
        "bias",
        "obligation_cohort_representativeness",
        "Make train/test disjointness insufficient for sampling adequacy.",
    ),
    (
        "threshold",
        "obligation_threshold_empirical_binding",
        "Bind declared thresholds to empirical evidence obligations.",
    ),
    (
        "pk",
        "obligation_model_form_vs_biology",
        "Distinguish kinetic model form checks from biological adequacy.",
    ),
    (
        "clearance",
        "obligation_model_form_vs_biology",
        "Distinguish kinetic model form checks from biological adequacy.",
    ),
)


def _obligation_sketch(thesis: str | None, checks: list[str]) -> dict[str, Any]:
    text = f"{thesis or ''} {' '.join(checks)}".lower()
    families: list[str] = []
    sketches: list[str] = []
    for needle, family, sketch in _OBLIGATION_HINTS:
        if needle in text and family not in families:
            families.append(family)
            sketches.append(sketch)
    if not families:
        families.append("obligation_computational_vs_empirical_separation")
        sketches.append(
            "Expose computational support vs empirical adequacy as distinct fields."
        )
    # Priority: more specific families first; count of matched hints as weight.
    return {
        "proposed_obligation_families": families,
        "obligation_sketches": sketches,
        "priority": min(5, max(1, len(families) + (1 if len(checks) >= 2 else 0))),
        "inspection_class": "scientific_adequacy_open",
        "discharged": False,
    }


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
        checks = sorted(set(manifest_checks))
        sketch = _obligation_sketch(entry.get("thesis"), checks)
        candidates.append(
            {
                "id": f"SF-AC-{ex_id}",
                "source_example": ex_id,
                "thesis": entry.get("thesis"),
                "pcs_checks_observed": checks,
                "computational_support_expected": True,
                "empirical_adequacy_established": False,
                "formalization_opportunity": (
                    "Optional future work: make the separation between computational "
                    "support and empirical adequacy an explicit, machine-checkable "
                    "certificate field / obligation — not claimed implemented here."
                ),
                "proposed_obligation": sketch,
                "readme_excerpt": readme.strip().splitlines()[:8],
                "status": "proposal_candidate",
                "not_claimed_done": True,
            }
        )
    payload = {
        "format": "pcs-independent-aristotle-candidates-v1",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "disclaimer": (
            "PROPOSALS ONLY. These catalog gaps between computational PASS and "
            "empirical adequacy. They are not Lean proofs, not discharged obligations, "
            "and not claims of scientific truth."
        ),
        "issues_accept": False,
    }
    return seal_artifact(payload)


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
        "| ID | Source | Thesis | Checks | Proposed obligation | Priority |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in payload["candidates"]:
        checks = ", ".join(f"`{t}`" for t in c["pcs_checks_observed"]) or "—"
        prop = c.get("proposed_obligation") or {}
        fams = ", ".join(
            f"`{f}`" for f in (prop.get("proposed_obligation_families") or [])
        ) or "—"
        lines.append(
            f"| `{c['id']}` | `{c['source_example']}` | {c['thesis']} | {checks} "
            f"| {fams} | {prop.get('priority', '—')} |"
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
