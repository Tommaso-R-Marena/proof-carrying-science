# Aristotle task — checked RawDecisionWire decoder

## Established foundation

The previous independently verified pass closed and promoted:

```lean
PCS.WireCheck.wireCheck_sound :
  wireCheck w = true -> WellFormed w
```

and its computational/formal/empirical/mixed assurance corollaries. PR #17 also
has independently passing Lean 4.28.0 and Python gates.

This task is the next **strictly lower** refinement step. Do not alter the proved
`WellFormed`, `wireCheck`, `decodeRawWire`, `Assures`, or existing soundness
statements.

## Target

Complete every `sorry` in:

```text
formal/ProofTasks/CheckedRawWire.lean
```

The staged executable composition is:

```lean
def checkedDecodeRawWire (raw : RawDecisionWire) : Option DecisionWire :=
  match decodeRawWire raw with
  | none => none
  | some w => if wireCheck w then some w else none
```

Prove:

1. successful checked decoding preserves the exact `decodeRawWire` result;
2. successful checked decoding implies `wireCheck w = true`;
3. therefore successful checked decoding implies `WellFormed w`;
4. compose that result into the four assurance classes.

The intended semantic chain is:

```text
RawDecisionWire
  -> decodeRawWire
  -> DecisionWire
  -> wireCheck = true
  -> WellFormed
  -> Assures
```

## Promotion gate

If all staged theorems compile with no placeholders:

- promote the definition and proved theorems into
  `formal/PCS/CheckedRawWire.lean`;
- import that module from `formal/PCS.lean`;
- extend `formal/PCS/Audit.lean` with `#print axioms` for the promoted theorems;
- reduce `ProofTasks/CheckedRawWire.lean` to regression/examples against the
  production module.

Do not promote anything with a `sorry`.

## Required adversarial examples

Add closed examples showing:

- unknown wire format -> checked decode is `none`;
- unknown spec/checker version -> `none`;
- unknown claim/evidence/outcome/decision token -> `none`;
- structurally decodable but forged recorded decision -> `none` because
  `wireCheck` rejects it;
- structurally decodable but wrong context scope -> `none`;
- frozen PK/PD raw vector -> checked decode returns the expected `pkpdWire`.

Do not use recorded raw invariant booleans or the raw wire hash as proof inputs.

## Verification

Use Lean 4.28.0 and run from `formal/`:

```text
lake env lean ProofTasks/CheckedRawWire.lean
lake env lean ProofTasks/WireCheck.lean
lake env lean ProofTasks/WireRefinementChecks.lean
lake build
```

Then from repository root:

```text
bash scripts/verify_lean.sh
python -m pytest -q
python -m pytest -q tests/test_normalized_wire.py tests/test_v05_trust.py tests/test_attestation_finalization.py
```

The inherited expected Python gate is 113/113 full-suite and 35/35 targeted.

## Axiom / escape-hatch audit

No new `axiom`, `sorry`, `admit`, `unsafe`, `implemented_by`, `extern`,
or `native_decide` may enter the production formal root.

Print axioms for every promoted `checkedDecodeRawWire_*` theorem. Standard Lean
axioms already present in the kernel may remain; no `sorryAx` or PCS-specific
axiom.

## Explicit non-claim

Even if this task fully succeeds, it still starts from typed `RawDecisionWire`.
It does **not** prove:

- raw JSON parsing;
- duplicate-key handling;
- JSON Schema implementation;
- canonical JSON encoding;
- SHA-256 or Ed25519;
- Python scientific replay;
- construction of `RawDecisionWire` from JSON text.

Those are the next lower boundary and must remain explicit.

If any target is false, return the counterexample rather than weakening it.
Return exact source changes, commands/exit codes, axiom dependencies, and a
boundary-by-boundary verdict.
