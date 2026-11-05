import PCS.V2.TranslationAuthority

/-!
# Kernel-checked positive and adversarial fixtures for the semantic translation checker

Every verdict below is decided by the Lean kernel (`decide`) on the actual checker
`translationAccepts` / `diagnose`; no fixture is checked only by running a program.

The fixture authority uses a *stand-in* receipt verifier (`fixtureAuthority`): a receipt
verifies iff it names the fixture authority and carries the fixture token.  It plays the
role of the Ed25519 verifier used by the executable (`AuthorityConfig.toAuthority`); the
signed JSON versions of these fixtures are produced by `tools/WriteSemanticFixtures.lean`
and run against the compiled binary by `tools/run_semantic_fixture_tests.sh` and the Python
tests.

Positive fixtures (all `ACCEPTED`):

* `safety` — "The agent never acts unsafely after permission is revoked", selected reading
  `∀ t i j, revokedAt t i → before i j → ¬ unsafeAt t j`, candidate α-renamed with the
  assumptions in a different order;
* `liveness` — `∀ t i, requested t i → ∃ j, before i j ∧ responded t j`;
* `arith` — `∀ n, even n → even (succ (succ n))`, with an internal kernel proof in the
  intended model `natModel` (`arith_interpretation_holds`): for this registry the
  elaboration bridge is replaced by an in-Lean computation of the denotation;
* `unbounded` — `∀ x, ∃ y, lt x y ∧ y ≠ x` against a candidate written with `¬ (y = x)`.

Adversarial fixtures (all rejected, with the expected failure code present): quantifier
∀→∃, ∃→∀ and order reversal, dropped and inserted negation, reversed implication,
dropped / added / weakened assumption, free variable, wrong rebinding, variable capture,
∧→∨, unknown definition, similarly-named wrong definition, wrong Lean identity for a
symbol, shadowing grounding, binder shadowing a symbol, duplicate registry entry,
unresolved ambiguity (`NEEDS_CLARIFICATION`), forged / missing / mis-bound confirmation,
model-asserted confirmation, forged elaboration and proof receipts, `sorryAx` proof,
mismatching Lean source, mismatching proposer explanation, unsupported construct,
ill-typed (malformed) candidate, and "high confidence" on a failing candidate.  Most
mutations are submitted **with genuine receipts for the mutated Lean source**, so they are
caught by the semantic checks, not by receipt verification.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.Fixtures

open PCS.V2.Semantic

/-! ## Approved symbol environment -/

def v (x : String) : Term := .var x
def P (p : String) (args : List Term) : Formula := .pred p args

def prov (m : String) : String := "PCS/Examples/" ++ m ++ ".lean"

def registry : Registry :=
  { sorts := [⟨"Trace", "PCS.Examples.Trace", prov "Safety"⟩, ⟨"Time", "Nat", "Lean core"⟩,
      ⟨"Nat", "Nat", "Lean core"⟩],
    symbols := [
      ⟨"revokedAt", "PCS.Examples.Safety.revokedAt", .pred ["Trace", "Time"], prov "Safety"⟩,
      ⟨"unsafeAt", "PCS.Examples.Safety.unsafeAt", .pred ["Trace", "Time"], prov "Safety"⟩,
      ⟨"unsafeAttempt", "PCS.Examples.Safety.unsafeAttempt", .pred ["Trace", "Time"], prov "Safety"⟩,
      ⟨"before", "PCS.Examples.Safety.before", .pred ["Time", "Time"], prov "Safety"⟩,
      ⟨"requested", "PCS.Examples.Safety.requested", .pred ["Trace", "Time"], prov "Safety"⟩,
      ⟨"responded", "PCS.Examples.Safety.responded", .pred ["Trace", "Time"], prov "Safety"⟩,
      ⟨"even", "PCS.Examples.Arith.isEven", .pred ["Nat"], prov "Arith"⟩,
      ⟨"lt", "Nat.lt", .pred ["Nat", "Nat"], "Lean core"⟩,
      ⟨"succ", "Nat.succ", .fn ["Nat"] "Nat", "Lean core"⟩] }

