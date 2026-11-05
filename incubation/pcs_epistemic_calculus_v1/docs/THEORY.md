# Proof-Carrying Epistemic Calculus — Theory v1

## Motivation

PCS founding documents define the graded judgment `Γ ; E ⊢ C @ L` and name two
theorem targets that remained open as executable research kernels:

1. **Composition** — when certificates for subworkflows compose (`FORMAL_SEMANTICS_DRAFT` §6).
2. **Invalidation** — when changed artifacts force claim reopen, and why
   non-impact requires dependency completeness (`FORMAL_SEMANTICS_DRAFT` §7,
   commons INV-006).

Science also proceeds by **rival models**. Existing PCS certificates package a
single workflow; they do not treat disagreement as a first-class assurance
object. This incubation closes that gap with a **dialectic** layer.

## Evidence lattice

Four classes remain distinct:

| Class | Role |
| --- | --- |
| `formal` | Independently checkable mathematical/program properties |
| `computational` | Finite replayable checks |
| `empirical` | Observations about the world / context of use |
| `provenance` | Identity, lineage, integrity |

**Non-promotion theorems** (Lean):

- `no_computational_to_formal`
- `no_provenance_to_formal`
- `no_provenance_to_empirical`
- `formal_covers_computational`
- `le_refl` / `le_trans` / `le_antisymm` (partial order)
- `computational_incomparable_empirical`, `formal_incomparable_empirical`
- `meet_formal_empirical_collapses` — heterogeneous scientific meet collapses to
  provenance and must **not** be read as a discharge GLB or silent promotion

## Assurance

`Assures Γ L C E` holds when the claim's required class equals `L` and every
required evidence record is present, accepted, and lattice-allowed.

## Composition

Pipeline composition:

```
Assures Γ1 L1 c1 E1
Assures (Γ2[+c1]) L2 c2 E2
E1 disjoint from required(c2)
--------------------------------
Assures (Γ1 ∪ Γ2) L2 c2 (E1 ++ E2)
```

Lean: `compose_assures`, `supports_prepend_disjoint`.

## Invalidation

Declared-graph impact reaches artifacts through workflow edges, then evidence,
then claims. Lean covering lemma: `claimsRequiring_covers`.

World non-impact is **not** inferred from declared non-reachability unless an
explicit `dependency_complete = true` hypothesis is supplied
(`NonImpact`, `hidden_dependency_blocks_world_nonimpact`).

## Dialectic

For a finite ensemble of model certificates and candidate claims:

- **Agreement core** — supported in every model
- **Dispute frontier** — supported in some but not all
- **Distinguishing experiment** — an observation that partitions the ensemble

Merging ensembles never forces consensus; disputes that remain split stay in the
frontier (`dispute_preserved_if_still_split`).

## Authority boundary

This calculus is incubation research. It does **not** authorize production PCS
package acceptance, clinical validity, or empirical scientific truth.
