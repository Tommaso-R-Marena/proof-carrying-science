# PCS Proof-Carrying Semantic Intelligence v3 — Report

Package: standalone `formal/` Lake package `PCS` (Lean `leanprover/lean4:v4.28.0`, no Mathlib,
`lakefile.toml` unchanged).
Baseline: commit `3dc1eb7` ("Initial commit", the v2 state handed over).  All v3 work is in
the commits after it on this branch.  The production PCS repository (Python
`proof_translation_v06.py`, Claim IR, Proof Obligation Graph, `pcs-proof-proposals-v1`, CLI, CI,
CertiForge) is **not** present in this package.  The work that needs it is listed in §11 and in
`docs/PCS_V3_INTEGRATION.md`.

v1 and v2 are preserved.  No existing theorem statement, module name or import was changed or
removed.  The only edits to pre-existing files are new `import` lines appended to `PCS.lean` and
new modes added to `PCSSemanticCheck.lean`; the v1 and v2 modes still work and are now documented
as NON-PRODUCTION.

---

## 0. What PCS can now prove, what it can check operationally, and what remains unverified

### 0.1 Proved in Lean (kernel-checked; axioms only `propext`, `Classical.choice`, `Quot.sound`)

For the v3 authority `pcs-semantic-check --v3 <authority> <request> <ledger-snapshot>`, the
theorem **`PCS.V2.Semantic.V3.pcs_v3_certified_wire_assurance`** proves the following.  If the
executable prints `CERTIFIED_TRANSLATION` on the raw bytes, then:

1. the three inputs are canonical JSON encodings of a decoded authority configuration, ledger
   snapshot (with clock) and request, and the printed decision is the pure function
   `decideV3` of those values;
2. every core semantic gate holds: no unresolved ambiguity, unique grounding in the approved
   registry, both claims well typed and closed, supported fragment, binder hygiene, the Lean
   rendering is exactly the canonical one, and the Lean-syntax anti-capture gate passes.  No
   stateless v1/v2 receipt was used;
3. every confirmation receipt attests **exactly** the selected interpretation (source text,
   selected structure, ambiguity resolutions) in the authority's context.  Any interpretation it
   could attest is equal to that one in all three components;
4. the selected interpretation and the candidate have **equal denotations in every model and
   every valuation**;
5. the semantic link is either an α/normal-form equality or a rewrite certificate accepted by the
   checker `checkCert`, which is proved sound.  Who produced the certificate makes no difference;
6. every receipt envelope has the known protocol version, an active and unrevoked key of its own
   role, exactly the expected statement, a validity window that contains the clock, an issuance
   time after the ledger genesis, a fresh nonce and a verifying Ed25519 signature.  Nonces are
   distinct, every role meets its quorum of **distinct** issuers, and the claimed axioms are
   allowed;
7. the new ledger is the snapshot extended by exactly the request's nonces.  Any later request
   that presents any of them is rejected (`stepV3_replay_rejected`);
8. for each role and each possible world, if fewer than the role's quorum of active keys are
   dishonest, the fact the role's statement asserts is true;
9. assume three trust conditions: proof-key quorum honesty, `KernelRecordSound` and
   `LeanFrontendFaithful` for the environment fingerprint bound into the receipts.  Then the
   selected interpretation **holds** in the model induced by that Lean environment through the
   registry, for every valuation.

In addition, it is proved that:

* the executable decision **equals** its specification: `decideV3_certified_iff` and
  `stateful_authority_refines_specification` (both soundness and completeness);
* the decision ignores proposer identity, model confidence and self-asserted confirmation
  (`decideV3_ignores_proposer_metadata`);
* a successful elaboration record is **not** a proof (`elaboration_record_is_not_proof`);
* for the restricted fragment, the Lean syntax PCS generates and the Semantic IR have the same
  meaning under Lean-style name resolution (`lean_reading_correspondence`), for **every**
  registry and every environment model;
* strengthening (entailment) is a separate result class with its own authorization and its own
  soundness theorem, and it is never an equivalence (`strengthening_is_not_equivalence`);
* for the CertiForge contract: program equivalence is an equivalence relation, properties
  transfer across it, certified optimization chains compose, and improvement claims are
  independent of the equivalence guarantee.

### 0.2 Checked operationally (executed and tested, **not** formally verified)