/-- Canonical grounding of a symbol (what an honest proposer declares). -/
def ground (f : String) : SymbolRef :=
  match registry.resolve f with
  | some e => ⟨f, e.leanName, e.provenance⟩
  | none => ⟨f, "?", "?"⟩

def fixtureAuthorityName : String := "pcs-fixture-authority"
def fixtureToken : String := "fixture-valid-signature"

/-- The fixture authority (stand-in receipt verifiers; see module doc). -/
def authority : Authority :=
  { registry := registry,
    requireElaboration := true,
    requireProof := true,
    allowedAxioms := ["propext", "Classical.choice", "Quot.sound"],
    verifyConfirmation := fun r => r.authority == fixtureAuthorityName && r.signature == fixtureToken,
    verifyElaboration := fun r => r.authority == fixtureAuthorityName && r.signature == fixtureToken,
    verifyProof := fun r => r.authority == fixtureAuthorityName && r.signature == fixtureToken }

/-! ## Request builders -/

def interp (text : String) (c : SemanticClaim) (amb : List Ambiguity := []) : Interpretation :=
  { sourceText := text, proposer := "model:untrusted", modelAssertsConfirmed := true,
    selected := c, ambiguities := amb }

def confirm (I : Interpretation) : ConfirmationReceipt :=
  ⟨I.sourceText, I.selected, I.ambiguities, fixtureAuthorityName, fixtureToken⟩

/-- An honest candidate: canonical groundings, rendered source, no explanation. -/
def cand (c : SemanticClaim) (syms : List String) : Candidate :=
  { claim := c, groundings := syms.map ground, leanSource := renderClaimLean registry c,
    declName := "pcs_claim", explanation := none, proposer := "model:untrusted",
    modelConfidence := 900 }

/-- A request with genuine confirmation, elaboration and proof receipts for the candidate's
    own source. -/
def request (I : Interpretation) (C : Candidate) : Request :=
  { interpretation := I, confirmation := some (confirm I), candidate := C,
    elaboration := some ⟨C.leanSource, C.declName, fixtureAuthorityName, fixtureToken⟩,
    proof := some ⟨C.leanSource, C.declName, ["propext"], fixtureAuthorityName, fixtureToken⟩ }

def codes (req : Request) : List FailureCode := (diagnose authority req).map (·.code)

/-! ## Positive fixtures -/

def safetyText : String := "The agent never acts unsafely after permission is revoked."

def safetyAmb : List Ambiguity :=
  [⟨"after", .temporal, "Does 'after' mean strictly later?", some "strictly later time (before i j)"⟩,
   ⟨"unsafe", .symbol, "Which notion of 'unsafe'?", some "PCS.Examples.Safety.unsafeAt"⟩,
   ⟨"agent", .referent, "Which agent?", some "the agent whose trace is t (every trace)"⟩]

def safetyClaim : SemanticClaim :=
  { params := [⟨"t", "Trace"⟩, ⟨"i", "Time"⟩, ⟨"j", "Time"⟩],
    assumptions := [P "revokedAt" [v "t", v "i"], P "before" [v "i", v "j"]],
    conclusion := .not (P "unsafeAt" [v "t", v "j"]) }

/-- α-renamed, assumptions reordered. -/
def safetyCandClaim : SemanticClaim :=
  { params := [⟨"tr", "Trace"⟩, ⟨"a", "Time"⟩, ⟨"b", "Time"⟩],
    assumptions := [P "before" [v "a", v "b"], P "revokedAt" [v "tr", v "a"]],
    conclusion := .not (P "unsafeAt" [v "tr", v "b"]) }

def safetySyms : List String := ["before", "revokedAt", "unsafeAt"]

def safetyI : Interpretation := interp safetyText safetyClaim safetyAmb
def safetyReq : Request := request safetyI (cand safetyCandClaim safetySyms)

theorem safety_accepted : translationAccepts authority safetyReq = true := by decide +kernel
theorem safety_verdict : (checkTranslation authority safetyReq).verdict = .accepted := by decide +kernel

