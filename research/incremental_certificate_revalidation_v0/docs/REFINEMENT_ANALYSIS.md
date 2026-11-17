# Refinement analysis — Lean model vs executable verifier

## What is proved

If a decoded state satisfies Lean `IncrementalAccept`, then `FreshValid` holds
(`executableAcceptImpliesLeanFresh` via `incremental_implies_fresh`). The
acceptance structure carries premises only (prior FreshWitness, ChangesComplete,
idsCovered, affected recheck, unaffected reuse) — not an assumed `FreshValid`
conclusion. Families A–J in `SOUNDNESS_THEOREMS.md` constrain any correct
implementation.

## Invalidation alignment

| Side | Invalidation graph | Change accounting |
|---|---|---|
| Lean | `Affected g' changes` (updated graph) | `ChangesComplete` |
| Python (default) | `invalidation_graph="new"` | `require_changes_complete=True` |
| Python (negative only) | `invalidation_graph="prior"` | optional disable |

Prior-only Affected is incomplete for new dependency edges. Executable tests
demonstrate set incompleteness and a false-accept path when prior invalidation is
combined with incomplete changes and forged new-key authority.

## What is tested (not proved)

1. Python `affected_closure` agrees with inductive `Affected` on generated graphs.
2. Incremental reports agree with the independent fresh reference on mutation sequences.
3. Adversarial mutations cannot obtain acceptance from forged/stale cache entries
   under default defenses.
4. Assumption-removal counterexamples: dropping ChangesComplete, authority, or
   new-graph invalidation invalidates the intended guarantee.

**Differential agreement is empirical validation, not a refinement proof.**

## Smallest remaining unverified translation boundary

```
Python JSON graph/change/cache bytes
        │  (canonical decode — tested)
        ▼
Lean Graph / ChangeSet / Cache / Assignment / Certificates
        │  (IncrementalAccept — proved ⇒ FreshValid)
        ▼
Mathematical acceptance
```

The critical gap is showing that the Python incremental algorithm *establishes*
`IncrementalAccept`, not merely that its boolean outcome matches another Python
fresh verifier.

## Non-goals for v0

- Extracting a verified executable from Lean (possible future: decide-based checker).
- Proving the CPython interpreter.
- Content-addressed Merkle trust roots as mathematical authority.
- Calling differential tests a refinement proof.
