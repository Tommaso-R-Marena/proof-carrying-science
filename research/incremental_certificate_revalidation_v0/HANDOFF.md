# HANDOFF — Incremental Certificate Revalidation v0

## Branch / commits

- **Branch:** `research/pcs-incremental-revalidation-v0`
- **Draft PR:** https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/217
- **Tip:** recorded in `results/HEAD_COMMIT.txt` (do not chase SHA in this file)
- **Worktree:** `/home/ubuntu/worktrees/pcs-incremental-revalidation-v0`
- **Base main:** `bc78660b5fac857fce3873eb6cda0445d1903da1`
- **Exclusive path:** `research/incremental_certificate_revalidation_v0/` only

## Completed

- [x] Overlap audit vs PRs #199–#216 and main research (checked-reuse, workflow, epistemic, intake Incremental.lean)
- [x] Isolated worktree + Lean `PCSIncremental` library (builds; no sorry/admit)
- [x] Substantive `IncrementalAccept` (premises only) + `incremental_implies_fresh`
- [x] New-graph invalidation aligned Lean ↔ Python; prior mode retained for negatives
- [x] Assumption-removal counterexamples (forgery / prior Affected / ChangesComplete)
- [x] Expensive-check benchmarks: trusted reuse ~60–90× vs fresh on sparse leaf edits
- [x] Cheap-ops negative performance result preserved
- [x] Theorems A–J + correspondence gap doc (differential ≠ refinement)
- [x] Python verifier + fresh reference + adversarial suite
- [x] Docs + manuscript draft
- [x] Draft PR #217 opened (clearance required before non-draft)

## Proven theorems (Lean)

`incremental_implies_fresh` (derives FreshValid; does not assume it),
`reuse_entry_checks`, invalidation soundness/completeness, `affected_least`,
`new_edge_requires_new_graph_invalidation`, policy/version/op/evidence/dep
eligibility breaks, non-escalation, compositional fresh, mutation safety,
demo forged/policy/dep counterexamples, `executableAcceptImpliesLeanFresh`.
Axioms: none, or `propext` / `Classical.choice` / `Quot.sound` from `by_cases`.

## Implemented but unproved

- Python affected-closure ≡ Lean `Affected` (differentially tested)
- Full refinement of Python `IncrementalVerifier` to `IncrementalAccept`
- Minimal work bounds / complexity theorems
- Proof-carrying cache update certificates for third-party checkers

## Tests

- `pytest` under `tests/` (core, differential, adversarial, assumption counterexamples)
- Adversarial: all defenses held under default posture
- Demo: agree with fresh; forgery rejected under defense-in-depth

## Performance

- Cheap Int ops: incremental slower (~0.45–0.53×) — negative result kept.
- Expensive synthetic checks: trusted sparse reuse ~64–123×; root-heavy ~1× failure;
  defense recheck-on-reuse ~1×. See `docs/PERFORMANCE_REPORT.md`.

## Overlap concerns

PR #201 `Incremental.lean` is related abstractly; scoped to intake; not duplicated.
Do not edit other research dirs.

## Next highest-value objectives

1. Bridge `runIncremental` ok-result ⇒ `LogicalAccept` (kernel-checked).
2. Real Lean 4.28.0 proof-check benchmarks (cold/warm/trusted/defense).
3. Independent arithmetic reference (no shared op registry).
4. Multistep history soundness; PRIOR_ART novelty comparison.
5. Independent human review of theorem statements and trust model.
