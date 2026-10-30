# TECHNICAL_REPORT — Workstream E (program assurance)

## Scope

Program-level assurance synthesis for the PCS independent evaluation effort.
Deliverables are infrastructure and reporting only:

| Component | Input | Output |
| --- | --- | --- |
| Path collision scanner | Any filesystem tree (default `independent_eval/`) | JSON collision groups |
| Branch nonoverlap auditor | Known sibling branch names | Pairwise changed-file overlaps |
| Inventory aggregator | Sibling report files if present | PRESENT/MISSING matrix |
| Proposals catalog | Static prioritized seed list | `PROPOSALS.json` + `.md` |

## Method

### Collision scanner

Walk files under a root, skipping cache/VCS directories. Group by
`relative_path.casefold()`. Any group with more than one distinct relative path
is a collision (e.g. `…/CHECKLIST.json` vs `…/checklist.json`).

### Nonoverlap auditor

For each configured branch, run read-only:

```bash
git diff --name-only origin/main...<branch>
```

Compute pairwise intersections of changed-file sets. Missing refs are recorded
as `MISSING` / `missing_branches`, not as empty diffs.

Default branch set:

- `feature/independent-eval-protocol-adversarial-c8bb`
- `feature/independent-eval-scientific-falsification-c8bb`
- `feature/independent-eval-repro-tcb-c8bb`
- `feature/independent-eval-reviewer-adoption-c8bb`
- `feature/independent-scientific-pilot-c8bb` (PR #120)

### Inventory aggregator

Under each of:

- `independent_eval/protocol_adversarial/`
- `independent_eval/scientific_falsification/`
- `independent_eval/repro_tcb/`
- `independent_eval/reviewer_adoption/`

probe for `TEST_INVENTORY.md`, `BUGS_AND_AMBIGUITIES.md`,
`OPEN_TRUST_ASSUMPTIONS.md`, and `TECHNICAL_REPORT.md`. When
`TEST_INVENTORY.md` is present and contains a `Collected tests: N` line, record
`N`; otherwise do not invent a count.

### Proposals catalog

Seeded proposals (`E-P01` …) are labeled `status: proposal` with
`not_claimed_done: true`. They prioritize CI gates, inventory dashboards,
residual-trust rollups, and future Codex/Aristotle formalization candidates.

## Results (this package)

See `results/SUMMARY.json` after:

```bash
PYTHONPATH=independent_eval/program_assurance python3 -m python_harness.run_all
```

On an isolated Workstream E checkout, sibling prefixes are expected to be
`MISSING` unless other worktrees are overlaid. Collision scan of this package
tree alone should report zero collisions. Nonoverlap against remote sibling
branches is informational when those refs are fetched.

## Non-claims

- Does not claim A–D evaluation campaigns are complete.
- Does not claim external-lab or human-reviewer validation.
- Does not modify production PCS, Lean, or CI trees.