def livenessClaim : SemanticClaim :=
  { params := [⟨"t", "Trace"⟩, ⟨"i", "Time"⟩],
    assumptions := [P "requested" [v "t", v "i"]],
    conclusion := .quant .ex "j" "Time" (.and (P "before" [v "i", v "j"]) (P "responded" [v "t", v "j"])) }

def livenessCandClaim : SemanticClaim :=
  { params := [⟨"tr", "Trace"⟩, ⟨"s", "Time"⟩],
    assumptions := [P "requested" [v "tr", v "s"]],
    conclusion := .quant .ex "u" "Time" (.and (P "before" [v "s", v "u"]) (P "responded" [v "tr", v "u"])) }

def livenessSyms : List String := ["before", "requested", "responded"]
def livenessI : Interpretation := interp "Every request is eventually answered." livenessClaim
def livenessReq : Request := request livenessI (cand livenessCandClaim livenessSyms)

theorem liveness_accepted : translationAccepts authority livenessReq = true := by decide +kernel

def arithClaim : SemanticClaim :=
  { params := [], assumptions := [],
    conclusion := .quant .all "n" "Nat"
      (.imp (P "even" [v "n"]) (P "even" [.app "succ" [.app "succ" [v "n"]]])) }

def arithCandClaim : SemanticClaim :=
  { params := [], assumptions := [],
    conclusion := .quant .all "m" "Nat"
      (.imp (P "even" [v "m"]) (P "even" [.app "succ" [.app "succ" [v "m"]]])) }

def arithI : Interpretation := interp "Adding two to an even number gives an even number." arithClaim
def arithReq : Request := request arithI (cand arithCandClaim ["even", "succ"])

theorem arith_accepted : translationAccepts authority arithReq = true := by decide +kernel

def unboundedClaim : SemanticClaim :=
  { params := [], assumptions := [],
    conclusion := .quant .all "x" "Nat" (.quant .ex "y" "Nat"
      (.and (P "lt" [v "x", v "y"]) (.ne (v "y") (v "x")))) }

def unboundedCandClaim : SemanticClaim :=
  { params := [], assumptions := [],
    conclusion := .quant .all "p" "Nat" (.quant .ex "q" "Nat"
      (.and (P "lt" [v "p", v "q"]) (.not (.eq (v "q") (v "p"))))) }

def unboundedI : Interpretation := interp "Every number has a different, larger number." unboundedClaim
def unboundedReq : Request := request unboundedI (cand unboundedCandClaim ["lt"])

theorem unbounded_accepted : translationAccepts authority unboundedReq = true := by decide +kernel

/-- The deterministic Lean rendering of the accepted safety candidate. -/
theorem safety_lean_source :
    renderClaimLean registry safetyCandClaim =
      "∀ (tr : PCS.Examples.Trace) (a : Nat) (b : Nat), (PCS.Examples.Safety.before a b) → " ++
      "(PCS.Examples.Safety.revokedAt tr a) → (¬ (PCS.Examples.Safety.unsafeAt tr b))" := by decide +kernel

/-! ### Intended model for the arithmetic symbols, and an internal kernel proof -/

/-- Intended model: natural numbers, `even n ↔ n % 2 = 0`, `lt` is `<`, `succ` is `+1`. -/
def natModel : Model :=
  { Dom := Nat,
    HasSort := fun _ _ => True,
    fn := fun f ds => match f, ds with
      | "succ", [n] => n + 1
      | _, _ => 0,
    pred := fun p ds => match p, ds with
      | "even", [n] => n % 2 = 0
      | "lt", [a, b] => a < b
      | _, _ => False }

/-- In the intended model the accepted candidate means the native Lean proposition. -/
theorem arith_candidate_denotes (ρ : String → Nat) :
    arithCandClaim.denote natModel ρ ↔ ∀ n : Nat, n % 2 = 0 → (n + 1 + 1) % 2 = 0 := by
  simp [arithCandClaim, SemanticClaim.denote, denoteParams, Formula.denote, P, v,
    Term.denoteList, Term.denote, natModel, update]

