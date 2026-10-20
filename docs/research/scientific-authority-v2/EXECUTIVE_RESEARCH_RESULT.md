# Scientific Authority V2: implemented research result

The new prototype extends PR158 in three concrete ways. It checks the scientific
mathematics of a complete bounded retained history, obtains post-verification
commitments from an independently executable durable witness, and refuses
eligibility until the local state matches a nonce-fresh finalized witness state.
It recovers only from exact retained signed material. It does not invent missing
authorization or treat a local SQLite commit as a distributed atomic transaction.

The supported scientific class is unchanged: finite exact-rational discrete
A→B transfer, at most64 firings, bounded canonical rational operands, checked
conservation and numerical enclosures, and optional finite nonnegativity. Each
artifact declares its own problem. No fixed-problem improvement, chemical kinetics,
clinical adequacy, neural promotion or empirical scientific acceptance follows.

## Actual implementation and evidence

| Capability | Status | Evidence |
| --- | --- | --- |
| Checked genesis plus every retained scientific artifact | EXECUTED_PASS | `scientific_history_v2`,17tests;0/1/8/32-event replay |
| Rejecting full-history procedure and soundness | PROVED | `audit_sound`, complete formal inventory |
| Durable post-verification PREPARE/FINALIZE witness | EXECUTED_PASS |25unique witness tests, actual Lean/Ed25519/SQLite/HTTP |
| Full signed nonce-bound checkpoint evidence | EXECUTED_PASS |1focused real-server delta test; coordinator tests use new API |
| Honest serial state non-equivocation | PROVED | Fixed-root durable trace theorem; no clone/rollback claim |
| Prepared/local-only state cannot serve | PROVED / EXECUTED_PASS | Closed initialized trace plus coordinator tests |
| Distributed process-crash/recovery windows | EXECUTED_PASS |10actual process exits within17coordinator tests |
| Producer-store rollback detection/reconstruction | EXECUTED_PASS | Live witness, exact material reconstruction |
| Witness/all-store rollback immunity | FALSIFIED under lost-continuity model | Independent18-control campaign retains2counterexamples |
| Separate process, one host/admin (Profile A) | EXECUTED_PASS | Actual server/client and process identifiers |
| Distinct outer-user storage/key principal (Profile B) | BLOCKED_TECHNICAL | UID1000, no capabilities/sudo/mapping helpers |
| Independently administered witness (Profile C) | BLOCKED_EXTERNAL | No independent operator/host/bootstrap provided |
| General Python/crypto/SQLite/compiler refinement | UNVERIFIED | Explicit runtime correspondence obligations |
| Empirical adequacy/external laboratory adoption | UNVERIFIED | Synthetic research demonstration only |

## Formal result

The new isolated Lean4.28.0 project has64 authored theorems and133 total theorem
closures, all within `propext`, `Classical.choice`, `Quot.sound`. Fresh author,
parent and independent copied-source builds agree. Fourteen additional independent
kernel controls test the assumptions, including cloned-witness divergence and
the insufficiency of bare structural equality without checked initialization.

`audit_sound` derives complete mathematical history validity from actual checked
genesis and rejecting traversal. `initialized_trace_serving_scientific` closes
the initialization/invariant dependency. `no_conflicting_finalization_later`
concerns one honest serial state. `recovery_sound` requires complete checked
archive equality to a finalized, pending-free witness. Runtime pending resolution
is an explicit sequence of protocol transitions before that final condition.

Complete signatures, hypotheses, imported/new distinctions, source hashes and
closures are in `FORMAL_THEOREM_INVENTORY.json`; exact correspondence limits are
in `FORMAL_RUNTIME_CORRESPONDENCE.md`. No old theorem or production source changes.

## GitHub and release boundary

The immutable research base is branch
`integration/pcs-authority-v2-baseline-20261020`, exactly PR158 head
`7be674df70eb3108c9dbd8b0b97f42a728bde000`. PR159 contains historical replay;
PR160 contains the witness; PR161 contains formal results; PR162 is the independent
adversarial review. The separate integration branch composes reviewed commits
without merging PRs or rewriting predecessor branches.

This document is a pre-publication qualification record. The final integration
head, actual GitHub proposed-merge commit, tree identity and hosted results are
recorded in its PR description and external final handoff after execution.
No green parent workflow substitutes for final-stack qualification.
