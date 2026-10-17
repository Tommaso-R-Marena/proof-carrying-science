"""Filesystem anchors for the program_assurance package."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
INDEPENDENT_EVAL = REPO_ROOT / "independent_eval"
RESULTS = ROOT / "results"
PROPOSALS_DIR = ROOT / "proposals"

# Sibling workstream prefixes (do not create their content from this package).
SIBLING_PREFIXES: tuple[str, ...] = (
    "independent_eval/protocol_adversarial",
    "independent_eval/scientific_falsification",
    "independent_eval/repro_tcb",
    "independent_eval/reviewer_adoption",
)

SIBLING_BRANCHES: tuple[str, ...] = (
    "feature/independent-eval-protocol-adversarial-c8bb",
    "feature/independent-eval-scientific-falsification-c8bb",
    "feature/independent-eval-repro-tcb-c8bb",
    "feature/independent-eval-reviewer-adoption-c8bb",
    "feature/independent-eval-program-assurance-c8bb",
    "feature/independent-scientific-pilot-c8bb",
)

# Report filenames looked up under each sibling prefix when present.
INVENTORY_REPORT_NAMES: tuple[str, ...] = (
    "TEST_INVENTORY.md",
    "BUGS_AND_AMBIGUITIES.md",
    "OPEN_TRUST_ASSUMPTIONS.md",
    "TECHNICAL_REPORT.md",
)