/-- **Kernel-verified obligation, transported to the human-selected interpretation**: the
    selected interpretation holds in the intended model.  (Here no external elaboration
    bridge is needed: the denotation is computed inside Lean.) -/
theorem arith_interpretation_holds (ρ : String → Nat) : arithClaim.denote natModel ρ := by
  have h : arithCandClaim.denote natModel ρ :=
    (arith_candidate_denotes ρ).mpr (fun n hn => by omega)
  have := accepted_translation_preserves_meaning arith_accepted natModel ρ
  exact this.mpr h

/-! ## Adversarial fixtures -/

/-- Replace the candidate claim (honest groundings, re-rendered source and **genuine
    receipts for the mutated source**). -/
def mutate (base : Request) (c : SemanticClaim) (syms : List String) : Request :=
  request base.interpretation (cand c syms)

-- ∀ → ∃ (inner quantifier)
def qAllToEx : Request := mutate arithReq
  { arithCandClaim with conclusion := (.quant .ex "m" "Nat"
      (.imp (P "even" [v "m"]) (P "even" [.app "succ" [.app "succ" [v "m"]]]))) } ["even", "succ"]
theorem qAllToEx_rejected : translationAccepts authority qAllToEx = false := by decide +kernel
theorem qAllToEx_code : FailureCode.quantifierMismatch ∈ codes qAllToEx := by decide +kernel

-- ∃ → ∀
def qExToAll : Request := mutate livenessReq
  { livenessCandClaim with conclusion := (.quant .all "u" "Time"
      (.and (P "before" [v "s", v "u"]) (P "responded" [v "tr", v "u"]))) } livenessSyms
theorem qExToAll_rejected : translationAccepts authority qExToAll = false := by decide +kernel
theorem qExToAll_code : FailureCode.quantifierMismatch ∈ codes qExToAll := by decide +kernel

-- quantifier-order reversal: ∀x ∃y  ↦  ∃y ∀x
def qOrder : Request := mutate unboundedReq
  { unboundedCandClaim with conclusion := (.quant .ex "q" "Nat" (.quant .all "p" "Nat"
      (.and (P "lt" [v "p", v "q"]) (.not (.eq (v "q") (v "p")))))) } ["lt"]
theorem qOrder_rejected : translationAccepts authority qOrder = false := by decide +kernel
theorem qOrder_code : FailureCode.quantifierMismatch ∈ codes qOrder := by decide +kernel

-- negation disappears
def negDropped : Request := mutate safetyReq
  { safetyCandClaim with conclusion := P "unsafeAt" [v "tr", v "b"] } safetySyms
theorem negDropped_rejected : translationAccepts authority negDropped = false := by decide +kernel
theorem negDropped_codes : FailureCode.negationMismatch ∈ codes negDropped ∧
    FailureCode.polarityMismatch ∈ codes negDropped := by decide +kernel

-- negation inserted
def negInserted : Request := mutate arithReq
  { arithCandClaim with conclusion := (.quant .all "m" "Nat"
      (.imp (P "even" [v "m"]) (.not (P "even" [.app "succ" [.app "succ" [v "m"]]])))) } ["even", "succ"]
theorem negInserted_rejected : translationAccepts authority negInserted = false := by decide +kernel
theorem negInserted_code : FailureCode.negationMismatch ∈ codes negInserted := by decide +kernel

-- implication direction reversed
def impReversed : Request := mutate arithReq
  { arithCandClaim with conclusion := (.quant .all "m" "Nat"
      (.imp (P "even" [.app "succ" [.app "succ" [v "m"]]]) (P "even" [v "m"]))) } ["even", "succ"]
theorem impReversed_rejected : translationAccepts authority impReversed = false := by decide +kernel
theorem impReversed_code : FailureCode.polarityMismatch ∈ codes impReversed := by decide +kernel

-- assumption dropped
def asmDropped : Request := mutate safetyReq
  { safetyCandClaim with assumptions := [P "revokedAt" [v "tr", v "a"]] } safetySyms
theorem asmDropped_rejected : translationAccepts authority asmDropped = false := by decide +kernel
theorem asmDropped_code : FailureCode.assumptionDropped ∈ codes asmDropped := by decide +kernel

