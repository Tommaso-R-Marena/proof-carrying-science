# Formal specification — Incremental Certificate Revalidation v0

## Problem

Given a finite computation DAG and a previously accepted verification state,
determine which node certificates may be safely reused after a precisely
represented change set, such that incremental acceptance never exceeds fresh
full verification.

## Objects

| Object | Meaning |
|---|---|
| `Node` | id, op, deps, policy, version, evidence |
| `Graph` | finite list of nodes |
| `ObligationKey` | exact tuple (id, op, policy, version, evidence, depOutputs) |
| `Certificate` | payload + claimed output |
| `CacheEntry` | key + cert + `priorAccepted` |
| `ValidState` | well-formed acyclic graph + outputs + authoritative cache |
| `ChangeSet` | node ids whose local definition/evidence changed |
| `LocalCheck` | op → version → policy → deps → payload → output → Bool |

## Three cache concepts

1. **Lookup** — retrieving a stored entry by key.
2. **Eligibility** — `cached.key = current.key` (exact equality).
3. **Authority** — `priorAccepted = true` under an explicit trust model.

Lookup alone never establishes mathematical validity.

## Fresh validity

`FreshValid check g σ certs` means every node `n` satisfies
`nodeChecks check n σ (certs n.id)`.

## Affected set

`Affected g changes leaf` iff some `root ∈ changes` has `Downstream g root leaf`,
where `Downstream` follows dependency edges from changed nodes to dependents.

## Incremental acceptance

`IncrementalAccept` requires:

- `FreshValid` on the new graph/assignment/certificates;
- reuse of cache entries only when `reusePermitted` (eligible ∧ authority);
- affected nodes rechecked via local checks.

## Central theorem

`incremental_implies_fresh`: IncrementalAccept ⇒ FreshValid.

Stronger behavioral equivalence of runtimes is **not** claimed; see
`REFINEMENT_ANALYSIS.md`.

## Out of scope

Cryptographic collision resistance; cross-process trust roots; scientific-domain
checkers; proof-search lemma reuse.