* **Persistent replay protection:** `python/pcs_semantic/receipt_store.py` is a SQLite store.
  It does atomic check-and-consume with `BEGIN IMMEDIATE`, a `PRIMARY KEY (scope, nonce)`
  constraint, rollback on every non-certified outcome, release of a result only after `COMMIT`,
  fail-closed open, an explicit genesis on re-initialization, clock-regression rejection and
  run-time revocation.  It is tested across process boundaries, under concurrent use of one
  nonce, with a crash before commit, with lost persistence and with a reset.  It relies on
  SQLite and file-system atomicity and durability.  The Lean side proves only that the decision
  on the restricted snapshot the store passes equals the decision on the full ledger
  (`decideV3_restrict`).
* **Lean elaboration correspondence:** `tools/CheckElaborationV3.lean`, mode `check`, elaborates
  the generated source in the real Lean 4.28.0 frontend.  It checks that the result is
  structurally the expression the syntax tree denotes, that every registry constant resolves to
  the registered name with the registered type, and that the environment fingerprint matches.
  This is the executable check of `LeanFrontendFaithful` for each instance; it is not a proof of
  that condition.
* **Kernel check:** mode `prove` replays the declaration through the Lean kernel
  (`Environment.replay`).  It also checks the statement, the declaration kind (`theorem`) and the
  axiom closure, and it refuses imports and notation injection in the proof file.  A proof made
  with `skipKernelTC` is rejected with `KERNEL_REPLAY_FAILED`.
* **Reference issuers:** `python/pcs_semantic/issuer_v3.py` signs elaboration and proof receipts
  only after these checks succeed.  These issuers use **test keys**.

### 0.3 Unverified / trusted (the residual TCB)

* Ed25519 unforgeability and key secrecy.  Beyond that, the honesty of fewer than *quorum* keys
  per role.  Dishonest, compromised or malicious keys stay in the threat model; the only
  assumption is a bound on how many there are.
* Lean kernel soundness, plus the fidelity of the Lean frontend for the fingerprinted environment
  (`LeanFrontendFaithful`).  This is checked per instance, not proved.
* The Lean compiler and runtime that run `pcs-semantic-check`, the OS, SQLite, the file system,
  and a trusted monotone clock.
* The authority configuration itself: which keys, quorums, registry and fingerprint are approved.
* The human, or other authorized process, that issues confirmation receipts.  **A confirmation
  is evidence that an interpretation was selected. It is not evidence that the interpretation is
  what the speaker meant.**
* **A receipt signed with a test key (all fixtures in this package) is not evidence that a real
  kernel check took place.**  It shows only that the protocol accepts or rejects such receipts
  correctly.

---

## 1. Architecture implemented

```
raw bytes: authority.json  request.json  ledger-snapshot.json (consumed nonces, revocations, genesis, now)
   │  parseCanonicalBytes + decoders (proved round-trip, TranslationV3Json)
   ▼
decideV3 A now S r                                      (TranslationV3, pure, proved)
   ├─ authority well-formedness (role-disjoint keys, quorums ≥ policy)
   ├─ core gates (v1/v2 semantic contract + checkLeanSyntax anti-capture gate, LeanSyntaxV3)
   ├─ legacy-receipt rejection (v1 stateless receipts must be absent)
   ├─ semantic link: normal form equality or re-checked rewrite certificate (v2 checkCert)
   └─ receiptPhase (ReceiptAuthorityV3): per envelope version/role/key/window/genesis/nonce/
      statement/signature, distinct nonces, per-role quorum of distinct issuers, allowed axioms
   ▼
DecisionV3 (outcome, diagnostics, certificate, consumed nonces)   stepV3 → new LedgerV3
   ▼
ReceiptStore.certify (SQLite, BEGIN IMMEDIATE … COMMIT)            (operational, tested)
```

Receipt statements carry domain separation by purpose (`confirmation`, `elaboration`,
`proof`/kernel check, `strengthening-authorization`, CertiForge `program-equivalence`).  Each binds
the authority context: scope, environment fingerprint, toolchain, protocol version, and a
registry digest given as the full encoded registry.  They also bind the exact interpretation or
the exact canonical Lean source.  The injectivity of these encodings is proved
(`confirmationStatement_inj`, `proofStatement_inj`, `elaborationStatement_inj`,
`statements_domain_separated`).

---

## 2. Files added or changed

