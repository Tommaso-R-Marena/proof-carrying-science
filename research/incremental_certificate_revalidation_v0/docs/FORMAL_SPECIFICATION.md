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
| `LocalCheck` | op → version → policy → **evidence** → deps → payload → output → Bool |
| `FreshWitness` | prior FreshValid + cacheSound authority reconstruction |

## Three cache concepts

1. **Lookup** — retrieving a stored entry by key.
2. **Eligibility** — `cached.key = current.key` (exact equality).
3. **Authority** — `priorAccepted = true` under an explicit trust model.

Lookup alone never establishes mathematical validity.

## Fresh validity

`FreshValid check g σ certs` means every node `n` satisfies
`nodeChecks check n σ (certs n.id)`.

## Affected set

`Affected g' changes leaf` iff some `root ∈ changes` has `Downstream g' root leaf`
on the **updated** graph. Prior-graph Downstream is incomplete when new dependency
edges appear (`new_edge_requires_new_graph_invalidation`).

## ChangesComplete

Any definitional difference between same-id nodes of `g` and `g'` must be listed
in `changes`. Combined with `idsCovered` (no brand-new ids without prior coverage),
this seeds invalidation correctly.

## Incremental acceptance (premises only)

`IncrementalAccept` is a Type carrying:

- `prior : FreshWitness` — sound prior verification + authoritative cache;
- `changesComplete` — complete accounting of definitional edits;
- `idsCovered` — every updated-graph id existed previously;
- `affectedRechecked` — every Affected node on `g'` locally checks;
- `unaffectedReused` — every Unaffected node reuses an eligible ∧ authoritative entry.

It does **not** contain a `FreshValid g'` field.

## Central theorem

`incremental_implies_fresh`: the premises above imply `FreshValid` on `g'`.
Proof cases on Affected vs Unaffected; reuse uses `reuse_entry_checks` from
`FreshWitness.cacheSound`.

Stronger behavioral equivalence of runtimes is **not** claimed; see
`REFINEMENT_ANALYSIS.md`.

## Out of scope

Cryptographic collision resistance; cross-process trust roots; scientific-domain
checkers; proof-search lemma reuse.
