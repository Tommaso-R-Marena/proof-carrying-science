# Invariant summaries do not certify a transport recurrence

This isolated research library supplies a parameterized, kernel-checked negative
result for the existing PCS discrete transport semantics. It does not change any
production authority, existing Lean statement, parser, schema, or runtime verdict.
Its base is the frozen portable replay head
`ca63ee0a4560919395dc9605e9aa0ec484430d41` (PR165). No merge/deployment is performed.

For rational parameters `0 ≤ a < b ≤ 1/2`, define unit volumes, initial state
`(1,0)`, symmetric matrix `P(a) = [[1-a,a],[a,1-a]]`, and forged next state
`y(b) = (1-b,b)`. Ordinary Lean proves:

- `P(a)` satisfies the existing `Certified` transport contract.
- `y(b)` preserves the initial total amount and stays in `[0,1]`.
- Its quadratic energy is strictly lower than both the initial energy and the
  energy of the **true** next state `P(a)·(1,0)`.
- The unchanged `PCSReal.TransportTrace.check` rejects that recorded update.
- A trajectory that retains `y(b)` after this jump preserves mass, bounds and
  nonincreasing energy at **every natural time**, but the exact checker rejects
  it at **every positive finite horizon**. The zero-step horizon is excluded.

The four new declarations in namespace `PCSPortableInvariantFamily` are
`matrix_certified`, `step_initial`, `invariant_counterexample_family`, and
`all_times`. Their exact statements and explicit parameter assumptions are in
`CounterexampleFamily.lean`. Only standard `propext`, `Classical.choice` and
`Quot.sound` are permitted by the complete axiom inventory. No new axiom,
native evaluation, or placeholder proof is used.

This proves insufficiency of invariant summaries as evidence for a declared
recurrence. It does not discredit those mathematical invariants. A model and a
recorded trajectory require separate evidence. There is no empirical conclusion,
general neural-improvement result, recursive self-improvement claim, or Python
universal authority here. Natural-number quantification in Lean is distinct from
the bounded finite CSV formats and their unproved decoding correspondence.

## Replay

Use the repository Lean4.28.0 configuration, pinned Mathlib
`8f9d9cff6bd728b17a24e163c9402775d9e6a365`, and Python3.12.14 on Linux:

```sh
source scripts/activate_lean_428.sh
lake exe cache get
python -m research.transport_invariant_counterexamples_v1.audit --out /new/evidence-directory
```

The standard-library-only harness requires a clean committed checkout and
preserves every predecessor blob/mode. It captures source bytes, freshly compiles
the old transport/trace/composition libraries and the new family, requires all
four exact axiom closures, and invokes official `leanchecker --fresh` on the
compiled family. Source/object changes, nonzero exits, missing audit entries,
unapproved axioms, and process/resource failures refuse success. It records the
tested commit/tree and binary/source hashes. Compilation keeps `-M2048 -j1` and
`Elab.async=false`; the object recheck has a300s wall/6GiB address-space bound.
Existing evidence directories are never overwritten.

`leanchecker --fresh` uses the same installed Lean C++ kernel and skips unsafe
and partial declarations. It is explicitly **not an external independent
verifier**, independent administration, full Mathlib source rebuild, or proof of
the compiler/OS/source-to-object boundary. Hashes detect corruption and require a
trusted provenance channel for authentication. Subprocesses do not establish an
immutable host. All PCS/scientific authority flags remain false.

## Supporting experiment provenance

The precursor proof artifacts and every failed elaboration/audit attempt remain
in the phase evidence package. A missing finite-sum import was repaired without
changing statements. A longer theorem name caused multiline axiom output to fail
the strict inherited audit; attempted print-width changes did not repair it.
The final shorter `all_times` identifier preserves the formula and fits the
unchanged exact audit format. No trusted parser was weakened.

Separate concrete runtime replays on frozen PR165 use `(a,b)` equal to
`(1/8,1/4)`, `(1/4,1/2)`, and `(49/100,1/2)`, plus16/64-step constant-tail
trajectories. These compare prepared matrices and recorded-domain values against
the abstract family, then execute real Lean negative certificates. They test the
runtime boundary; the universal mathematical claim comes from the theorem above.
They do not establish a kernel refinement of Python/CSV handling.