Lean (new): `PCS/V2/ReceiptAuthorityV3.lean`, `PCS/V2/TranslationV3.lean`,
`PCS/V2/ReceiptThreatModelV3.lean`, `PCS/V2/TranslationV3Json.lean`, `PCS/V2/LeanSyntaxV3.lean`,
`PCS/V2/AssuranceV3.lean`, `PCS/V2/EntailmentV3.lean`, `PCS/V2/CertiForgeAdapterV1.lean`,
`PCS/V2/SemanticV3Audit.lean`, `tools/CheckElaborationV3.lean`.
Lean (changed): `PCS.lean` (imports appended), `PCSSemanticCheck.lean` (modes `--v3` exit 0/3/1
and `--v3-strengthen` exit 4/1; v1/v2 modes labelled NON-PRODUCTION).
Python (new): `python/pcs_semantic/receipts_v3.py`, `python/pcs_semantic/receipt_store.py`,
`python/pcs_semantic/issuer_v3.py`; tests `python/tests/test_semantic_authority_v3.py`,
`test_elaboration_v3.py`, `test_issuer_v3.py`, `test_strengthening_v3.py`, `test_schema_v3.py`.
Tools: `tools/gen_semantic_v3_fixtures.py`, `tools/run_semantic_v3_fixture_tests.sh`,
`tools/gen_semantic_v3_audit.py`, `tools/check_semantic_v3_audit.sh`.
Fixtures: `fixtures/semantic_authority_v3/` (5 authority configs, 37 request/state pairs,
`expected.json`, `env_fingerprint.txt` = `sha256:4c1e3351f54f4daf5394fe963057dba9d5b3d7de41006cf3c9b18736f40422ce`).
Schema: `schemas/semantic_authority_v3.schema.json`.
Docs: `docs/PCS_V3_INTEGRATION.md`, `docs/PCS_CERTIFORGE_ADAPTER_V1.md`, this report.
Hand-off package: `dist/pcs_v3_source_complete.patch` (single patch, baseline `3dc1eb7` → final
revision) and `dist/patches/` (`git format-patch` series).  See §12.

---

## 3. Theorems (names, statements, dependencies)

All are in namespace `PCS.V2.Semantic.V3` unless another namespace is given.  The complete list of
138 audited theorems is in `PCS/V2/SemanticV3Audit.lean`.

### 3.1 Centerpiece — `pcs_v3_certified_wire_assurance` (`PCS/V2/AssuranceV3.lean`)

```lean
theorem pcs_v3_certified_wire_assurance {aRaw rRaw sRaw : ByteArray}
    (h : (semanticCheckV3 aRaw rRaw sRaw).decision.outcome = .certifiedTranslation) :
    ∃ cfg snap r,
      (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfigV3 = some cfg ∧
      (parseCanonicalBytes maxInputBytes sRaw).bind decLedgerSnapshot = some snap ∧
      (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV3 = some r ∧
      (semanticCheckV3 aRaw rRaw sRaw).decision = decideV3 cfg.toAuthority snap.now snap.state r.clamp ∧
      CoreGates cfg.registry r.core.base ∧ NoLegacyReceipts r.core.base ∧
      cfg.toAuthority.wellFormedB = true ∧
      (∀ e ∈ r.receipts, e.role = .confirmation →
        e.statement = confirmationStatement cfg.toAuthority r.core.base.interpretation ∧
        ∀ I' : Interpretation, e.statement = confirmationStatement cfg.toAuthority I' →
          I'.sourceText = r.core.base.interpretation.sourceText ∧
          I'.selected = r.core.base.interpretation.selected ∧
          I'.ambiguities = r.core.base.interpretation.ambiguities) ∧
      (∀ (M : Model) (ρ : String → M.Dom),
        r.core.base.interpretation.selected.denote M ρ ↔ r.core.base.candidate.claim.denote M ρ) ∧
      SemanticallyLinked r.core.base.interpretation r.core.base.candidate
        (semanticCheckV3 aRaw rRaw sRaw).decision.certificate ∧
      ReceiptsValid cfg.toAuthority snap.now snap.state r.clamp ∧
      (semanticCheckV3 aRaw rRaw sRaw).newState =
        some { snap.state with consumed := r.receipts.map (·.nonce) ++ snap.state.consumed } ∧
      (semanticCheckV3 aRaw rRaw sRaw).decision.consumed = r.receipts.map (·.nonce) ∧
      (∀ (W : ReceiptWorld) (role : ReceiptRole),
        DishonestBelow W cfg.toAuthority snap.now role (cfg.toAuthority.quorum role) →
          W.Holds role (expectedStatement cfg.toAuthority r.clamp role)) ∧
      (∀ L : LeanAuthorityWorld,
        DishonestBelow L.W cfg.toAuthority snap.now .proof (cfg.toAuthority.quorum .proof) →
        KernelRecordSound L → LeanFrontendFaithful L cfg.context.envFingerprint cfg.registry →
        ∀ ν, r.core.base.interpretation.selected.denote (modelOf L.env cfg.registry) ν)
```

