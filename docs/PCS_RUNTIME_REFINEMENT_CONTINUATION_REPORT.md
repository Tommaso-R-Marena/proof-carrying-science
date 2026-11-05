# Source-bound output admission and error propagation v3

The current CertiForge `eval` output continuation now has an executable source-bound
refinement under a precisely defined Rust fragment. It composes the existing checked
expression wrapper with the actual `Value::ty` helper, derived enum equality, `?`
error propagation, and the declared return-type check. Production Rust and all
previous formal sources remain unchanged.

## What coverage increased

At CertiForge `c71e8575db2800b015a9d444f8ed572490f3a871`, the new extraction binds:

| Current production source | Exact lines | Meaning covered |
| --- | --- | --- |
| `crates/certir-interpreter/src/lib.rs` | 158–162 | Checked expression call, early error propagation, output type rejection, successful return |
| `crates/certir/src/lib.rs` | 10–17 | Width variants and their `PartialEq`/`Eq` derive annotations |
| `crates/certir/src/lib.rs` | 59–64 | Type variants, nested Width field, and equality derive annotations |

The [new module](../formal/tools/RuntimeOutputBoundaryV3.lean) renders the continuation
AST to exactly the tokens in freshly read source snapshots. A receiver-selected
checkout must match the exact snapshot bytes before verification. Existing bound
expression-interpreter windows, the `Value::ty` helper at lines 21–26, and the v2
checked wrapper at lines 168–179 must also match.

The earlier Rust expression fragment does not implement equality for nested
`Ty::BitVec(Width)` values or direct method dispatch on struct-variant `Value::BitVec`.
V3 therefore adds a narrow typed continuation interpreter. It calls the freshly
source-extracted `Value::ty` helper directly and implements structural derived equality
for the actual two Ty variants and four Width variants. Unsupported type encodings
return no equality answer. No existing semantics were weakened or silently changed.

`checked_output_continuation_refines` proves the composed continuation equivalent
to a reference result for every represented store, expression, and declared return
type, with sufficient expression, iterator, and type-call budgets. The input store
is the receiver-supplied result of the earlier input-binding phase; that phase is
not extracted by this work.

`output_acceptance_requires_declared_type` proves that a successful reference result
has exactly the declared type. Every checked expression error is propagated unchanged
at the encoded runtime boundary. Resource exhaustion remains a non-value result.
`output_certificate_preserves` combines the existing accepted-certificate theorem
with the actual output guard, including the certificate checker's equality of original
and candidate return types.

These are source-bound language-fragment results, conditional on the declared
operational semantics. They are not proofs of native compiler correctness or the
entire runtime program. Native executions provide separately labeled regression
evidence.

## Reproduction and evidence

From the PCS root:

```bash
source /workspace/.onboarding/activate.sh
source scripts/activate_lean_428.sh
python scripts/verify_runtime_output_boundary_v3.py \
  --certiforge /workspace/certiforge --native --negative-controls \
  --output research/runtime-refinement-v3/verification.json
python -m pytest tests/test_runtime_output_boundary_v3.py \
  tests/test_runtime_checked_boundary_gate.py tests/test_runtime_refinement_gate.py -q
rustfmt --check research/runtime-refinement-v3/native_output_controls.rs
```

The preserved [verification receipt](../research/runtime-refinement-v3/verification.json)
records nine new kernel-checked results, with only `propext`, `Classical.choice`, and
`Quot.sound`, or subsets. Its verifier freshly compiles both direct dependencies into
an isolated temporary Lean search path and audits their 21 existing theorems before
compiling v3. Cached tool oleans are not accepted in place of those fresh dependency
checks.

Two changed-source snapshots are independently rejected in fresh Lean: an inverted
return-type guard and replacement of `eval_expr_checked` by unchecked `eval_expr`.
Both fail the source-binding proposition. Their failed axiom inventories are also
rejected; failed elaboration diagnostics never become positive evidence.

Forty assertions compile and execute against the actual native crates:

- All 25 combinations of actual and declared types: five matching outputs succeed;
  twenty mismatches return the exact return-type error.
- Four expression error paths propagate before the return-type guard.
- Three malformed narrow-width input payloads produce the canonicality error even
  when the declared return type is incompatible.
- Native u64 maximum, two arity mismatches, four input-type mismatches, and one dead
  branch exercise complete-function integration.

The final two groups include native tests of the unextracted input phase. Passing
them does not turn that phase into a universal proof.

Thirty-two pytest gates pass: fourteen new source-window/equality/mutation checks,
plus eighteen existing source-boundary gates. The source audit, Python compilation,
and Rust formatting check also pass. The receipt includes wall time, child CPU time,
and a clearly named **process-cumulative** maximum child RSS; that RSS is not the
individual native fixture's memory use. Cargo uses its existing warm cache and
offline local dependencies. No training or mathematical capability benchmark is
claimed by this formal-assurance work.

Initial elaboration failures are preserved: the first attempt omitted fuel in an
empty-function caller and mishandled a dependent equality; the second rewrote inside
an unreduced match. The third attempt checked all nine results. These were proof-code
development failures, not concealed production defects. The first complete positive
verification receipt is also retained separately from the final receipt.

## Remaining boundaries

The mutable `HashMap::new`/zip/input-type-check/insert phase at interpreter lines
140–157 remains unextracted. So do the complete Rust type checker, general Rust
parsing, HashMap implementation correspondence, compiler correctness, formatted
input-error rendering, and the Python/JavaScript conditional refinements.

The continuation's immutable field projections bind `program.body` and
`program.ret_ty` to receiver-supplied typed values. Rust references are represented
transparently. The equality rule follows the standard semantics of derived enum
equality; deriving-macro implementation correctness is not proved. The bounded AST
recognizes this source continuation, rather than arbitrary submitted Rust code.

The formal Value payload domain is Nat, whereas native Rust payloads are u64. The
new continuation is type-based and composes the earlier explicit masking boundary;
no result claims that impossible native payloads were executed. No scientific or
empirical authority is granted. Workstreams 29, 31, and 34 advance within these stated
bounds and retain their wider open obligations.
