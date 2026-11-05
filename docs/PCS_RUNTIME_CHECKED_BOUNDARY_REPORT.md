# Source-bound CertiForge checked-wrapper refinement v2

The current `eval_expr_checked` guard now has a source-bound executable Rust-fragment
refinement and a composition theorem for accepted rewrite certificates. This extends
the existing expression-interpreter extraction without changing production Rust or
claiming extraction of the top-level `eval` loop.

## Exact boundary

The selected CertiForge revision is
`c71e8575db2800b015a9d444f8ed572490f3a871`. Its interpreter lines 168–179 are preserved
in [checked-wrapper-v2.rs.txt](../formal/source_reference/certiforge/checked-wrapper-v2.rs.txt).
Their SHA-256, including the final newline, is
`a6463dde9f0e25f2a0e0be48b5d2c6950d291ceeb5627faa9554b150df52906b`.
The receiver-selected checkout must contain those exact bytes. The existing source
windows for `eval_expr`, its callees, and `Width::mask` must also match the original
Aristotle binding. Changes outside these windows remain outside the proof coverage.

[RuntimeCheckedBoundary.lean](../formal/tools/RuntimeCheckedBoundary.lean) introduces
a small iterator/early-return syntax fragment. Its rendered tokens bind the complete
wrapper signature and body to the freshly read source literal. The fragment covers
`for value in store.values()`, the `if let Value::BitVec` pattern, the conditional guard,
and the early return. It reuses the existing Rust expression semantics for the exact
masking condition, error construction, and final `eval_expr` call. This is a checked
AST for one recognized wrapper shape, not a general Rust parser.

`canonicalB_iff` proves that the actual masking test accepts exactly `Value.WF`.
`loop_exact` proves that sufficient iterator fuel returns the body result exactly
when every store value passes the guard; otherwise it returns the actual canonicality
error. Boolean entries are skipped by the pattern, and malformed unused entries are
also rejected. `guard_order_independent` makes this decision independent of the
HashMap snapshot's order.

`checked_wrapper_refines` composes that iterator contract with Aristotle's existing
source-extracted `eval_expr` theorem, for every represented store and expression,
all four widths, and every expression error path. `checked_certificate_preserves`
then composes it with the existing certificate checker and well-typed-store theorem.
The certificate checker still determines rewrite acceptance. Iterator and call-depth
exhaustion are explicit non-value outcomes.

## Executed evidence

Run from the PCS root, with the selected CertiForge checkout alongside it:

```bash
source /workspace/.onboarding/activate.sh
source scripts/activate_lean_428.sh
python scripts/verify_runtime_checked_boundary.py \
  --certiforge /workspace/certiforge --native --negative-controls \
  --output research/runtime-checked-boundary-v2/verification.json
python -m pytest tests/test_runtime_checked_boundary_gate.py \
  tests/test_runtime_refinement_gate.py -q
rustfmt --check research/runtime-checked-boundary-v2/native_controls.rs
```

The preserved [verification receipt](../research/runtime-checked-boundary-v2/verification.json)
contains 17 freshly kernel-checked theorems. Their axioms are restricted to `propext`,
`Classical.choice`, and `Quot.sound`, or subsets. Fresh Lean rejects two altered source
snapshots: an inverted inequality and a replaced width mask. Both fail specifically
at the source-binding proposition, and their failed axiom inventories are rejected.
The negative elaboration diagnostics include Lean's internal `sorryAx` placeholder
for the failed theorem; those failed runs are never accepted as proof evidence.

Thirty-one native Rust assertions pass across u8/u16/u32/u64: zero, one, maximum
canonical values, oversized shifts, malformed payloads at the three narrower widths,
malformed unused entries, missing variables, invalid operators, an invalid select
condition, Boolean ordering rejection, and Boolean inputs. These compile and execute
against the actual selected crates. The native test is regression evidence, not a
universal compiler-refinement proof.

The source gates pass 18 pytest tests: nine new tests covering exact binding, seven
semantic source mutations, and truncation, plus nine existing extraction/inventory
gate tests. The final measured run used 10.105542 seconds for positive Lean checking,
8.696831 and 7.929859 seconds for the two expected kernel failures, and 0.415786 seconds
for the native controls with a warm Cargo cache. These are invocation wall times,
not total project compute or a capability benchmark.

The first native fixture failed to compile because it incorrectly assumed `EvalError`
implemented `Clone`. The fixture now constructs that error afresh; the failed log is
preserved. No production defect was concealed or production code changed.

## Remaining obligations

The proofs are about the source-bound Rust fragment under its declared semantics.
They do not prove Rust compiler correctness, native HashMap implementation refinement,
the top-level parameter-binding/return-type loop, the Rust type checker, or general
Rust parsing. Immutable references are represented transparently; a finite values
snapshot represents HashMap iteration. Native maps have unique keys. The formal
store representation can also describe lists with duplicate keys, beyond that native
domain, without making a claim about native duplicate-key behavior.

Formal payloads are naturals, so the abstract bad-payload theorem also covers values
at or above `2^64` that cannot occur in a native Rust `u64`. Every native u64 payload is
canonical for width u64; the actual native controls use zero, one, and `u64::MAX`.
The two conditional Python/JavaScript refinements, English rewriting, and unextracted
Rust top-level loop remain open. No PCS scientific authority is conferred by these
proofs or receipts. Existing historical evidence is unchanged.

This advances the Rust boundary within workstreams 29, 31, and 34; it does not complete
their broader language, compiler, or integration obligations.
