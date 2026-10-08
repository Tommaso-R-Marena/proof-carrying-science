# PCS Semantic Translation Contract v1 — implementation report

> **Extended by v2:** see `PCS_PROOF_CARRYING_SEMANTIC_INTELLIGENCE_V2_REPORT.md` (certificate-based equivalence, verified countermodels). Everything in this report still holds.

## 0. Baseline, branch and scope

* **Source baseline.** I worked on the standalone `formal/` Lake package `PCS` (version 0.5.0) that was uploaded. Its Git history has a single commit:
  `07af06ef663d10d90e216acd04f5556373a404d1` ("Initial commit").
  I cannot check that this snapshot matches PR #78 of the integrated repository, because that repository is not present here.
* **Branch.** All work is on the branch `semantic-translation-v1`, forked from that commit. Production `main` was not modified.
* **Toolchain.** The pinned toolchain is unchanged: `leanprover/lean4:v4.28.0`. The project has no Mathlib dependency.
* **Preserved.** No existing Lean file was edited except:
  * `PCS.lean`: nine `import` lines were appended.
  * `lakefile.toml`: a new executable target `pcs-semantic-check` was added and listed among the default targets.

  No existing theorem, module name or import was changed, removed or weakened.
* **Not present here.** The parent `RequestProject` workspace and all Python sources of the full repository are absent. That includes `proof_translation_v06.py`, the Python Claim IR, the Proof Obligation Graph code and the proposal protocol `pcs-proof-proposals-v1`. Python integration that needs those files is listed under §13 (OPEN items).

## 1. Architecture actually implemented

```
 untrusted NL text + model proposal ─┐   (Interpretation.sourceText / proposer /
                                     │    modelAssertsConfirmed: never read by any check)
 authorized structured interpretation│   Interpretation.selected + ambiguity register
        │  ConfirmationReceipt (Ed25519, confirmation-role key, bound to exact text+claim+resolutions)
        ▼
 independent meaning  ⟦·⟧ : SemanticClaim.denote  (compositional, many-sorted, PCS.V2.SemanticIR)
        │
 formal translation candidate (Candidate: claim, groundings, Lean source, decl name,
        │   optional proposed explanation, proposer, model confidence [ignored])
        ▼
 deterministic checker  diagnose / checkTranslation   (PCS.V2.TranslationChecker)
        │   = exactly the certified contract TranslationContract   (translationAccepts_iff)
        │   ⇒ ∀ M ρ, ⟦interpretation⟧ ↔ ⟦candidate⟧               (accepted_translation_preserves_meaning)
        ▼
 Elaboration / Proof receipts (Ed25519, role keys, bound to exact Lean source, decl, axioms)
        ▼
 PCS authority: existing ClaimGraph / ClaimGraphMemo obligation checker, Proposer loop
        (PCS.V2.TranslationAuthority), executable `pcs-semantic-check` (PCSSemanticCheck.lean)
        ▼
 Explanation IR (Lean → human, structural, proved meaning-preserving; prose is untrusted)
```

The seven-way separation the contract requires maps onto the code as follows:

| # | Concept | Where |
|---|---|---|
| 1 | untrusted NL proposal | `Interpretation.sourceText`, `.proposer`, `.modelAssertsConfirmed` (ignored) |
| 2 | authorized structured interpretation | `Interpretation.selected`, `.ambiguities`, `ConfirmationReceipt` |
| 3 | its independent meaning | `SemanticClaim.denote` / `Formula.denote` (`PCS/V2/SemanticIR.lean`) |
| 4 | formal translation candidate | `Candidate` (`PCS/V2/TranslationContract.lean`) |
| 5 | executable semantic validator | `diagnose`, `checkTranslation`, `semanticCheck`, `pcs-semantic-check` |
| 6 | kernel-verified proof obligations | theorems below; the obligation-graph checker `semanticChecker` |
| 7 | external elaboration / runtime / confirmation assumptions | `ExternalWorld`, `ExternalContracts`, `ElaborationBridge` (explicit hypotheses) |

### Reused PCS infrastructure