The proof uses `semanticCheckV3_certified_sound`, `decideV3_certified_sound`,
`confirmationStatement_identifies`, `alphaEquiv_denote_iff` and `translation_certificate_sound`
(v2), `certified_receipt_quorum_assurance` and `certified_translation_holds_in_environment`.  The
last of these uses `lean_reading_correspondence` and `renderClaimLean_eq_print`.

**Why the three trust conditions in item 9 are needed and cannot be removed:**

* `DishonestBelow … .proof q` — a signature is evidence only about the signer.  If quorum-many
  proof keys are dishonest, they can sign anything, and no protocol can then conclude that a
  kernel check happened.  The theorem states the bound explicitly.  When the policy requires no
  proof receipts, `q = 0`, the hypothesis is unsatisfiable, and item 9 gives nothing.  That is
  the correct outcome: PCS claims no truth without a proof record.
* `KernelRecordSound` — this links an honest "kernel accepted source *s* in environment *fp*"
  assertion to the proposition *s* elaborates to, and that proposition to truth (kernel
  soundness).  It concerns the real Lean system, which lies outside the logic.
* `LeanFrontendFaithful` — this says Lean's real parser and elaborator read the printed text as
  `LDecl.denote` describes.  `lean_reading_correspondence` proves the correspondence for PCS's
  model of Lean name resolution.  That the real frontend implements this model is checked per
  instance by `CheckElaborationV3 check`; it is not proved.

### 3.2 Stateful authority and refinement (`TranslationV3.lean`, `ReceiptAuthorityV3.lean`)

| Theorem | Statement (summary) |
|---|---|
| `decideV3_certified_iff` | `outcome = certifiedTranslation ↔ wellFormed ∧ CoreGates ∧ NoLegacyReceipts ∧ semantic link ∧ ReceiptsValid` |
| `stateful_authority_refines_specification` | executable decision ⇒ `CertifiedV3` spec, and `CertifiedV3` with the request's certificate ⇒ executable certifies |
| `decideV3_certified_preserves_denotation` | certified ⇒ `∀ M ρ, I.denote M ρ ↔ C.denote M ρ` |
| `receiptPhase_ok_iff`, `receiptPhase_sound`, `receiptPhase_complete` | receipt phase succeeds exactly when `ReceiptsValid` holds, returning the request's nonces |
| `stepV3_ledger`, `stepV3_rejected_no_consumption`, `stepV3_monotone` | transition: certified ⇒ nonces prepended; rejected ⇒ ledger unchanged; consumed set only grows |
| `stepV3_replay_rejected` | after certification, any request presenting any consumed nonce (any clock, any ledger extending the new one) is not certified |
| `stepV3_consumed_nodup`, `runV3_consumed_nodup`, `runV3_no_double_consumption`, `runV3_ledger` | over any sequence of requests no nonce is consumed twice |
| `decideV3_restrict` | decision on the snapshot restricted to the request's nonces = decision on the full ledger (justifies the store's restricted read) |
| `decideV3_ignores_proposer_metadata` | proposer, model confidence and self-asserted confirmation fields do not change the decision |

### 3.3 Adversarial rejection and threat model (`ReceiptThreatModelV3.lean`)

`replayed_receipt_rejected`, `expired_receipt_rejected`, `future_receipt_rejected`,
`revoked_key_rejected`, `inactive_key_rejected` (rotation), `pre_genesis_receipt_rejected` (ledger
reset), `unknown_version_receipt_rejected`, `forged_signature_rejected`,
`duplicate_nonce_in_request_rejected`, `role_substitution_rejected`,
`cross_context_receipt_rejected` (other scope, environment, toolchain or registry),
`statement_replacement_rejected`, `legacy_receipt_rejected`, `quorum_not_met_rejected`,
`missing_confirmation_rejected`, `missing_proof_rejected`, `statements_domain_separated`.
In each case the theorem states that if the attack is present, the outcome is not
`certifiedTranslation`.
`certified_receipt_assurance` / `certified_receipt_quorum_assurance`: certified, together with
fewer than quorum dishonest active keys for a role, implies that the role's statement holds in
the world.  `certified_kernel_check_record` specializes this to the proof role.