-- extra assumption added
def asmAdded : Request := mutate safetyReq
  { safetyCandClaim with assumptions := safetyCandClaim.assumptions ++ [P "before" [v "b", v "a"]] }
  safetySyms
theorem asmAdded_rejected : translationAccepts authority asmAdded = false := by decide +kernel
theorem asmAdded_code : FailureCode.assumptionAdded ∈ codes asmAdded := by decide +kernel

-- assumption weakened (revokedAt t i replaced by True): a different claim
def asmWeakened : Request := mutate safetyReq
  { safetyCandClaim with assumptions := [P "before" [v "a", v "b"], .tt] } safetySyms
theorem asmWeakened_rejected : translationAccepts authority asmWeakened = false := by decide +kernel
theorem asmWeakened_codes : FailureCode.assumptionDropped ∈ codes asmWeakened ∧
    FailureCode.assumptionAdded ∈ codes asmWeakened := by decide +kernel

-- a variable becomes free (binder `b` removed)
def freeVar : Request := mutate safetyReq
  { safetyCandClaim with params := [⟨"tr", "Trace"⟩, ⟨"a", "Time"⟩] } safetySyms
theorem freeVar_rejected : translationAccepts authority freeVar = false := by decide +kernel
theorem freeVar_code : FailureCode.unexpectedFreeVariable ∈ codes freeVar := by decide +kernel

-- a variable is rebound incorrectly (unsafeAt tr a instead of unsafeAt tr b)
def rebound : Request := mutate safetyReq
  { safetyCandClaim with conclusion := .not (P "unsafeAt" [v "tr", v "a"]) } safetySyms
theorem rebound_rejected : translationAccepts authority rebound = false := by decide +kernel
theorem rebound_code : FailureCode.bindingMismatch ∈ codes rebound := by decide +kernel

-- variable capture: ∀p ∃q lt p q ↦ ∀q ∃q lt q q
def capture : Request := mutate unboundedReq
  { unboundedCandClaim with conclusion := (.quant .all "q" "Nat" (.quant .ex "q" "Nat"
      (.and (P "lt" [v "q", v "q"]) (.not (.eq (v "q") (v "q")))))) } ["lt"]
theorem capture_rejected : translationAccepts authority capture = false := by decide +kernel
theorem capture_codes : FailureCode.bindingMismatch ∈ codes capture ∧
    FailureCode.binderShadowing ∈ codes capture := by decide +kernel

-- ∧ ↦ ∨
def andToOr : Request := mutate livenessReq
  { livenessCandClaim with conclusion := (.quant .ex "u" "Time"
      (.or (P "before" [v "s", v "u"]) (P "responded" [v "tr", v "u"]))) } livenessSyms
theorem andToOr_rejected : translationAccepts authority andToOr = false := by decide +kernel
theorem andToOr_code : FailureCode.connectiveMismatch ∈ codes andToOr := by decide +kernel

-- an unknown definition is introduced
def unknownDef : Request := mutate safetyReq
  { safetyCandClaim with conclusion := .not (P "unsafeActionHallucinated" [v "tr", v "b"]) }
  (safetySyms ++ ["unsafeActionHallucinated"])
theorem unknownDef_rejected : translationAccepts authority unknownDef = false := by decide +kernel
theorem unknownDef_codes : FailureCode.unresolvedSymbol ∈ codes unknownDef ∧
    FailureCode.unknownDefinition ∈ codes unknownDef := by decide +kernel

-- a similarly named but different approved definition is substituted
def similarName : Request := mutate safetyReq
  { safetyCandClaim with conclusion := .not (P "unsafeAttempt" [v "tr", v "b"]) }
  ["before", "revokedAt", "unsafeAttempt"]
theorem similarName_rejected : translationAccepts authority similarName = false := by decide +kernel
theorem similarName_code : FailureCode.semanticMismatch ∈ codes similarName := by decide +kernel

