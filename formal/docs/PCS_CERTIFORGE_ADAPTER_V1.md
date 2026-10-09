# PCS ⇄ CertiForge adapter contract v1 (`pcs-certiforge-equivalence-v1`)

Lean source: `PCS/V2/CertiForgeAdapterV1.lean` (namespace `PCS.V2.CertiForge`).  No part of the
CertiForge repository is imported; the contract fixes only what PCS needs to *receive* an
independently checked program-equivalence certificate.

## Roles

| Actor | Trusted? | Role |
|---|---|---|
| optimizer | **no** | proposes `P ↦ Q` |
| CertiForge checker | only as bounded by the threat model | verifies `P ≡ Q`, signs a receipt |
| PCS (`decideCF`) | yes (proved) | decides whether to accept a scoped claim |

## Semantics in scope: `pcs-slbv-v1`

Pure, total, straight-line SSA programs over `BitVec w` (`SLProg`: `width`, `arity`, `body`,
`outputs`).  Instructions: `const v` and `bin op a b` with `op ∈ {add, sub, mul, and, or, xor,
shl, lshr}`; operands index earlier registers (inputs are registers `0 … arity-1`).  Shifts by
`≥ w` give `0` (Lean `BitVec`).  Denotation: `evalW`.  Equivalence: `ProgEquiv P Q` (same width,
arity, number of outputs, and equal outputs on every input vector).

**Out of scope, rejected as `UNSUPPORTED_SEMANTICS`:** effects/I/O, memory, division, undefined
behaviour, native execution, anything else (`ProgramSemantics.effectful | native |
undefinedBehavior | other`).  CertiForge's actual Rust verifier is **not** assumed to refine this
Lean semantics; if it uses a different semantics, the claim must not be labelled `pcs-slbv-v1`.

## Claim (`CFClaim`)

`semantics`, `source`, `target`, `checker` (approved checker id), optional `counterexample`
(input vector, may be supplied by anyone), optional `improvement` (`metric`, `before`, `after`),
`receipts` (receipt envelopes, protocol `pcs-receipt-v2`, role `proof`, signed by keys of the
adapter's own `AuthorityV3` configuration — not the Lean authority's keys).

Receipt statement (`cfStatement`):
`{checker, context, purpose: "certiforge-program-equivalence-v1", semantics: "pcs-slbv-v1",
source, target}` — domain separated from Lean kernel-check records
(`cfStatement_ne_proofStatement`) and bound to the scope, fingerprint and registry of the adapter
context.

## Decision (`decideCF`) and outcomes

1. authority ill-formed → `INVALID_AUTHORITY`
2. semantics ≠ `pcs-slbv-v1` → `UNSUPPORTED_SEMANTICS`
3. either program ill-formed → `MALFORMED_PROGRAM`
4. supplied counterexample refutes → `REFUTED` (overrides every receipt)
5. small input space (`width × arity ≤ exhaustiveBound`): PCS decides itself →
   `CERTIFIED_EQUIVALENCE_PCS_CHECKED` or `REFUTED`
6. shapes differ → `REFUTED`; checker not approved → `UNAPPROVED_CHECKER`
7. stateful receipt phase (ledger protocol of v3: active unrevoked key, exact statement,
   validity window, after genesis, fresh nonce, signature, distinct-issuer quorum) →
   `CERTIFIED_EQUIVALENCE_ATTESTED` or `RECEIPT_REJECTED`

`stepCF` consumes the receipt nonces only on `CERTIFIED_EQUIVALENCE_ATTESTED`.

## Proved results

| Theorem | Statement |
|---|---|
| `ProgEquiv.refl/symm/trans` | equivalence relation |
| `progEquiv_property_transfer` | equivalent programs satisfy the same *extensional* properties |
| `chain_equiv`, `certified_chain_property_transfer` | a chain of individually equivalent optimization steps composes; properties transfer from first to last |
| `cost_not_invariant` | an equivalent pair with different instruction counts exists: improvements are not implied by equivalence |
| `exhaustiveEquivB_sound` | PCS's own bounded check is sound |
| `refutesB_sound` | a refuting input disproves equivalence |
| `unsupported_semantics_rejected` | non-`pcs-slbv-v1` claims are rejected |
| `decideCF_pcsChecked_sound` | `CERTIFIED_EQUIVALENCE_PCS_CHECKED` ⇒ `ProgEquiv` (unconditional) |
| `decideCF_attested_receipts` | `CERTIFIED_EQUIVALENCE_ATTESTED` ⇒ supported semantics, well-formed programs, approved checker, every envelope valid against `cfStatement`, fresh distinct nonces, quorum |
| `decideCF_attested_sound` | `CERTIFIED_EQUIVALENCE_ATTESTED` ⇒ `ProgEquiv`, **assuming** fewer than quorum active checker keys are dishonest and checker statements mean equivalence (`CFStatementsMeanEquivalence`) |
| `counterexample_overrides_receipts` | a refuting input prevents both certified outcomes |
| `decideCF_ignores_improvement` | the improvement claim never affects the decision |
| `mulTwo_shlOne_pcs_checked`, `mulTwo_equiv_shlOne`, `mulTwo_addOne_refuted`, `effectful_claim_unsupported`, `no_improvement_claimed_correctly` | concrete checked examples |

`improvementVerified` recomputes only the `instruction_count` metric; any other improvement
metric (time, energy, …) is reported as unverified.

## Integration notes for the CertiForge side

* Provide a canonical-JSON wire codec for `CFClaim` (schema sketch in
  `schemas/semantic_authority_v3.schema.json#/$defs/certiforgeClaimV1`); it is **not** implemented
  in this package (OPEN).
* Persist nonces with the same store protocol as the translation authority (separate scope).
* If CertiForge ever produces a Lean-checkable proof of `ProgEquiv`, PCS could accept it without
  the honesty assumption; that path does not exist yet.
