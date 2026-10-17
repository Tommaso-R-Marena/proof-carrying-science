"""Smoke entrypoint: run all Workstream E assurance synthesizers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .collision_scanner import scan_path_collisions, write_collision_report
from .inventory_aggregator import (
    aggregate_inventory,
    render_inventory_markdown,
    write_inventory_report,
)
from .nonoverlap_auditor import audit_branch_nonoverlap, write_nonoverlap_report
from .paths import (
    INDEPENDENT_EVAL,
    INVENTORY_REPORT_NAMES,
    PROPOSALS_DIR,
    REPO_ROOT,
    RESULTS,
    ROOT,
    SIBLING_BRANCHES,
    SIBLING_PREFIXES,
)
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

    collision = scan_path_collisions(INDEPENDENT_EVAL if INDEPENDENT_EVAL.exists() else ROOT)
    write_collision_report(collision, RESULTS / "path_collision_report.json")

    nonoverlap = audit_branch_nonoverlap(SIBLING_BRANCHES, repo=REPO_ROOT)
    write_nonoverlap_report(nonoverlap, RESULTS / "branch_nonoverlap_report.json")

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

    summary = {
        "format": "pcs-independent-program-assurance-summary-v1",
        "repo_head": _git_head(),
        "root": str(ROOT.relative_to(REPO_ROOT)),
        "path_collision": {
            "file_count": collision.file_count,
            "collision_group_count": len(collision.collision_groups),
            "has_collisions": collision.has_collisions,
        },
        "branch_nonoverlap": {
            "branches_audited": len(nonoverlap.changed_files),
            "missing_branches": list(nonoverlap.missing_branches),
            "has_overlaps": nonoverlap.has_overlaps,
            "pair_count": len(nonoverlap.pair_overlaps),
        },
        "inventory": {
            "prefixes_present": inventory.to_dict()["prefixes_present"],
            "prefixes_missing": inventory.to_dict()["prefixes_missing"],
        },
        "proposals": {
            "proposal_count": catalog["proposal_count"],
            "status": "proposal_catalog_only",
        },
        "disclaimer": (
            "Program assurance synthesizes presence/overlap/collision signals and "
            "proposal catalogs. It does not re-run A–D evaluation harnesses or "
            "claim their findings as completed here."
        ),
    }
    (RESULTS / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