### 3.4 Lean syntax and elaboration (`LeanSyntaxV3.lean`, `AssuranceV3.lean`)

* `renderClaimLean_eq_print` — the canonical source string is the printing of the Lean syntax tree
  `readClaim R c`.
* `lean_reading_correspondence (E : LeanEnvModel) (R : Registry) (c) (hsafe : leanSyntaxSafeB R c = true)
  (hclosed : c.freeVars = []) ν : (readClaim R c).denote E ν ↔ c.denote (modelOf E R) ν`.  This
  holds for every registry and every environment model.  `LProp.denote` resolves identifiers as
  Lean does: a bound name shadows a global one, and dotted names resolve through their head
  component.
* `gate_rejects_reserved_binder`, `capture_breaks_correspondence` — the gate is necessary.
  Without it, a binder named like a registry constant or namespace captures the symbol, and the
  correspondence fails (shown by a counterexample).
* `confirmationStatement_identifies`, `elaboration_record_is_not_proof`,
  `certified_translation_holds_in_environment`.

### 3.5 Logic and strengthening (`EntailmentV3.lean`, namespace `PCS.V2.Semantic` / `.V3`)

`Formula.iff_denote` (↔ as sugar for `(φ→ψ)∧(ψ→φ)`), `entailsF_sound`, `entails_sound`,
`strengthens_sound`, `decideStrengtheningV3_sound`, `stepStrengtheningV3_rejected_no_consumption`,
`strengthening_statement_ne_confirmation`, `ordinary_confirmation_cannot_authorize_strengthening`,
`strengthenCheckV3_certified_sound` (wire level), and `strengthening_is_not_equivalence`.  The last
one gives a certified strengthening where the two claims are not equivalent.  The strengthening
mode prints `CERTIFIED_STRENGTHENING` (exit 4) and never `CERTIFIED_TRANSLATION`.  It requires a
`strengthening-authorization` receipt that is bound to the exact candidate.

### 3.6 CertiForge adapter (`CertiForgeAdapterV1.lean`, namespace `PCS.V2.CertiForge`)

`ProgEquiv.refl/symm/trans`, `progEquiv_property_transfer` (an equivalence-invariant property
moves from P to Q), `chain_equiv` and `certified_chain_property_transfer` (composition of
individually certified steps), `cost_not_invariant` (improvement is not a semantic property),
`exhaustiveEquivB_sound`, `refutesB_sound`, `decideCF_pcsChecked_sound`,
`decideCF_attested_receipts` / `decideCF_attested_sound` (attested mode: the receipts are valid and
equivalence holds under issuer honesty), `counterexample_overrides_receipts`,
`decideCF_ignores_improvement`, `unsupported_semantics_rejected` (effects, native execution and UB
are rejected), `cfStatement_ne_proofStatement`, plus closed examples checked by `decide`
(`Examples.mulTwo_shlOne_pcs_checked`, `mulTwo_equiv_shlOne`, `mulTwo_addOne_refuted`,
`effectful_claim_unsupported`, `no_improvement_claimed_correctly`).  The scope is pure,
straight-line, fixed-width bitvector programs.  No refinement proof is assumed between
CertiForge's Rust verifier and Lean.  See `docs/PCS_CERTIFORGE_ADAPTER_V1.md`.

### 3.7 Axiom audit

`bash tools/check_semantic_v3_audit.sh` → `AUDIT PASS 138/138`.  Every v3 theorem depends only on
`propext`, `Classical.choice` and `Quot.sound`, or on a subset of them.  No `sorryAx`, no
`Lean.ofReduceBool`, no project axiom.  `rg` over the new files finds no `sorry`, `admit`,
`axiom`, `unsafe`, `extern`, `implemented_by` or `native_decide`.

---

## 4. Cryptographic assumptions

