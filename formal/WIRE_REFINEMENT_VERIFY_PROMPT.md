# Wire refinement verification prompt

This is a focused Lean verification pass for the next PCS serialization boundary.

## Project state

The existing PCS decision and normalized-state soundness layer on `main` is already
machine-checked under Lean 4.28.0. Do not alter or weaken those existing theorem
statements.

New formal modules on this branch:

- `PCS/Wire.lean`
- `PCS/WireVectors.lean`
- `PCS/WireCodec.lean`
- `PCS/WireCodecVectors.lean`

The Python side now emits a claim-scoped `pcs-normalized-decision-v1` object only
after independent certificate replay verification. Full Python predicates are
SHA-256 committed before they cross into Lean so that domain-specific fields are
not projected away.

## Required work

1. Use the existing `leanprover/lean4:v4.28.0` toolchain.
2. Run `lake build` from `formal/`.
3. If the new wire modules fail to elaborate, make the smallest proof/syntax changes
   necessary to compile them. Do not weaken:
   - `PCS.Wire.WellFormed`;
   - any existing `PCS.SerializedBridge` theorem;
   - any existing `Assures` semantics.
4. Preserve the exact evidence-binding idea:
   `decodePredicateCommitment` must map an equal commitment to the same opaque
   Lean predicate identity. Do not replace it with an unbound or constant predicate.
5. Preserve these `WellFormed` fields:
   - source claim identity;
   - exact evidence scope;
   - exact context/assumption scope;
   - unique decoded evidence IDs;
   - explicit context coverage;
   - required-evidence predicate binding;
   - recorded decision equality with `decideClaim`.
6. Compile the frozen `PCS.WireVectors.pkpdWire` examples and the raw-string
   `PCS.WireCodecVectors.rawPkpdWire` decoder examples.
7. Confirm unknown wire-format/version/enum strings are rejected and that raw
   recorded invariant booleans / wire hash are not treated as proofs of
   `WellFormed`.
8. Run `scripts/verify_lean.sh`.
9. Capture `#print axioms` output for:
   - `PCS.Wire.source_claim_identity`
   - `PCS.Wire.exact_context_scope_preserved`
   - `PCS.Wire.decoded_decision_matches_recorded`
   - `PCS.Wire.predicate_commitment_eq_preserved`
   - `PCS.Wire.wire_computational_sound`
   - `PCS.Wire.wire_formal_sound`
   - `PCS.Wire.wire_empirical_sound`
   - `PCS.Wire.wire_mixed_sound`
10. Report the exact Lean version, build exit code, placeholder/forbidden-declaration
   audit, and any source changes required.

## Safety constraints

Do not add `sorry`, `admit`, project `axiom`, `unsafe`, `implemented_by`,
`extern`, or `native_decide`.

If any theorem is false as stated, report the counterexample or missing precondition
instead of weakening it silently.

## Intended result

A successful pass should justify the following narrower chain:

```text
typed, well-formed claim-scoped DecisionWire
        -> Normalized.DecisionInput
        -> machine-checked decide soundness
        -> Γ ; E ⊢ C @ L
```

Raw JSON parsing and SHA-256 correctness remain outside this theorem and must stay
explicitly identified as the next lower refinement boundary.
