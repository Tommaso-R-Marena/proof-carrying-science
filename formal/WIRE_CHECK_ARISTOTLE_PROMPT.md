# Aristotle task — close and promote the finite wire-checker bridge

The PCS decision, normalized-state, and typed `DecisionWire` soundness layers are
already machine-checked. The previous independent pass also rebuilt the wire
codec/vectors under Lean 4.28.0. This pass must close the final finite Boolean
checker bridge and independently re-run the executable gates.

## Primary theorem target

Prove every remaining `sorry` in `ProofTasks/WireCheck.lean` without changing the
statements of:

- `PCS.Wire.WellFormed`;
- `PCS.Wire.toDecisionInput`;
- existing `PCS.SerializedBridge` or `PCS.Wire` soundness theorems;
- `Assures` semantics;
- full predicate-commitment equality.

The central theorem is:

```lean
wireCheck w = true -> WellFormed w
```

The Boolean checker must continue to cover exactly:

1. source claim-ID equality;
2. exact evidence-ID scope;
3. no duplicate evidence IDs;
4. exact context-ID scope;
5. every evidence predicate commitment equals the claim commitment;
6. recomputed `decideClaim` equals the recorded decision.

The four proof obligations currently staged are:

- `decodedEvidence_unique_of_wire_ids_nodup`;
- `contextCovers_of_exact_context_scope`;
- `requiredEvidenceBound_of_commitments`;
- `wireCheck_sound`.

Suggested decomposition: pull decoded members back through `List.map`; use the
`Nodup` fact on mapped source IDs for uniqueness; derive context witnesses from
exact mapped-ID equality; preserve predicate equality through
`decodePredicateCommitment`; then decompose the Boolean conjunction in
`wireCheck_sound` and convert each successful Boolean equality/test into the
corresponding proposition.

If those proofs compile cleanly, promote the checker from `ProofTasks` into an
ordinary production module `PCS/WireCheck.lean`, import it from the formal root,
and extend the permanent axiom audit to include `wireCheck_sound` and the four
`wireCheck_*_sound` corollaries. Do not promote anything with a placeholder.

## Frozen cross-language vector

The Python side was hardened after the previous pass to remove platform `libm`
from certificate semantics. The restricted analytic PK/PD replay now uses
fixed-precision `Decimal` arithmetic for the exponential, tolerance comparisons,
and committed error diagnostics. The frozen v0.5.1 vector is now expected to be:

```text
certificate_semantic_hash =
0fc13509d27c7b31e45ed9a841bfacddc9ca8a1a6c7e3a2af66e0b434cb36a8a

wire_semantic_hash =
c5d3da1f6296a62e3affe9f7d43c3c8d50f51b0b99f75da459ca613d0e5580a7

predicate commitment =
pcs-predicate-sha256:8cc9e0b74e7361040ed704b89f6753399f9c07573fe51198f0f093c6017f2c4c
```

Do not refresh these hashes merely because a test fails. First determine whether
identical repository inputs actually reproduce them. A mismatch is a release
blocker and must be explained.

## Required verification

Use Lean 4.28.0. Run all of the following:

```text
cd formal
lake env lean ProofTasks/WireCheck.lean
lake env lean ProofTasks/WireRefinementChecks.lean
lake build
bash scripts/verify_lean.sh
```

Then from the repository root, using the available Python 3 environment:

```text
python -m pytest -q
python -m pytest -q \
  tests/test_normalized_wire.py \
  tests/test_v05_trust.py \
  tests/test_attestation_finalization.py
```

The pre-handoff local result is 113/113 full-suite and 35/35 targeted. In
particular, verify that the PK/PD frozen vector reproduces exactly and that the
new regression proving the verifier does not depend on `math.exp` passes.

## Trust / escape-hatch audit

Search the production formal root for:

```text
sorry admit axiom unsafe implemented_by extern native_decide
```

No new occurrence is allowed. Print axioms for:

- `wireCheck_sound`;
- `wireCheck_computational_sound`;
- `wireCheck_formal_sound`;
- `wireCheck_empirical_sound`;
- `wireCheck_mixed_sound`;
- the existing `wire_*_sound` theorems.

Standard Lean axioms such as `propext`, `Classical.choice`, and `Quot.sound` may
appear; no `sorryAx` or new PCS-specific axiom may appear.

## Non-claims that must remain explicit

Even after `wireCheck_sound`, do **not** claim an end-to-end theorem over delivered
ZIP/JSON bytes. Raw JSON parsing, JSON Schema implementation, SHA-256/Ed25519,
Python scientific replay, and the JSON-text-to-typed-raw-wire construction remain
outside the Lean theorem. This pass is specifically intended to close:

```text
typed DecisionWire + wireCheck = true -> WellFormed -> Assures
```

If any target is false, report the counterexample or missing precondition instead
of weakening or silently changing the theorem.

Return the exact source changes, commands and exit codes, full Python/Lean test
counts, the axiom audit, and a final PASS/FAIL verdict for each boundary.