Signatures are Ed25519.  The verifier is the v2 Lean implementation `PCS.V2.Ed25519`, the same
one used for v1/v2 receipts.  The formal protocol does **not** assume unforgeability globally.
`ReceiptWorld` / `KeyHonest` model each key as honest or dishonest, and every assurance theorem is
parametric in the number of dishonest keys.  So forgery, key compromise and a malicious issuer all
count as "dishonest key" and are bounded by the quorum.  The fixture keys are deterministic
**test keys** derived in `receipts_v3.py` and are not secret.

## 5. Storage, concurrency and clock assumptions

| Property | Status |
|---|---|
| Decision and ledger transition as functions of the snapshot | **proved** |
| No double consumption over any sequence of decisions | **proved** (`runV3_no_double_consumption`) |
| Restricted snapshot read is sound | **proved** (`decideV3_restrict`) |
| Atomic check-and-consume, concurrency serialization | **tested**; relies on SQLite `BEGIN IMMEDIATE` and the unique key |
| Durability across crash/restart | **tested** (process exits before commit, store reopened in a new process); relies on SQLite with `synchronous=FULL` and `fsync` |
| Lost persistence | fail-closed open (tested); reset needs a new genesis, so old receipts are rejected (proved: `pre_genesis_receipt_rejected`) given a monotone clock |
| Clock | trusted, monotone input; regression rejected by the store (tested); validity windows proved against the given clock |
| Key revocation / rotation | revocation set and validity windows proved to be enforced; correct operation of revocation is operational |

## 6. Supported logical fragment and limitations

Supported: the v1/v2 typed first-order fragment (∀/∃ over registered sorts, ¬, ∧, ∨, →, equality,
grounded predicates and functions, assumptions, explicit binders), the 34 proved v2 rewrite
rules, and ↔ as proved sugar.
Not implemented: typed numerals and arithmetic (no semantics was added, so these constructs are
rejected as unsupported); ↔ as a primitive constructor; a wire codec for CertiForge claims (the
adapter is a Lean-level contract); higher-order quantification; general Lean elaboration
correctness.  Countermodels remain bounded, and search exhaustion is never certification
(`SEARCH_EXHAUSTED` is a non-certifying outcome).

## 7. Adversarial cases (all rejected)

* **Fixtures** (`fixtures/semantic_authority_v3`, 32 negative, 5 positive): replay after
  consumption, duplicate nonce in one request, nonce rewritten after signing, expired,
  not-yet-valid, revoked in config, revoked in ledger, retired / future key rotation, pre-genesis
  after a ledger reset, unknown version, forged signature, attacker key, role field substituted,
  authority key in two roles, false kernel-proof claim signed by a wrong-role key, proof record
  without a kernel check, axiom not allowed, proof quorum with one issuer or with the same issuer
  twice, cross-environment reuse, cross-scope reuse, statement replacement, registry modified
  after receipts, legacy v1 receipts present, missing confirmation or proof, ∀→∃ with valid
  receipts, high model confidence with valid receipts, forged certificate, unknown symbol,
  unresolved ambiguity.
* **Python** (`test_semantic_authority_v3`): replay in the same process and across processes and
  restarts; 16 concurrent submissions in 8 worker processes (8 distinct requests sharing one proof nonce, each submitted twice): exactly one certifies; simulated crash (process exit) before commit: no result released, nothing consumed, retry certifies once;
  lost DB; reset with a new genesis; refused re-initialization; clock regression; run-time
  revocation; rejected requests consume nothing; expired/rotated keys; malformed and
  non-canonical JSON; random receipt mutations checked against an independent Python oracle.
* **Elaboration** (`test_elaboration_v3`): overloaded `∧ ¬ = →` notation, self-looping notation,
  root-level shadowing declarations, namespace change, a changed definition of the same type
  (caught by the fingerprint), an axiom-backed symbol, incorrect argument types, a wrongly typed
  constant, a misleading symbol name, duplicate grounding, a missing constant, non-canonical
  source, binders named like registry namespaces, constants or keywords.
* **Issuer** (`test_issuer_v3`): `sorry`, a custom axiom, unallowed or unclaimed axioms, a
  different statement, `def` instead of `theorem`, a missing declaration, notation hijack, an
  import in the proof file, `skipKernelTC` bypass.
* **Strengthening** (`test_strengthening_v3`): a stronger candidate is never a translation; an
  ordinary confirmation does not authorize strengthening; the authorization is bound to the exact
  candidate; a weaker candidate is rejected; a quantifier-scope change is rejected; replay.