-- the right symbol id, but grounded to a different Lean definition
def wrongIdentity : Request :=
  let C := cand safetyCandClaim safetySyms
  request safetyI { C with groundings := [ground "before", ground "revokedAt",
    ⟨"unsafeAt", "PCS.Examples.Safety.unsafeAt'", prov "Safety"⟩] }
theorem wrongIdentity_rejected : translationAccepts authority wrongIdentity = false := by decide +kernel
theorem wrongIdentity_code : FailureCode.incorrectSymbolIdentity ∈ codes wrongIdentity := by decide +kernel

-- a registered symbol is shadowed by a second grounding
def shadowGrounding : Request :=
  let C := cand safetyCandClaim safetySyms
  request safetyI { C with groundings := C.groundings ++
    [⟨"unsafeAt", "Evil.unsafeAt", "attacker"⟩] }
theorem shadowGrounding_rejected : translationAccepts authority shadowGrounding = false := by decide +kernel
theorem shadowGrounding_code :
    FailureCode.duplicateOrShadowedGrounding ∈ codes shadowGrounding := by decide +kernel

-- a binder is named like a registered symbol (would capture it in the Lean source)
def binderShadow : Request := mutate safetyReq
  { params := [⟨"tr", "Trace"⟩, ⟨"before", "Time"⟩, ⟨"b", "Time"⟩],
    assumptions := [P "before" [v "before", v "b"], P "revokedAt" [v "tr", v "before"]],
    conclusion := .not (P "unsafeAt" [v "tr", v "b"]) } safetySyms
theorem binderShadow_rejected : translationAccepts authority binderShadow = false := by decide +kernel
theorem binderShadow_code : FailureCode.binderShadowing ∈ codes binderShadow := by decide +kernel

-- duplicate registry entry (registry-level shadowing)
def dupAuthority : Authority :=
  { authority with registry := { registry with symbols := registry.symbols ++
      [⟨"unsafeAt", "Evil.unsafeAt", .pred ["Trace", "Time"], "attacker"⟩] } }
theorem dupRegistry_rejected : translationAccepts dupAuthority safetyReq = false := by decide +kernel

-- an ambiguity remains unresolved ⇒ NEEDS_CLARIFICATION (never accepted)
def ambiguousI : Interpretation := interp safetyText safetyClaim
  (safetyAmb ++ [⟨"scope", .scope, "Does 'never' scope over all traces or the current one?", none⟩])
def ambiguousReq : Request := request ambiguousI (cand safetyCandClaim safetySyms)
theorem ambiguous_rejected : translationAccepts authority ambiguousReq = false := by decide +kernel
theorem ambiguous_needs_clarification :
    (checkTranslation authority ambiguousReq).verdict = .needsClarification := by decide +kernel

-- forged confirmation (wrong signature)
def forgedConfirmation : Request :=
  { safetyReq with confirmation := some { confirm safetyI with signature := "forged" } }
theorem forgedConfirmation_rejected : translationAccepts authority forgedConfirmation = false := by decide +kernel
theorem forgedConfirmation_verdict :
    (checkTranslation authority forgedConfirmation).verdict = .rejected := by decide +kernel

-- genuine confirmation of a *different* interpretation (e.g. without the negation)
def misboundConfirmation : Request :=
  { safetyReq with confirmation := some (confirm { safetyI with
      selected := { safetyClaim with conclusion := P "unsafeAt" [v "t", v "j"] } }) }
theorem misboundConfirmation_rejected :
    translationAccepts authority misboundConfirmation = false := by decide +kernel

-- model asserts confirmation but there is no receipt
def modelOnlyConfirmation : Request := { safetyReq with confirmation := none }
theorem modelOnlyConfirmation_rejected :
    translationAccepts authority modelOnlyConfirmation = false := by decide +kernel
theorem modelOnlyConfirmation_code :
    codes modelOnlyConfirmation = [FailureCode.confirmationMissing] := by decide +kernel

-- forged elaboration receipt
def forgedElaboration : Request :=
  { safetyReq with elaboration := some ⟨safetyReq.candidate.leanSource, "pcs_claim",
      fixtureAuthorityName, "forged"⟩ }
