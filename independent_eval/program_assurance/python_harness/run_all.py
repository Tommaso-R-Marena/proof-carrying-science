"""Smoke entrypoint: run all Workstream E assurance synthesizers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .inventory_aggregator import (
    aggregate_inventory,
    render_inventory_markdown,
    write_inventory_report,
)
from .paths import (
    INVENTORY_REPORT_NAMES,
    PROPOSALS_DIR,
    REPO_ROOT,
    RESULTS,
    ROOT,
    SIBLING_PREFIXES,
)
from .preflight import run_preflight
from .proposals_catalog import write_catalog


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    del argv  # smoke entry takes no flags for now
    RESULTS.mkdir(parents=True, exist_ok=True)

    # Soft mode for smoke summary so missing remote refs don't fail the campaign;
    # use ``python -m python_harness.preflight`` for hard gates.
    preflight = run_preflight(
        fail_on_overlap=False,
        fail_on_collision=False,
    )

    inventory = aggregate_inventory(
        repo=REPO_ROOT,
        prefixes=SIBLING_PREFIXES,
        report_names=INVENTORY_REPORT_NAMES,
    )
    write_inventory_report(inventory, RESULTS / "program_inventory.json")
    (RESULTS / "program_inventory.md").write_text(
        render_inventory_markdown(inventory), encoding="utf-8"
    )

    catalog = write_catalog(
        json_path=PROPOSALS_DIR / "PROPOSALS.json",
        md_path=PROPOSALS_DIR / "PROPOSALS.md",
    )
    (RESULTS / "proposals_catalog.json").write_text(
        json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    collision_gate = preflight["gates"].get("path_collision", {})
    nonoverlap_gate = preflight["gates"].get("branch_nonoverlap", {})
    trust_gate = preflight["gates"].get("residual_trust", {})

    summary = {
        "format": "pcs-independent-program-assurance-summary-v1",
        "repo_head": _git_head(),
        "root": str(ROOT.relative_to(REPO_ROOT)),
        "path_collision": {
            "file_count": collision_gate.get("file_count"),
            "collision_group_count": collision_gate.get("collision_group_count"),
            "has_collisions": not collision_gate.get("pass", True),
        },
        "branch_nonoverlap": {
            "branches_audited": nonoverlap_gate.get("pair_count"),
            "missing_branches": nonoverlap_gate.get("missing_branches", []),
            "has_overlaps": nonoverlap_gate.get("has_overlaps"),
            "pair_count": nonoverlap_gate.get("pair_count"),
        },
        "residual_trust": {
            "sources_present": trust_gate.get("sources_present"),
            "sources_missing": trust_gate.get("sources_missing"),
            "assumption_id_count": trust_gate.get("assumption_id_count"),
            "tcb_closed": False,
        },
        "inventory": {
            "prefixes_present": inventory.to_dict()["prefixes_present"],
            "prefixes_missing": inventory.to_dict()["prefixes_missing"],
        },
        "proposals": {
            "proposal_count": catalog["proposal_count"],
            "status": "proposal_catalog_only",
        },
        "preflight_soft_pass": preflight["pass"],
        "disclaimer": (
            "Program assurance synthesizes presence/overlap/collision/trust signals and "
            "proposal catalogs. It does not re-run A–D evaluation harnesses or "
            "claim their findings as completed here. Use python_harness.preflight for hard gates."
        ),
    }
    (RESULTS / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