* All v1 (33) and v2 (32) Python tests and all v1/v2 fixtures still pass.

Zero false accepts in this finite campaign is evidence about these cases.  It is not a proof of
general soundness; the general soundness claims are the Lean theorems above.

## 8. Commands executed on the final source revision and results

| Command | Result |
|---|---|
| `rm -rf .lake/build && lake build` | success, 253 jobs, ~19 min; only warning: pre-existing unused variable in `SHA256` |
| `bash tools/check_semantic_v3_audit.sh` | `AUDIT PASS 138/138` |
| `bash tools/run_fixture_tests.sh` | 14 ok |
| `bash tools/run_semantic_fixture_tests.sh` | 36 ok |
| `bash tools/run_semantic_v2_fixture_tests.sh` | 42 checked, 0 failures |
| `bash tools/run_semantic_v3_fixture_tests.sh` | 37 checked, 0 failures |
| `bash tools/run_semantic_v2_end_to_end.sh` | all pass (exit 0) |
| `CheckGoldenFileLiterals` | OK |
| `python3 -m unittest discover -s python/tests` | 124 tests, OK (~290 s) |
| `rg` for `sorry`/`admit`/`axiom`/`unsafe`/`extern`/`native_decide` in new files | none |

## 9. Residual trusted computing base

Lean kernel; Lean compiler and runtime for `pcs-semantic-check`; Lean frontend fidelity for the
pinned fingerprint (checked per instance); Ed25519 together with the quorum honesty bound; the
approved authority configuration and registry; SQLite, the file system and the OS for the store;
a trusted monotone clock; the external confirmation process; the deployed issuers' operational
integrity, bounded by the quorum.

## 10. OPEN items (not done)

1. Integration into the production repository (`proof_translation_v06.py`, Claim IR,
   `pcs-proof-proposals-v1`, CLI, CI).  The exact steps are in `docs/PCS_V3_INTEGRATION.md` §2–§4.
   None of this was executed here.
2. A formal proof of `LeanFrontendFaithful` (it would need a verified Lean frontend).  It is
   checked per instance today.
3. Formal verification of the persistent store.  Today it is a tested reference.
4. Real key custody (HSM/KMS), a trusted time service, deployed issuer services and the human
   confirmation UI with authentication.
5. Typed numerals and arithmetic; ↔ as a primitive; a wire codec and executable mode for
   CertiForge claims; a port of the store to the production database.

## 11. Integration requirements (summary)

See `docs/PCS_V3_INTEGRATION.md`.  In short:

* route translation acceptance only through `ReceiptStore.certify` (or a port that keeps its
  invariants) running `--v3`;
* label v1/v2 decisions non-production;
* add a distinct `CERTIFIED_STRENGTHENING` class;
* pin `env_fingerprint` in the production environment;
* deploy the elaboration and proof issuers as separate services with their own keys;
* add the v3 CI commands from §8.

## 12. Hand-off package

* `dist/pcs_v3_source_complete.patch` — a single binary-safe `git diff 3dc1eb7 HEAD` covering
  every v3 change.
* `dist/patches/*.patch` — the same changes as a `git format-patch` series.  Apply with `git am`
  on a new branch.
* Equivalently, every file listed in §2 is in the source tree of this revision.

## 13. What PCS can truthfully say, and what it cannot

**Can say** (for a v3-certified model-generated translation): the translation was accepted from
canonical wire bytes by an authority whose decision is proved equal to its specification.  The
candidate has the same denotation as the explicitly selected and confirmed structured
interpretation in every model.  Every symbol is uniquely grounded in the approved registry.
Every required receipt was verified, bound to the exact claim, source and environment context,
authorized for its role, fresh and consumed.  It cannot be replayed against the same ledger.
Under the stated issuer-quorum, kernel and frontend conditions, the interpretation holds in the
fingerprinted Lean environment.  No model, search procedure, confidence field or self-asserted
confirmation can cause acceptance.

**Cannot say**: that the interpretation is what the human meant; that the registry's definitions
describe the real world; that a test-key receipt reflects a real kernel check; that the real
Lean frontend is proved faithful; that the SQLite store is formally verified; that persistence
holds beyond SQLite's and the file system's guarantees; that a strengthening is a translation;
or that a finite adversarial campaign proves general soundness.