theorem forgedElaboration_rejected : translationAccepts authority forgedElaboration = false := by decide +kernel
theorem forgedElaboration_code :
    codes forgedElaboration = [FailureCode.elaborationNotVerified] := by decide +kernel

-- elaboration receipt for a different source
def staleElaboration : Request :=
  { safetyReq with elaboration := some ⟨"True", "pcs_claim", fixtureAuthorityName, fixtureToken⟩ }
theorem staleElaboration_rejected : translationAccepts authority staleElaboration = false := by decide +kernel

-- forged proof receipt
def forgedProof : Request :=
  { safetyReq with proof := some ⟨safetyReq.candidate.leanSource, "pcs_claim", ["propext"],
      "someone-else", fixtureToken⟩ }
theorem forgedProof_rejected : translationAccepts authority forgedProof = false := by decide +kernel
theorem forgedProof_code : codes forgedProof = [FailureCode.proofNotVerified] := by decide +kernel

-- genuinely signed proof receipt that depends on `sorryAx`
def sorryProof : Request :=
  { safetyReq with proof := some ⟨safetyReq.candidate.leanSource, "pcs_claim",
      ["propext", "sorryAx"], fixtureAuthorityName, fixtureToken⟩ }
theorem sorryProof_rejected : translationAccepts authority sorryProof = false := by decide +kernel

-- Lean source that is not the rendering of the structured candidate
def sourceMismatch : Request :=
  let C := cand safetyCandClaim safetySyms
  let C' := { C with leanSource := "∀ (tr : PCS.Examples.Trace) (a : Nat) (b : Nat), True" }
  request safetyI C'
theorem sourceMismatch_rejected : translationAccepts authority sourceMismatch = false := by decide +kernel
theorem sourceMismatch_code : FailureCode.leanRenderingMismatch ∈ codes sourceMismatch := by decide +kernel

-- proposer-supplied explanation that differs from the derived one (round-trip mismatch)
def explanationMismatch : Request :=
  let C := cand safetyCandClaim safetySyms
  request safetyI { C with explanation := some (toExplanation registry safetyClaim |>.toClaim |>
    fun c => toExplanation registry { c with conclusion := P "unsafeAt" [v "t", v "j"] }) }
theorem explanationMismatch_rejected :
    translationAccepts authority explanationMismatch = false := by decide +kernel
theorem explanationMismatch_code :
    FailureCode.roundtripMismatch ∈ codes explanationMismatch := by decide +kernel

-- unsupported construct (generalized quantifier "most")
def unsupportedReq : Request := mutate safetyReq
  { safetyCandClaim with conclusion := .unsupported "generalized_quantifier:most" } safetySyms
theorem unsupported_rejected : translationAccepts authority unsupportedReq = false := by decide +kernel
theorem unsupported_code : FailureCode.unsupportedConstruct ∈ codes unsupportedReq := by decide +kernel

-- malformed (ill-typed) candidate: wrong arity
def illTypedReq : Request := mutate safetyReq
  { safetyCandClaim with conclusion := .not (P "unsafeAt" [v "tr"]) } safetySyms
theorem illTyped_rejected : translationAccepts authority illTypedReq = false := by decide +kernel
theorem illTyped_code : FailureCode.illTyped ∈ codes illTypedReq := by decide +kernel

-- "high confidence" does not help a failing candidate
def highConfidence : Request :=
  let c : Candidate := { negDropped.candidate with modelConfidence := 1000, proposer := "model:very-confident" }
  { negDropped with candidate := c }
theorem highConfidence_rejected : translationAccepts authority highConfidence = false := by decide +kernel

/-- The verdict on a model-metadata-only variation is the same, for every confidence. -/
theorem confidence_never_matters (conf : Nat) :
    checkTranslation authority { negDropped with candidate :=
      { negDropped.candidate with modelConfidence := conf } } =
    checkTranslation authority negDropped := by
  have := decision_ignores_model_metadata authority negDropped conf negDropped.interpretation.proposer
    negDropped.candidate.proposer negDropped.interpretation.modelAssertsConfirmed
  simpa using this

end PCS.V2.Semantic.Fixtures
