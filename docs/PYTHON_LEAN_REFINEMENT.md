# Python ↔ Lean Decision-Kernel Refinement

Status: **historical design note**. The decision-kernel and serialized-representation
milestones described below have since been integrated into the PCS v0.6/v2 Lean
layer. For the current theorem chain and remaining trusted boundaries, use
`docs/LEAN_KERNEL_STATUS.md` and `formal/PCS_FULL_FORMALIZATION_REPORT.md` as the
authoritative references.

## Goal

PCS now separates **evidence establishment** from **claim-status decision**.

The Python replay/checking layer first establishes normalized evidence objects. The pure function `pcs.decision.assess_claim` then maps a claim plus its required evidence to one of six statuses:

- `OPEN`
- `FALSIFIED_OR_CHECK_FAILED`
- `COMPUTATIONALLY_SUPPORTED`
- `FORMALLY_VERIFIED_UNDER_ASSUMPTIONS`
- `EMPIRICALLY_VALIDATED_WITHIN_SCOPE`
- `MIXED_SUPPORT_UNDER_ASSUMPTIONS`

The formal target is to prove that the executable decision procedure refines the Lean assurance semantics rather than merely duplicating similar-looking case logic.

## Current boundary

The Python decision kernel is intentionally pure: it does not read files, execute scientific checks, hash artifacts, or validate signatures. Those operations happen before it is called.

The Lean layer currently defines:

- typed claim/evidence classes;
- explicit assumption context `Γ`;
- predicate/evidence binding;
- the logical judgment `Assures Γ L C E`;
- single-evidence Boolean admission functions with soundness theorems.

## Frozen conformance vectors

`tests/decision_vectors.json` is the first cross-language decision table. It covers:

- missing evidence;
- unverified evidence;
- failure dominance;
- computational support;
- formal evidence class separation;
- empirical/statistical support;
- mixed formal+empirical support;
- formal evidence satisfying a computational claim.

Python tests execute all vectors on every test run.

This was the next Lean milestone when this note was written. It has since been completed and incorporated into the current decision/normalized-state theorem chain.

## Refinement theorem target

For normalized claim/evidence state and an explicit assumption context:

```text
LeanDecision(c, E) = accepted(L)
∧ ContextCovers(Γ, c)
---------------------------------
Γ ; E ⊢ c @ L
```

This theorem is **one-way soundness**, not completeness. PCS may conservatively leave a claim OPEN even when stronger evidence exists outside the supported decision procedure.

That serialized implementation-refinement bridge has since been proved for the current v0.6/v2 representation. The deployed high-assurance path now gates authoritative validity on compiled Lean acceptance; the remaining operational and semantic boundaries are listed in the current status/report files referenced above.

## Why the split matters

This gives the project a tractable formalization boundary:

1. untrusted/domain-specific systems generate candidate evidence;
2. the replay layer establishes evidence facts;
3. a small pure decision kernel assigns scoped assurance status;
4. Lean proves the admission logic is sound relative to `Assures`.

The long-term goal is to shrink steps 2–3 into independently checkable kernels wherever practical without confusing computational correctness with empirical scientific validity.
