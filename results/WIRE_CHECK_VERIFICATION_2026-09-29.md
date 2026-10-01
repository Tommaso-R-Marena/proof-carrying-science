# Wire-checker bridge: verification record (2026-09-29)

Task: `formal/WIRE_CHECK_ARISTOTLE_PROMPT.md`. Toolchain: `leanprover/lean4:v4.28.0` (Lean 4.28.0, core only; no Mathlib).

## Pre-existing build break (found and fixed)

At the start of this pass, `lake build` in `formal/` **failed** (exit 1):

```
error: PCS/Wire.lean:135:9: Ambiguous term
  decide
Possible interpretations:
  Normalized.decide : DecisionInput → DecisionStatus
  Decidable.decide : (p : Prop) → [h : Decidable p] → Bool
```

So the earlier "rebuilt under Lean 4.28.0" record did not match this tree. Fix: in
`PCS.Wire.decoded_decision_matches_recorded`, write `PCS.Normalized.decide` in place of
the unqualified `decide` (in both the statement and the `simpa` set). This is the only
reading that type-checks, so what the theorem says is unchanged. No other existing
statement was touched.

## Source changes

1. `formal/PCS/Wire.lean`: the name fix above.
2. `formal/PCS/WireCheck.lean` (new production module, namespace `PCS.WireCheck`): the
   checker (`idsUnique`, `exactContextScope`, `evidenceCommitmentsBound`, `wireCheck`),
   unchanged from the staged version and still covering exactly the six checks. It also
   holds the four proofs, which contain no placeholders:
   - `decodedEvidence_unique_of_wire_ids_nodup`: pulls decoded members back through
     `List.map`, then uses a private lemma (`eq_of_mem_of_nodup_map`, proved by list
     induction): if a mapped list has no duplicates, the map is injective on that list;
   - `contextCovers_of_exact_context_scope`: rewrites with exact mapped-ID equality to get
     a witness assumption;
   - `requiredEvidenceBound_of_commitments`: a selected required item is in the list, and
     equal commitments decode to equal predicates via `predicate_commitment_eq_preserved`;
   - `wireCheck_sound`: splits the Boolean conjunction and turns each passing check into
     its proposition (`beq_iff_eq`, `of_decide_eq_true`, `List.all_eq_true`);
   - `wireCheck_{computational,formal,empirical,mixed}_sound`: unchanged corollaries.
   The staged file had a duplicate local `contextIds`, identical to `PCS.Wire.contextIds`.
   It was dropped, so `exactContextScope` now refers to the same `contextIds` used by
   `WellFormed`.
3. `formal/PCS.lean`: now imports `PCS.WireCheck`.
4. `formal/PCS/Audit.lean`: now imports `PCS.WireCheck` and has `#print axioms` lines for
   the four lemmas, `wireCheck_sound` and the four `wireCheck_*_sound` corollaries.
5. `formal/ProofTasks/WireCheck.lean`: now a thin check file. It imports the production
   module and restates the four staged targets as `example`s. It also checks
   `wireCheck pkpdWire = true` and that a tampered recorded decision gives `false`, both by
   `decide`.

## Commands and exit codes

| Command (in `formal/` unless noted) | Exit | Result |
|---|---:|---|
| `lake build` (before the fix) | 1 | ambiguous `decide` in `PCS/Wire.lean` |
| `lake env lean ProofTasks/WireCheck.lean` | 0 | no errors, no warnings, no `sorry` |
| `lake env lean ProofTasks/WireRefinementChecks.lean` | 0 | no errors |
| `lake build` | 0 | `Build completed successfully (19 jobs).` |
| `bash scripts/verify_lean.sh` (repository root) | 0 | Lean kernel build, placeholder audit, and forbidden-declaration audit passed |
| `python -m pytest -q` (repository root) | 0 | **113 passed** |
| targeted normalized-wire/trust/attestation suite | 0 | **35 passed** |

Python 3.11.14 with pytest 9.1.1, cryptography 50.0.0 and jsonschema 4.26.0.

## Frozen cross-language vector

The vector was rebuilt from repository inputs (`build_certificate` on
`examples/pkpd_one_compartment/manifest.json`, then `normalize_verified_certificate(…, "C_PK_REPLAY")`):

```text
certificate_semantic_hash = 0fc13509d27c7b31e45ed9a841bfacddc9ca8a1a6c7e3a2af66e0b434cb36a8a
wire_semantic_hash        = c5d3da1f6296a62e3affe9f7d43c3c8d50f51b0b99f75da459ca613d0e5580a7
predicate commitment      = pcs-predicate-sha256:8cc9e0b74e7361040ed704b89f6753399f9c07573fe51198f0f093c6017f2c4c
```

All three match the expected values exactly. No hash was refreshed. The libm-independence regression also passes.

## Trust / escape-hatch audit

The production formal root contains no new `sorry`, `admit`, `axiom`, `unsafe`,
`implemented_by`, `extern`, or `native_decide` occurrence apart from audit/doc text.

Axioms printed by `lake build`:

| Theorem | Axioms |
|---|---|
| `PCS.WireCheck.decodedEvidence_unique_of_wire_ids_nodup` | propext, Quot.sound |
| `PCS.WireCheck.contextCovers_of_exact_context_scope` | propext, Quot.sound |
| `PCS.WireCheck.requiredEvidenceBound_of_commitments` | propext, Quot.sound |
| `PCS.WireCheck.wireCheck_sound` | propext, Quot.sound |
| `PCS.WireCheck.wireCheck_computational_sound` | propext, Classical.choice, Quot.sound |
| `PCS.WireCheck.wireCheck_formal_sound` | propext, Classical.choice, Quot.sound |
| `PCS.WireCheck.wireCheck_empirical_sound` | propext, Classical.choice, Quot.sound |
| `PCS.WireCheck.wireCheck_mixed_sound` | propext, Classical.choice, Quot.sound |
| existing `PCS.Wire.wire_*_sound` | propext, Classical.choice, Quot.sound |

None depends on `sorryAx`, and none uses a PCS-specific axiom.

## What is still outside the theorem

This pass proves:

```text
typed DecisionWire + wireCheck = true -> WellFormed -> Assures
```

It is **not** an end-to-end theorem over delivered ZIP/JSON bytes. Still outside Lean:
raw JSON parsing, JSON Schema implementation, SHA-256/Ed25519, Python scientific
replay, and building the typed raw wire from JSON text.

## Verdicts

| Boundary | Verdict |
|---|---|
| Lean build of the formal root (after the one-line name fix) | PASS |
| `wireCheck_sound` and four staged obligations | PASS |
| Promotion to `PCS/WireCheck.lean` | PASS |
| Axiom / escape-hatch audit | PASS |
| Python full suite (113/113) and targeted suite (35/35) | PASS |
| Frozen v0.5.1 vector reproduces exactly | PASS |
| End-to-end over delivered bytes | NOT CLAIMED |
