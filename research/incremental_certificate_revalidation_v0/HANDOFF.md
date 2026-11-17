# HANDOFF — Incremental Certificate Revalidation v0

## Branch / commits

- **Branch:** `research/pcs-incremental-revalidation-v0`
- **Current commit:** `103854d15614afaad155ea2bd21ed446c6f1b355`
- **Worktree:** `/home/ubuntu/worktrees/pcs-incremental-revalidation-v0`
- **Base main:** `bc78660b5fac857fce3873eb6cda0445d1903da1`
- **Exclusive path:** `research/incremental_certificate_revalidation_v0/` only

Update this file’s commit SHA after each push.

## Completed

- [x] Overlap audit vs PRs #199–#216 and main research (checked-reuse, workflow, epistemic, intake Incremental.lean)
- [x] Isolated worktree + Lean `PCSIncremental` library (builds; no sorry/admit)
- [x] Theorems A–J core subset + `affected_least` + counterexamples + correspondence gap doc
- [x] Python verifier + fresh reference + adversarial suite (9 attacks resisted)
- [x] Differential mutation tests (12 pytest tests passing)
- [x] Benchmarks to ~20k-node synthetic scientific graphs (honest slowdown recorded)
- [x] Docs: formal spec, soundness, trust, refinement, performance, adversarial, reproducibility, integration proposal
- [x] Manuscript draft

## Proven theorems (Lean)

`incremental_implies_fresh`, invalidation soundness/completeness, `affected_least`,
policy/version/op/evidence/dep eligibility breaks, non-escalation, compositional
fresh, mutation safety, demo forged/policy/dep counterexamples,
`executableAcceptImpliesLeanFresh`. Axioms: none or `propext` only.

## Implemented but unproved

- Python affected-closure ≡ Lean `Affected` (differentially tested)
- Full refinement of Python `IncrementalVerifier` to `IncrementalAccept`
- Minimal work bounds / complexity theorems
- Proof-carrying cache update certificates for third-party checkers

## Tests

- `pytest` 12 passed
- Adversarial: all defenses held
- Demo: agree with fresh; forgery rejected under defense-in-depth

## Performance

Incremental slower than fresh for cheap Int ops (~0.5×). Reuse counts high on
sparse changes. See `docs/PERFORMANCE_REPORT.md`.

## Overlap concerns

PR #201 `Incremental.lean` is related abstractly; scoped to intake; not duplicated.
Do not edit other research dirs.

## Next highest-value objectives

1. Prove stronger bidirectional equivalence under reconstructed authoritative caches.
2. Lean-extracted or decide-based checker for a thin executable fragment.
3. Benchmarks where local_check is artificially/really expensive (Lean kernel).
4. Frontier scheduling to avoid full topo walks (with proof obligations).
5. Independent human review of theorem statements and trust model.
