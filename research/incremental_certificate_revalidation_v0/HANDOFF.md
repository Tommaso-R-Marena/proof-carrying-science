# HANDOFF — Incremental Certificate Revalidation v0

## Branch / commits

- **Branch:** `research/pcs-incremental-revalidation-v0`
- **Draft PR:** https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/217
- **Tip:** recorded in `results/HEAD_COMMIT.txt` (do not chase SHA in this file)
- **Worktree:** `/home/ubuntu/worktrees/pcs-incremental-revalidation-v0`
- **Base main:** `bc78660b5fac857fce3873eb6cda0445d1903da1`
- **Exclusive path:** `research/incremental_certificate_revalidation_v0/` only

## Completed

- [x] Overlap audit; exclusive namespace; draft PR #217
- [x] Substantive `IncrementalAccept` + `incremental_implies_fresh` (non-vacuous)
- [x] **GC-II:** assumption audit (logical vs operational); evidence-bound LocalCheck
- [x] **GC-II:** `Algorithm.lean` — `computeChanges` complete, `runIncremental`, `incremental_run_sound`
- [x] **GC-II:** Python `compute_changes` / atomic ValidState commit; evidence/atomic tests
- [x] New-graph invalidation; assumption-removal counterexamples
- [x] Cheap-ops slowdown preserved; synthetic expensive-check speedups labeled
- [x] PRIOR_ART survey draft; baseline/progress docs

## Proven theorems (Lean)

`logical_implies_fresh`, `incremental_implies_fresh`, `reuse_entry_checks` (evidence-bound),
`computeChanges_complete`, `runIncremental_changes_complete`, `incremental_run_sound`,
`affectedClosure_step_sound`, invalidation sound/complete, `affected_least`,
`new_edge_requires_new_graph_invalidation`, eligibility/non-escalation families,
`executableAcceptImpliesLeanFresh`. No sorry/admit/custom axioms.

## Implemented but unproved

- `runIncremental` ok ⇒ constructed `LogicalAccept` (bridge)
- Python affected-closure ≡ Lean `Affected` (differentially tested)
- Full Python⇒Lean refinement
- Real Lean-kernel performance advantage (synthetic only so far)

## Tests

- pytest: 22 passed (core, differential, adversarial, assumption, evidence/atomic)
- `lake build` green

## CI

- Research/portability checks green
- `source-policy` / `verified-public-integration` fail on sealed census (**expected**; do not weaken)

## Next highest-value objectives

1. Bridge `runIncremental` ok ⇒ `LogicalAccept`
2. Real Lean 4.28.0 proof-check benchmarks
3. Independent arithmetic reference (no shared registry)
4. Multistep history; novelty vs PRIOR_ART
5. Independent human review
