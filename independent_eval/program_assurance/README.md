# Workstream E — Program-level assurance synthesis

Cross-cutting evaluation **infrastructure** for the PCS independent evaluation
program. This package does **not** duplicate Workstreams A–D harnesses; it
synthesizes collision, non-overlap, inventory, and proposal signals.

```bash
PYTHONPATH=independent_eval/program_assurance \
  python3 -m pytest -q independent_eval/program_assurance/tests

PYTHONPATH=independent_eval/program_assurance \
  python3 -m python_harness.run_all
```

| Doc | Purpose |
| --- | --- |
| `NONOVERLAP.md` | Writable scope vs forbidden trees / sibling PRs |
| `TEST_INVENTORY.md` | Collected pytest node ids |
| `TECHNICAL_REPORT.md` | Synthesis findings and method |
| `BUGS_AND_AMBIGUITIES.md` | Ambiguities and observed hazards |
| `proposals/PROPOSALS.{json,md}` | Prioritized **proposals** (not completed work) |

## Components

1. **Path collision scanner** (`python_harness/collision_scanner.py`) — case-insensitive path collision detection for any tree (default `independent_eval/`).
2. **Branch nonoverlap auditor** (`python_harness/nonoverlap_auditor.py`) — read-only `git diff --name-only origin/main...<branch>` pairwise overlap report.
3. **Program inventory aggregator** (`python_harness/inventory_aggregator.py`) — reads sibling reports **if present**; records `MISSING` otherwise (never invents counts).
4. **Proposals catalog** (`python_harness/proposals_catalog.py`) — machine-readable future-work proposals for Codex/Aristotle.

## Sibling prefixes (read-only; not created here)

- `independent_eval/protocol_adversarial/`
- `independent_eval/scientific_falsification/`
- `independent_eval/repro_tcb/`
- `independent_eval/reviewer_adoption/`
