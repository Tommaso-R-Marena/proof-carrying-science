# Refinement analysis — Lean model vs executable verifier

## What is proved

If a decoded state satisfies Lean `IncrementalAccept`, then `FreshValid` holds
(`executableAcceptImpliesLeanFresh`). Families A–J in `SOUNDNESS_THEOREMS.md`
constrain any correct implementation.

## What is tested (not proved)

1. Python `affected_closure` agrees with inductive `Affected` on generated graphs.
2. Incremental reports agree with the independent fresh reference on mutation sequences.
3. Adversarial mutations cannot obtain acceptance from forged/stale cache entries.

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
fresh verifier. Agreement of two executables is empirical differential validation.

## Non-goals for v0

- Extracting a verified executable from Lean (possible future: decide-based checker).
- Proving the CPython interpreter.
- Content-addressed Merkle trust roots as mathematical authority.