* `PCS.V2.ClaimGraph` (`Checker`, `CheckerSound`, `checkGraph`, `root_assurance_sound`) and `PCS.V2.ClaimGraphMemo` (`checkGraphMemo`, `checkGraphMemo_eq`). Semantic claims serve as the claim IR, with proved decomposition rules and proof-receipt leaves (`semanticChecker`, `semanticChecker_sound`, `translated_claim_graph_sound(_memo)`).
* `PCS.V2.Proposer` (`Strategy`, `History`, `runLoop`, `loop_output_checked`). The untrusted propose → check → repair loop is reused verbatim (`untrusted_proposer_cannot_bypass_translation_authority`).
* `PCS.V2.Json`, `PCS.V2.JsonRoundtrip` (`ser`, `parse_ser`), `PCS.V2.Canonical` (`parseCanonicalBytes`, `parseCanonicalBytes_complete`). These provide the canonical-JSON gate and the serialization refinement.
* `PCS.V2.Ed25519.verify` (the project's RFC 8032 verifier), `PCS.V2.Ed25519Sign`, `PCS.V2.Base64`. These handle receipt verification and fixture signing.
* The fail-closed registry design of `PCS.V2.ExecutableAuthority` / `FailClosedGate` (unique registration, unknown means reject) is mirrored by `Registry.wellFormedB` / `Registry.resolve`.

## 2. Files added or changed

Added (Lean):
* `PCS/V2/SemanticIR.lean`: typed fragment, registry, models, compositional denotation, free variables, hygiene, typing, type soundness.
* `PCS/V2/SemanticNormalize.lean`: de Bruijn normalization, `≠` desugaring, assumption-set equivalence, and the proofs that they preserve denotation.
* `PCS/V2/ExplanationIR.lean`: Explanation IR, its own semantics, round trip, summaries, and the Lean and literal-English renderers.
* `PCS/V2/TranslationContract.lean`: interpretations, ambiguities, candidates, receipts, authority, the individual predicates and `TranslationContract`.
* `PCS/V2/TranslationChecker.lean`: failure codes, diagnostics, verdicts, the checker, the exact characterisation, the flagship, and the preservation and rejection theorems.
* `PCS/V2/TranslationAuthority.lean`: external world and contracts, the authority theorem, obligation-graph reuse, and proposer non-authority.
* `PCS/V2/TranslationJson.lean`: strict canonical wire format, Ed25519 receipt verification, the pure front end `semanticCheck`, and the refinement theorems.
* `PCS/V2/TranslationFixtures.lean`: 4 positive and 32 adversarial requests, each checked by `decide +kernel` (plus the duplicate-registry authority), and an intended-model example with an in-Lean proof.
* `PCS/V2/TranslationAudit.lean`: `#print axioms` for 46 principal results, printed on every build.
* `PCSSemanticCheck.lean`: executable `pcs-semantic-check` (check mode and `--explain` mode).

Added (tools, fixtures, schema, Python, docs):
* `tools/WriteSemanticFixtures.lean`: deterministic generator of the signed JSON fixtures. It also cross-checks every verdict with the pure front end.
* `tools/run_semantic_fixture_tests.sh`: runs the compiled binary on all fixtures.
* `fixtures/semantic_translation_v1/`: `authority.json`, `authority_duplicate_registry.json`, `claim_safety.json`, `expected.json`, and `requests/*.json` (36 requests).
* `schemas/semantic_translation_v1.schema.json`: JSON Schema for the request, authority and decision documents.
* `python/pcs_semantic/__init__.py`, `python/pcs_semantic/semantic_translation_v1.py`: fail-closed Python client of the Lean authority.
* `python/tests/test_semantic_translation_v1.py`: 33 tests, covering fixtures, wire and receipt adversaries, metadata manipulation, the semantic fuzz campaign with an independent finite-model oracle, explanation, and the repair loop.
* `PCS_SEMANTIC_TRANSLATION_V1_REPORT.md`: this file.

Changed: `PCS.lean` (nine imports appended) and `lakefile.toml` (new executable and default target).

## 3. Supported semantic fragment

* **Sorts.** Registered sort ids. Each one is grounded to a Lean type and a provenance string.
* **Terms.** Variables, and applications of registered function symbols with typed signatures. Constants are nullary functions.
* **Formulas.** `⊤`, `⊥`, registered predicates applied to terms, `=`, `≠`, `¬`, `∧`, `∨`, `→`, and typed quantifiers `∀ x : s, φ` and `∃ x : s, φ`.
* **Claims.** Typed parameters (read universally), an explicit list of assumptions kept apart from the conclusion, and a conclusion. Denotation: `∀ params, (⋀ assumptions) → conclusion`.
* **Semantics.** Many-sorted structures `Model` (domain, sort membership, interpretation of symbols by canonical id). Quantifiers range over the stated sort.
* **Typing.** `Term.sortOf`, `Formula.wellTypedB`, `SemanticClaim.wellTypedB`. Arity and sorts must match, and both sides of an equation must have the same sort. `Term.denote_hasSort` proves type soundness for conforming models and well-typed valuations.

**Known unsupported constructs.** These must be sent as `{"op":"unsupported","construct":…}` and are always rejected with `UNSUPPORTED_CONSTRUCT`; any unknown operator is rejected as `MALFORMED_INPUT`:
* `↔`, which must currently be split into two claims or two implications;
* modal, temporal, deontic and probabilistic operators, and generalised or counting quantifiers ("most", "at least three");
* numerals and arithmetic literals, unless registered as nullary function symbols;
* higher-order quantification, λ, set comprehension, definite descriptions;
* subtyping, polymorphism, and coercions between sorts.

**Deliberately conservative (false rejects, never false accepts).** Only α-renaming, `≠ ⇝ ¬ =` and assumption order/duplication are normalized. The checker therefore rejects candidates that are logically equivalent but differ syntactically: commuted `∧`/`∨`, double negation, De Morgan, quantifier distribution, or an argument order that happens to be equivalent. It also rejects strictly stronger or weaker candidates: it requires equivalence, not entailment.

## 4. Exact theorem names and what they establish

All of these are kernel-checked. Their axioms are printed by `PCS/V2/TranslationAudit.lean`: only `propext`, `Classical.choice` and `Quot.sound` (or a subset), with no `sorryAx` and no `Lean.ofReduceBool`.

**Semantics and normalization** (`SemanticIR`, `SemanticNormalize`)
* `Term.denote_hasSort`, `Term.denoteList_hasSort`: well-typed terms denote elements of their sort, in conforming models under well-typed valuations.
* `Term.toDB_denote`, `Formula.toDB_denote`, `Formula.toDB_denote_nil`: de Bruijn conversion (including `≠` desugaring) is exact for every model, valuation and environment.
* `Formula.alpha_denote_iff`: formulas with equal nameless forms have the same denotation everywhere.
* `SemanticClaim.normalize_denote`: a claim and its normal form have the same denotation.
* `ndenoteClaim_congr_assumptions`: assumption-set equivalence preserves denotation.
* **`alphaEquiv_denote_iff`**: if the normal forms are `NClaim.Equiv`, then **for every model and valuation** the two claims are logically equivalent. This is the justification of the accepted normalization.

**Checker** (`TranslationChecker`)
* **`translationAccepts_iff`** (via `diagnose_eq_nil_iff`): the checker accepts exactly when the certified `TranslationContract` holds. This is the executable/certified refinement inside Lean.
* Supporting characterisations: `translationAccepts_eq_false_iff`, `verdict_accepted_iff`, `accepted_iff_no_diagnostics`, and one component lemma `check*_nil` per diagnostic family.
* **`translation_acceptance_sound`** (flagship): acceptance implies `NoUnresolvedAmbiguity ∧ GroundedSymbols ∧ PreservesQuantifiers ∧ PreservesPolarity ∧ PreservesNegation ∧ PreservesAssumptions ∧ PreservesBindings ∧ NoUnexpectedFreeVariables ∧ SupportedFragment ∧ RoundTripEquivalent`.
* **`accepted_translation_preserves_meaning`** (main preservation theorem): acceptance implies `∀ M ρ, ⟦interpretation.selected⟧ M ρ ↔ ⟦candidate.claim⟧ M ρ`. It holds for **every** model and valuation, which gives `accepted_translation_preserves_meaning_typed` (conforming models, well-typed valuations) as a special case. Logical equivalence in all structures is the strongest semantic relation two claims can have.
* `accepted_explanation_means_interpretation`: the derived Explanation IR means exactly what the selected interpretation means.
* Individual preservation theorems:
  * `accepted_translation_has_no_unresolved_ambiguity`
  * `accepted_translation_preserves_quantifiers`
  * `accepted_translation_preserves_polarity`
  * `accepted_translation_preserves_negation`
  * `accepted_translation_preserves_assumptions`
  * `accepted_translation_preserves_bindings`
  * `accepted_translation_has_no_unexpected_free_variables`
  * `accepted_translation_roundtrips`
  * `accepted_translation_is_confirmed`
  * `accepted_translation_uses_only_grounded_symbols`: every used symbol resolves uniquely, is a registry member, and has exactly one declared grounding equal to its canonical Lean name and provenance.
* Rejection theorems:
  * `rejected_of_not_contract`
  * **`semantically_inequivalent_rejected`** (a candidate that differs in meaning in *any* model is rejected)
  * `unresolved_ambiguity_rejected`, `unresolved_ambiguity_not_accepted`
  * `unknown_symbol_rejected`, `unknown_interpretation_symbol_rejected`, `unknown_definition_rejected`, `incorrect_symbol_identity_rejected`
  * `duplicate_registry_entry_rejected`, `shadowed_grounding_rejected`, `binder_shadowing_symbol_rejected`, `shadowed_or_duplicate_grounding_rejected`
  * `dropped_assumption_rejected`, `added_assumption_rejected`
  * `quantifier_change_rejected`, `polarity_change_rejected`, `negation_change_rejected`, `connective_change_rejected`, `binding_change_rejected`
  * `free_variable_rejected`, `unsupported_construct_rejected`, `ill_typed_rejected`
  * `missing_confirmation_rejected`, `forged_confirmation_rejected`, `misbound_confirmation_rejected`, `model_asserted_confirmation_insufficient`
  * `missing_elaboration_rejected`, `forged_elaboration_rejected`, `missing_proof_rejected`, `forged_proof_rejected`, `disallowed_axiom_rejected`
  * `lean_source_mismatch_rejected`, `explanation_mismatch_rejected`
* **`decision_ignores_model_metadata`**: the full decision (verdict and every diagnostic) is unchanged by the proposer identities, the self-reported confidence and the self-asserted confirmation flag.

**Authority** (`TranslationAuthority`)
* **`translation_authority_sound`**: acceptance plus `ExternalContracts A W` gives:
  1. unconditionally, meaning equivalence for every model and valuation;
  2. `W.Confirmed` of the exact text, claim and ambiguity resolutions;
  3. if elaboration is required, `W.Elaborates` of the exact source and declaration;
  4. if a proof is required, `W.KernelProved` of the exact source and declaration;
  5. if a proof is required, then for every intended model `M` with `ElaborationBridge`, the **selected interpretation holds in `M`**.
* `semanticRule_sound`, `semanticChecker_sound`: the semantic obligation checker meets the existing `CheckerSound` obligations of `PCS.V2.ClaimGraph`.
* `translated_claim_graph_sound`, `translated_claim_graph_sound_memo`: an accepted translation plus an obligation graph accepted by the existing (memoised) checker implies the interpretation holds in the intended model.
* **`untrusted_proposer_cannot_bypass_translation_authority`**, `no_strategy_forges_translation`, `untrusted_proposer_output_confirmed`: for **every** proposer strategy, every output of the existing `runLoop` satisfies the whole contract and preserves meaning, with no hypothesis on the strategy.

**Explanation IR** (`ExplanationIR`)
* **`explanation_roundtrip`**: `(toExplanation R c).toClaim = c` exactly.
* **`explanationIR_preserves_semantics`**: the Explanation IR's own compositional semantics equals the claim's in every model and valuation.
* `toNode_roundtrip`, `toNode_denote`: the corresponding results for single explanation trees.
* `explanation_quantifiers_faithful`, `explanation_negations_faithful`, `explanation_references_grounded`, `explanation_references_complete`: the summary fields are exactly the corresponding structural facts of the claim.

**Wire format and executable** (`TranslationJson`)
* `decTerm_encTerm`, `decFormula_encFormula`, `decClaim_encClaim`, `decExplanation_enc`, `decCandidate_enc`, …, **`decRequest_encRequest`**: the strict decoder inverts the canonical encoder.
* `semanticCheck_decision`: if both inputs decode, the front end's decision is `checkTranslation` of the decoded pair.
* **`semanticCheck_accepted_iff`**: the front end returns `ACCEPTED` iff the bytes decode to a pair satisfying `TranslationContract`.
* `semanticCheck_malformed_request_rejected`: a request that does not decode is rejected.
* **`semanticCheck_encRequest`** (serialization refinement): on the canonical bytes of any request whose encoding is canonical, the front end computes exactly the certified decision on that request.
* `sigOK_authorized`: a verified receipt names a key that is authorized for its role.

**Fixtures** (`TranslationFixtures`; every verdict is checked by `decide +kernel` on the real checker). The positive fixtures are `safety_accepted`, `liveness_accepted`, `arith_accepted` and `unbounded_accepted`. Adversarial fixtures and the codes they must produce are listed in §9. In addition:
* `arith_candidate_denotes`, `arith_interpretation_holds`: in the intended model `natModel`, the accepted candidate means the native Lean proposition `∀ n, n % 2 = 0 → (n+1+1) % 2 = 0`, which is proved in Lean. The proof is transported to the selected interpretation by the preservation theorem. Here the elaboration bridge is replaced by an in-Lean computation.
* `confidence_never_matters`.

## 5. What remains external (TCB)

1. **`ExternalContracts`** (hypothesis): the receipt verifiers are sound. In the executable this means Ed25519 unforgeability under the configured role keys, *and* that each key holder signs only after the real external process ran: human or authorized confirmation, `lake env lean` elaboration, and a kernel proof with the reported axiom list.
2. **`ElaborationBridge R W M`** (hypothesis): a kernel-proved Lean rendering of a well-typed, closed, hygienic claim means that the claim holds in the intended model `M`. In other words, each approved symbol, as a Lean constant, denotes what `M` says. This needs a model of Lean elaboration of the rendered text, which is not formalized. It is discharged internally only for the `natModel` example.
3. **Human intent.** `W.Confirmed` is evidence that an authorized process confirmed an interpretation. It is never treated as a mathematical fact about what the speaker meant.
4. **Runtime.** Three things are trusted rather than proved:
   * that the compiled `pcs-semantic-check` computes `semanticCheck` (compiler and runtime);
   * file IO;
   * that the Python side serializes the intended object.

   The hypothesis `canonical (encRequest r)` of `semanticCheck_encRequest` is a decidable check on each concrete request.
5. **The registry.** The authority configuration decides which symbols are approved, what they ground to, and which keys are authorized.

## 6. Ambiguity policy

* Every interpretation carries an explicit ambiguity register. Each item has a kind (scope, lexical, symbol, temporal, referent, other), a question, and an optional resolution.
* An unresolved item produces `AMBIGUOUS_SCOPE` (for scope) or `UNRESOLVED_AMBIGUITY`. A missing confirmation produces `CONFIRMATION_MISSING`.
* If the only diagnostics are of these kinds, the verdict is `NEEDS_CLARIFICATION`. Otherwise it is `REJECTED`. Neither verdict is ever acceptance.
* The confirmation receipt signs the exact resolutions, so editing a resolution after confirmation is rejected (Python test `test_ambiguity_resolution_edited_after_confirmation`).
* A model's `model_asserts_confirmed: true` is never read (`model_asserted_confirmation_insufficient`, fixture `neg_model_asserted_confirmation_only`).

## 7. Grounding policy

* The registry must be well formed: symbol and sort ids are distinct, and every sort used in a signature is registered.
* Every symbol used by the candidate must resolve uniquely, and the candidate must declare **exactly one** grounding for it, equal to the registry's canonical Lean name and provenance.
* Every declared grounding must name an approved definition.
* Binder names may not coincide with any registered id or Lean name, so a rendered binder cannot capture a constant. They may not re-bind a variable already in scope.
* Hallucinated, substituted, shadowed and duplicate definitions are all rejected (§4, §9).

## 8. Round-trip and explanation policy

* **Round trip.** Claim → Explanation IR → claim is the identity (`explanation_roundtrip`). The round-trip check also requires that any proposer-supplied explanation is *exactly* the derived one; otherwise the result is `ROUNDTRIP_MISMATCH`.
* **Equivalence level.** Equivalence is checked on the structured representation only. No English string is compared or certified.
* **Contents.** The Explanation IR carries:
  * variables with their sorts;
  * assumptions and conclusion as role-labelled trees;
  * all quantifiers in order;
  * the negation count;
  * the referenced definitions and sorts with their Lean names, signatures and provenance;
  * a fixed trust-boundary statement;
  * a fixed "not established" list.
* **Proved.** Its meaning equals the checked claim's (`explanationIR_preserves_semantics`).
* **Not certified.** `renderLiteral` (deterministic literal English) and any future LLM renderer are presentation only.

## 9. Adversarial cases (all rejected or unresolved; kernel-checked and also run on the binary)

Each fixture below is checked by kernel `decide` in `PCS/V2/TranslationFixtures.lean`, and run on the signed JSON version through the binary. Most semantic mutations carry **genuine elaboration and proof receipts for the mutated source**, so they are caught by the semantic checks, not by receipt verification.

| fixture | verdict | required codes |
|---|---|---|
| ∀→∃ (`neg_forall_to_exists`) | REJECTED | QUANTIFIER_MISMATCH |
| ∃→∀ (`neg_exists_to_forall`) | REJECTED | QUANTIFIER_MISMATCH |
| quantifier-order reversal ∀x∃y→∃y∀x | REJECTED | QUANTIFIER_MISMATCH |
| negation dropped | REJECTED | NEGATION_MISMATCH, POLARITY_MISMATCH |
| negation inserted | REJECTED | NEGATION_MISMATCH |
| implication reversed | REJECTED | POLARITY_MISMATCH |
| assumption dropped / added / weakened | REJECTED | ASSUMPTION_DROPPED / ASSUMPTION_ADDED / both |
| variable made free | REJECTED | UNEXPECTED_FREE_VARIABLE |
| variable rebound incorrectly | REJECTED | BINDING_MISMATCH |
| variable capture ∀p∃q→∀q∃q | REJECTED | BINDING_MISMATCH, BINDER_SHADOWING |
| ∧→∨ | REJECTED | CONNECTIVE_MISMATCH |
| unknown definition introduced | REJECTED | UNRESOLVED_SYMBOL, UNKNOWN_DEFINITION |
| similarly named wrong definition (`unsafeAttempt` for `unsafeAt`) | REJECTED | SEMANTIC_MISMATCH |
| right id, wrong Lean definition | REJECTED | INCORRECT_SYMBOL_IDENTITY |
| shadowing second grounding | REJECTED | DUPLICATE_OR_SHADOWED_GROUNDING |
| binder named like a registered symbol | REJECTED | BINDER_SHADOWING |
| duplicate registry entry | REJECTED | REGISTRY_MALFORMED |
| unresolved scope ambiguity | NEEDS_CLARIFICATION | AMBIGUOUS_SCOPE |
| forged confirmation (unauthorized key) | REJECTED | CONFIRMATION_NOT_VERIFIED |
| genuine confirmation of another interpretation | REJECTED | CONFIRMATION_NOT_VERIFIED |
| model-asserted confirmation only | NEEDS_CLARIFICATION | CONFIRMATION_MISSING |
| forged / stale elaboration receipt | REJECTED | ELABORATION_NOT_VERIFIED |
| forged proof receipt; genuinely signed receipt listing `sorryAx` | REJECTED | PROOF_NOT_VERIFIED |
| Lean source ≠ rendering of the structured candidate | REJECTED | LEAN_RENDERING_MISMATCH |
| proposer explanation ≠ derived explanation | REJECTED | ROUNDTRIP_MISMATCH |
| unsupported construct (`generalized_quantifier:most`) | REJECTED | UNSUPPORTED_CONSTRUCT |
| malformed (wrong arity) candidate | REJECTED | ILL_TYPED |
| model confidence 1000 on a failing candidate | REJECTED | NEGATION_MISMATCH |

Further Python adversarial tests run against the binary:
* **Malformed or non-canonical JSON:** whitespace, unsorted keys, a missing or extra field, the wrong schema tag (including `pcs-proof-proposals-v1`), an unknown operator, float or negative confidence, truncated, empty or invalid-UTF-8 input. All produce `MALFORMED_INPUT`.
* **Receipt attacks:**
  * tampered signature;
  * interpretation text or ambiguity resolution edited after confirmation;
  * confirmation replayed from another request;
  * role confusion (an elaboration signature used as a proof signature; a proof key used for confirmation);
  * an edited axiom list;
  * removed receipts.
* **Metadata:** metadata changes on all fixtures leave every verdict unchanged.
* **Semantic fuzz campaign:** 240 seeded mutants, submitted without receipts and with honestly re-rendered sources so that only the semantic checks decide. Every accepted mutant (46, e.g. reordered or duplicated assumptions) was checked against an **independent Python finite-model evaluator** on 25 random models; no false accept was found. 194 mutants were rejected.
* **α-renaming completeness:** 20 consistent α-renamings with shuffled assumptions were all accepted.
* **Repair loop:** feedback drives repair, and a confident but wrong proposer is never accepted.

## 10. Model feedback contract

* Every decision carries deterministic, structured diagnostics: `code`, `component`, and `detail` (paths and skeletons for quantifier and negation mismatches, the offending symbol or grounding, the dropped or added assumption, ambiguity id and question). It also carries `expected_lean_source`.
* `Decision.feedback()` in Python packages these as labels for a future proposer: `accepted`, `verdict`, `failure_codes`, `failing_components`, `diagnostics`, `expected_lean_source`, `needs_clarification`.
* All labels come from PCS's own checker. No Aristotle output is used as a training target, and no model was trained.

## 11. Commands executed and results

All commands were run from the project root on branch `semantic-translation-v1`.

| command | result |
|---|---|
| `lake build` (baseline, before any change) | `EXIT 0`; the only warning is the pre-existing unused variable in `PCS/V2/SHA256.lean:137` |
| `bash tools/run_fixture_tests.sh` (baseline) | 14/14 ok |
| `lake build` (final, all default targets incl. `pcs-semantic-check`) | `Build completed successfully (211 jobs)`, `EXIT 0`; same single pre-existing warning |
| axiom audit (`PCS/V2/TranslationAudit.lean`, part of the build) | 46 results; only `propext`, `Classical.choice`, `Quot.sound` (or subsets); `sorryAx` / `ofReduceBool` occurrences in the build log: 0 |
| `bash tools/run_fixture_tests.sh` (final) | 14/14 ok, exit 0 (existing authority unaffected) |
| `lake env lean --run tools/CheckGoldenFileLiterals.lean` | `OK`, exit 0 |
| `lake env lean --run tools/WriteSemanticFixtures.lean` | 36 fixtures written, every verdict cross-checked by the pure front end; regenerated files are byte-identical to the committed ones (`git status --porcelain fixtures/` empty) |
| `bash tools/run_semantic_fixture_tests.sh` | 36/36 ok, exit 0 |
| `python3 -m unittest discover -s python/tests -v` | `Ran 33 tests … OK` (fuzz: accepted=46, rejected=194) |
| `grep -nE '\b(sorry\|admit\|axiom\|unsafe\|extern\|implemented_by\|native_decide)\b'` over all new Lean files | only comment or string hits (the word "axiom" in prose and diagnostics; the ambiguity id `"unsafe"`); no declarations |

## 12. What PCS can now truthfully say about a model-generated translation

If PCS accepts a translation under authority `A`, then the following is kernel-checked:
* The selected structured interpretation has no unresolved ambiguity.
* It carries a verified confirmation receipt bound to its exact text, structure and resolutions.
* Every symbol the candidate uses is uniquely grounded in the approved registry, with the exact approved Lean name and provenance.
* Both claims are well typed, closed, inside the supported fragment and binder-hygienic.
* Quantifiers, polarity, negations, connectives, assumptions and bindings are preserved.
* The candidate's Lean source is the deterministic rendering of the candidate.
* Any proposer explanation equals the derived Explanation IR.
* Required elaboration and proof receipts verify and are bound to that exact source, declaration and allowed axioms.
* **The meaning of the candidate is logically equivalent to the meaning of the selected interpretation in every model of the symbols and under every valuation.** This is proved from an independent compositional semantics, not from the checker's own conditions.
* This holds for every proposer strategy, whatever it claims about its own confidence or about confirmation.

Under the explicit external contracts (`ExternalContracts`), the confirmation, elaboration and kernel-proof facts hold. Under the explicit `ElaborationBridge` for an intended model, the selected interpretation is true in that model.

## 13. What PCS still cannot truthfully claim — and OPEN items

PCS cannot claim any of the following:
* that the selected interpretation is what the speaker actually meant, or that the English has a unique meaning;
* that arbitrary English, or any English rendering (including `explanation_literal`), is semantically certified;
* that a compiling Lean theorem matches human intent;
* that a Lean proof makes the assumptions or empirical premises true in the world;
* that the proposing model is correct or calibrated;
* that the compiled binary, file IO or the Python bridge are verified;
* that the receipt issuers are honest (this is assumed through `ExternalContracts`);
* that the Lean elaboration of the rendered source means the semantic claim (this is assumed through `ElaborationBridge`, except where it is computed in Lean, as in the `natModel` example).

OPEN items (these need the complete repository or new infrastructure):
1. **Python pipeline integration.** Wire `python/pcs_semantic` into `proof_translation_v06.py`. This requires mapping the Python Claim IR and Proof Obligation Graph nodes to `SemanticClaim` and calling `semantic_translation_v1.check` before any candidate becomes authoritative. It also requires versioning the new fields next to `pcs-proof-proposals-v1`, for example an optional `semantic_translation` member that carries a `pcs-semantic-translation-v1` request. None of these files are in this package.
2. **Receipt issuers.**
   * An elaboration and proof service that runs `lake env lean` on `theorem <decl> : <lean_source> := …`, checks `#print axioms`, and signs an `ElaborationReceipt` or `ProofReceipt`.
   * A human confirmation UI that shows the Explanation IR and signs a `ConfirmationReceipt`.
   * Key management for the three roles.
3. **Elaboration bridge.** Internalize `ElaborationBridge` for registries whose symbols are Lean definitions of the project, by generating the intended `Model` from the registry and proving `renderClaimLean` elaborates to the denotation. This is done only for the `natModel` example.
4. **Fragment extensions.** `↔`, numerals, sound extra normalizations (∧/∨ commutativity and associativity via sorting, double negation), and entailment-based acceptance for intentionally stronger formalizations (a candidate that implies the interpretation). Each needs its own denotation-preservation proof.
5. **Composition with package authority.** Bind a semantic-translation acceptance to a signed PCS package claim, for example by requiring the `Candidate.claim` to equal the decoded claim of a `DomainAdapter` and conjoining with `checkProposal`. The existing theorems compose by conjunction; a dedicated end-to-end theorem is open.

## 14. Recommended next step toward a learned translator

Use `pcs-semantic-check` as the oracle in a propose → check → repair loop: `propose_check_repair` mirrors the proved `runLoop`.
* Log `(request, Decision.feedback())` pairs produced by PCS itself as supervision.
* Begin with the deterministic fields that the checker reveals: `expected_lean_source`, failure codes, and dropped or added assumptions.
* Before any learned component is introduced, implement the elaboration and proof receipt service (OPEN 2), so that accepted translations also carry kernel-proof receipts.
* The model's outputs stay untrusted: only checker acceptance, which the theorems in §4 cover, gives authority.
