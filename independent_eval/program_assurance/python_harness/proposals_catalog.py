"""Prioritized proposals catalog.

These entries are **proposals for future Codex/Aristotle work**, not claims that
the listed work is complete. The catalog is machine-readable JSON plus a
markdown rendering checked into ``proposals/``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CATALOG_FORMAT = "pcs-independent-program-proposals-v1"

# Static seed catalog shipped with Workstream E. Status is always "proposal".
DEFAULT_PROPOSALS: list[dict[str, Any]] = [
    {
        "id": "E-P01",
        "priority": 1,
        "title": "Case-insensitive path collision gate in CI",
        "status": "proposal",
        "workstream_affinity": ["program_assurance", "reviewer_adoption"],
        "summary": (
            "Wire the collision scanner as a required check on independent_eval/** "
            "so CHECKLIST.json vs checklist.json class failures are caught before merge."
        ),
        "rationale": (
            "Workstream D hit a repository-integrity failure from dual checklist "
            "filenames that collide on case-insensitive filesystems."
        ),
        "harness_local": "implemented_as_preflight_gate",
        "ci_wiring": "proposal",
        "not_claimed_done": True,
    },
    {
        "id": "E-P02",
        "priority": 1,
        "title": "Automated sibling-branch nonoverlap report in draft PR CI",
        "status": "proposal",
        "workstream_affinity": ["program_assurance"],
        "summary": (
            "Run the nonoverlap auditor against the known independent-eval branches "
            "(and PR #120 pilot) and fail soft with a posted artifact when overlaps appear."
        ),
        "rationale": (
            "Parallel workstreams A–D plus the scientific pilot must remain path-disjoint; "
            "manual NONOVERLAP.md alone does not detect drift."
        ),
        "harness_local": "implemented_as_preflight_gate",
        "ci_wiring": "proposal",
        "not_claimed_done": True,
    },
    {
        "id": "E-P03",
        "priority": 2,
        "title": "Cross-workstream inventory dashboard from PRESENT reports only",
        "status": "proposal",
        "workstream_affinity": ["program_assurance"],
        "summary": (
            "Publish a rolling program inventory that aggregates TEST_INVENTORY / "
            "BUGS / OPEN_TRUST_ASSUMPTIONS / TECHNICAL_REPORT when present, marking "
            "MISSING otherwise — never inventing counts."
        ),
        "rationale": (
            "Program-level assurance needs a single view without duplicating A–D harness code."
        ),
        "harness_local": "implemented_as_inventory_aggregator",
        "ci_wiring": "proposal",
        "not_claimed_done": True,
    },
    {
        "id": "E-P04",
        "priority": 2,
        "title": "Unified residual-trust rollup across OPEN_TRUST_ASSUMPTIONS",
        "status": "proposal",
        "workstream_affinity": ["repro_tcb", "program_assurance"],
        "summary": (
            "When sibling OPEN_TRUST_ASSUMPTIONS.md files exist, extract structured "
            "assumption IDs into a program-level residual-trust index."
        ),
        "rationale": (
            "Trust boundaries are currently per-workstream; synthesis is needed for "
            "Codex/Aristotle follow-on formalization proposals."
        ),
        "harness_local": "implemented_as_residual_trust_rollup",
        "ci_wiring": "proposal",
        "not_claimed_done": True,
    },
    {
        "id": "E-P05",
        "priority": 3,
        "title": "Adversarial protocol corpus expansion beyond JCS/ZIP fixtures",
        "status": "proposal",
        "workstream_affinity": ["protocol_adversarial"],
        "summary": (
            "Continue expanding malformed-intake / signature / lock mutation families "
            "on Workstream A; treat further growth as ongoing evaluation, not a security proof."
        ),
        "rationale": "Protocol surface area grows with new claim kinds and archive encodings.",
        "harness_local": "partially_addressed_on_workstream_A",
        "ci_wiring": "n/a",
        "not_claimed_done": True,
    },
    {
        "id": "E-P06",
        "priority": 3,
        "title": "External-lab burden measurement with human participants",
        "status": "proposal",
        "workstream_affinity": ["reviewer_adoption"],
        "summary": (
            "Use the external_lab kit to run a real participant study; do not treat "
            "checklist completion as EXTERNAL_VALIDATION_COMPLETE."
        ),
        "rationale": (
            "Workstream D intentionally forbids claiming completed external validation "
            "from synthetic fixtures alone."
        ),
        "not_claimed_done": True,
    },
    {
        "id": "E-P07",
        "priority": 3,
        "title": "Aristotle-facing formalization candidates from inadequacy examples",
        "status": "proposal",
        "workstream_affinity": ["scientific_falsification", "program_assurance"],
        "summary": (
            "Catalog computationally-supported-but-inadequate cases as candidate "
            "proof obligations for future formal work — labeled proposals only."
        ),
        "rationale": (
            "Scientific falsification surfaces gaps between computational support and "
            "empirical adequacy that formal methods might later address."
        ),
        "harness_local": "partially_addressed_on_workstream_B_aristotle_candidates",
        "ci_wiring": "n/a",
        "not_claimed_done": True,
    },
    {
        "id": "E-P08",
        "priority": 4,
        "title": "Reconstruction campaign across additional Python/OS matrices",
        "status": "proposal",
        "workstream_affinity": ["repro_tcb"],
        "summary": (
            "Extend cross-environment reconstruction sampling when alternate "
            "interpreters/hosts are available; record absences rather than treating "
            "them as passes."
        ),
        "rationale": "TCB residual trust shrinks only with measured environments.",
        "harness_local": "partially_addressed_on_workstream_C_interpreter_matrix",
        "ci_wiring": "n/a",
        "not_claimed_done": True,
    },
    {
        "id": "E-P09",
        "priority": 2,
        "title": "Offline assurance card for external reviewers",
        "status": "proposal",
        "workstream_affinity": ["assurance_card", "reviewer_adoption", "program_assurance"],
        "summary": (
            "Ship a one-command JSON/HTML assurance card that separates authority-lane "
            "`pcs verify` from non-authority inspection classes for any evidence bundle."
        ),
        "rationale": (
            "Reviewers need a single offline artifact that is usable without learning "
            "the full PCS toolchain, without conflating inspection with acceptance."
        ),
        "harness_local": "implemented_as_workstream_F_assurance_card",
        "ci_wiring": "proposal",
        "not_claimed_done": True,
    },
]


def build_catalog(proposals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    items = proposals if proposals is not None else list(DEFAULT_PROPOSALS)
    for item in items:
        if item.get("status") != "proposal":
            raise ValueError(f"{item.get('id')}: status must be 'proposal' (not a completion claim)")
        if not item.get("not_claimed_done", False):
            raise ValueError(f"{item.get('id')}: not_claimed_done must be true")
    ordered = sorted(items, key=lambda p: (p.get("priority", 99), p.get("id", "")))
    return {
        "format": CATALOG_FORMAT,
        "disclaimer": (
            "PROPOSALS ONLY — entries describe candidate future Codex/Aristotle work. "
            "None of these items are claimed as completed evaluation results."
        ),
        "proposal_count": len(ordered),
        "proposals": ordered,
    }


def render_proposals_markdown(catalog: dict[str, Any]) -> str:
    lines = [
        "# Prioritized proposals catalog",
        "",
        f"**{catalog['disclaimer']}**",
        "",
        f"Format: `{catalog['format']}`",
        f"Proposal count: {catalog['proposal_count']}",
        "",
        "| ID | Priority | Title | Affinity | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for p in catalog["proposals"]:
        affinity = ", ".join(p.get("workstream_affinity") or [])
        lines.append(
            f"| `{p['id']}` | {p['priority']} | {p['title']} | {affinity} | `{p['status']}` |"
        )
    lines.extend(["", "## Details", ""])
    for p in catalog["proposals"]:
        lines.extend(
            [
                f"### {p['id']} — {p['title']}",
                "",
                f"- **Priority:** {p['priority']}",
                f"- **Status:** `{p['status']}` (proposal — not claimed done)",
                f"- **Affinity:** {', '.join(p.get('workstream_affinity') or [])}",
                f"- **Summary:** {p['summary']}",
                f"- **Rationale:** {p['rationale']}",
                "",
            ]
        )
    return "\n".join(lines)


def write_catalog(
    *,
    json_path: Path | str,
    md_path: Path | str,
    proposals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    catalog = build_catalog(proposals)
    jp = Path(json_path)
    mp = Path(md_path)
    jp.parent.mkdir(parents=True, exist_ok=True)
    mp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mp.write_text(render_proposals_markdown(catalog), encoding="utf-8")
    return catalog


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .paths import PROPOSALS_DIR, RESULTS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=PROPOSALS_DIR / "PROPOSALS.json",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=PROPOSALS_DIR / "PROPOSALS.md",
    )
    parser.add_argument(
        "--results-copy",
        type=Path,
        default=RESULTS / "proposals_catalog.json",
        help="Also write a copy under results/ for run_all artifacts",
    )
    args = parser.parse_args(argv)

    catalog = write_catalog(json_path=args.json_out, md_path=args.md_out)
    if args.results_copy:
        args.results_copy.parent.mkdir(parents=True, exist_ok=True)
        args.results_copy.write_text(
            json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(catalog, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
