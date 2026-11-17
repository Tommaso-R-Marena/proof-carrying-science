# Trust boundaries

## In scope (research trust model)

- Local, fully checked prior `ValidState` produced by the same research verifier
  process (or an equivalently pinned replay of its report).
- Exact equality of obligation keys.
- Declared dependency edges are the sole invalidation topology.
- Synthetic local checkers for Int/Rat/predicate ops.

## Explicitly not established by this project

| Claim | Status |
|---|---|
| Cryptographic digests are collision-free | Not assumed in Lean; optional later with explicit axiom |
| Cross-host / cross-process cache trust | Out of scope |
| Immutable filesystem or OS integrity | Host assumption |
| Rollback protection without external checkpoint | Not claimed |
| Scientific truth of measurements | Never claimed; inputs are admitted evidence ids |
| Python runtime refines Lean model | Differentially tested; see REFINEMENT_ANALYSIS |
| Proof-search lemma libraries | Separate PCS workstream |

## Authority rule

```
reuse_permitted ⇔ eligible ∧ prior_accepted
```

A cache hit with `prior_accepted = false` is a non-event for acceptance.
Malformed, unknown, or unsupported entries cannot escalate to affirmative.

## Policy and version

Changing `policy` or `version` on a node breaks eligibility of any prior entry
keyed under the old values. Authority granted under policy P cannot transfer to P'.

## Relation to PR #201 intake cache

Scientific intake's host HMAC cache deliberately denies scientific authority and
assumes completeness of a declared input projection. This project targets graph
certificate revalidation with proved invalidation and fresh correspondence, and
does not reuse that cache implementation.
