import PCS.V2.SemanticV2Fixtures
import PCS.Examples.Agent
import PCS.Examples.Repro
import PCS.Examples.Bio

/-!
# The intended Lean model of the v2 registry: certificates transfer to real Lean statements

The v2 fixture registry grounds its symbols in the actual Lean declarations of
`PCS.Examples.Agent`, `PCS.Examples.Repro` and `PCS.Examples.Bio` (uninterpreted `opaque`
constants; `tools/CheckRegistryGrounding.lean` checks names and signatures executably).

Here we build, **inside Lean**, the intended model `leanModel` whose carriers are those Lean
types and whose symbols are those Lean constants, prove it conforms to the registry
(`leanModel_conforms`), and prove that the PCS denotation of each fixture claim in
`leanModel` is *literally* the Lean proposition that PCS renders for it
(`*_lean_meaning`).  Combining this with the kernel-checked `CERTIFIED_TRANSLATION` outcomes
gives kernel-checked equivalences between the **actual Lean statements** of the selected
interpretation and of the accepted candidate (`*_certified_lean_statements_equivalent`).

This discharges, for these claims, the semantic part of the elaboration bridge inside Lean:
the remaining external step is only that the rendered *source text* elaborates to these
propositions (checked executably by the test-suite and `tools/run_semantic_v2_end_to_end.sh`).

**Limit (remark, not a theorem):** a finite
countermodel shows that two claims differ in *some* model; it cannot show that the specific
Lean propositions over opaque constants differ — Lean knows nothing about those constants.
The countermodel therefore refutes the translation as a *meaning-preserving* translation
(for all interpretations of the approved symbols), which is exactly the contract PCS checks.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.LeanModel

open PCS.V2.Semantic PCS.V2.Semantic.FixturesV2
open PCS.Examples

/-- One universe of values for all registered sorts. -/
inductive LVal where
  | nat (n : Nat)
  | action (a : Agent.Action)
  | run (r : Repro.Run)
  | dataset (d : Repro.Dataset)
  | digest (d : Repro.Digest)
  | residue (r : Bio.Residue)
  | pos (p : Bio.Pos)
  | junk

def lHasSort : SortId → LVal → Prop
  | "Time", .nat _ => True
  | "Action", .action _ => True
  | "Run", .run _ => True
  | "Dataset", .dataset _ => True
  | "Digest", .digest _ => True
  | "Residue", .residue _ => True
  | "Pos", .pos _ => True
  | _, _ => False

def lFn : String → List LVal → LVal
  | "outputDigest", [.run r] => .digest (Repro.outputDigest r)
  | "posOf", [.residue r] => .pos (Bio.posOf r)
  | _, _ => .junk

def lPred : String → List LVal → Prop
  | "revoked", [.nat t] => Agent.revoked t
  | "before", [.nat i, .nat j] => Agent.before i j
  | "performs", [.nat t, .action a] => Agent.performs t a
  | "forbidden", [.action a] => Agent.forbidden a
  | "withinBudget", [.nat t] => Agent.withinBudget t
  | "sameConfig", [.run a, .run b] => Repro.sameConfig a b
  | "evaluatedOn", [.run r, .dataset d] => Repro.evaluatedOn r d
  | "trainedOn", [.run r, .dataset d] => Repro.trainedOn r d
  | "binding", [.residue r] => Bio.binding r
  | "inSite", [.pos p] => Bio.inSite p
  | "inSiteLegacy", [.pos p] => Bio.inSiteLegacy p
  | "validIndex", [.pos p] => Bio.validIndex p
  | _, _ => False

/-- **The intended model**: Lean's own types and constants. -/
def leanModel : Model := ⟨LVal, lHasSort, lFn, lPred⟩

/-! ## Quantifier transfer lemmas -/

theorem forall_time (Q : LVal → Prop) :
    (∀ d, leanModel.HasSort "Time" d → Q d) ↔ ∀ n : Nat, Q (.nat n) := by
  constructor
  · intro h n; exact h _ trivial
  · intro h d hd; cases d <;> simp_all [leanModel, lHasSort]

theorem forall_action (Q : LVal → Prop) :
    (∀ d, leanModel.HasSort "Action" d → Q d) ↔ ∀ a : Agent.Action, Q (.action a) := by
  constructor
  · intro h a; exact h _ trivial
  · intro h d hd; cases d <;> simp_all [leanModel, lHasSort]

theorem forall_run (Q : LVal → Prop) :
    (∀ d, leanModel.HasSort "Run" d → Q d) ↔ ∀ r : Repro.Run, Q (.run r) := by
  constructor
  · intro h r; exact h _ trivial
  · intro h d hd; cases d <;> simp_all [leanModel, lHasSort]

theorem forall_residue (Q : LVal → Prop) :
    (∀ d, leanModel.HasSort "Residue" d → Q d) ↔ ∀ r : Bio.Residue, Q (.residue r) := by
  constructor
  · intro h r; exact h _ trivial
  · intro h d hd; cases d <;> simp_all [leanModel, lHasSort]

/-! ## Conformance -/

/-- `leanModel` respects every registered function signature. -/
theorem leanModel_conforms : leanModel.Conforms registry := by
  intro f e ss r hres hk ds hds
  obtain ⟨hmem, hid⟩ := Registry.resolve_mem hres
  simp only [registry, prov, List.mem_cons, List.mem_nil_iff, or_false] at hmem
  rcases hmem with rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl <;>
    simp only [SymKind.fn.injEq, reduceCtorEq] at hk
  · obtain ⟨rfl, rfl⟩ := hk
    subst hid
    cases hds with
    | cons h1 h2 =>
      cases h2
      rename_i d
      cases d <;> simp_all [leanModel, lHasSort, lFn]
  · obtain ⟨rfl, rfl⟩ := hk
    subst hid
    cases hds with
    | cons h1 h2 =>
      cases h2
      rename_i d
      cases d <;> simp_all [leanModel, lHasSort, lFn]

/-! ## The PCS meaning in `leanModel` is the rendered Lean statement -/

/-- AI safety, selected interpretation. -/
theorem rev_interpretation_lean_meaning (ρ : String → LVal) :
    revClaim.denote leanModel ρ ↔
      ∀ i : Nat, Agent.revoked i → ∀ j : Nat, ∀ a : Agent.Action,
        Agent.before i j ∧ Agent.performs j a → ¬ Agent.forbidden a := by
  simp only [SemanticClaim.denote, revClaim, denoteParams, Formula.denote, P, v,
    Term.denoteList, Term.denote, update, List.mem_singleton, forall_eq]
  rw [forall_time]
  apply forall_congr'; intro i
  apply imp_congr
  · simp [leanModel, lPred]
  · rw [forall_time]; apply forall_congr'; intro j
    rw [forall_action]; apply forall_congr'; intro a
    simp [leanModel, lPred]

/-- AI safety, accepted candidate (quantifiers exchanged, `→ ¬` as negated conjunction). -/
theorem rev_candidate_lean_meaning (ρ : String → LVal) :
    revPosClaim.denote leanModel ρ ↔
      ∀ r : Nat, Agent.revoked r → ∀ act : Agent.Action, ∀ t : Nat,
        ¬ (Agent.forbidden act ∧ (Agent.performs t act ∧ Agent.before r t)) := by
  simp only [SemanticClaim.denote, revPosClaim, denoteParams, Formula.denote, P, v,
    Term.denoteList, Term.denote, update, List.mem_singleton, forall_eq]
  rw [forall_time]
  apply forall_congr'; intro r
  apply imp_congr
  · simp [leanModel, lPred]
  · rw [forall_action]; apply forall_congr'; intro a
    rw [forall_time]; apply forall_congr'; intro t
    simp [leanModel, lPred]

/-- Reproducibility, selected interpretation. -/
theorem repro_interpretation_lean_meaning (ρ : String → LVal) :
    reproClaim.denote leanModel ρ ↔
      ∀ r1 r2 : Repro.Run, Repro.sameConfig r1 r2 →
        Repro.outputDigest r1 = Repro.outputDigest r2 := by
  simp only [SemanticClaim.denote, reproClaim, denoteParams, Formula.denote, P, v,
    Term.denoteList, Term.denote, update, List.not_mem_nil, false_implies, implies_true,
    true_implies]
  rw [forall_run]; apply forall_congr'; intro r1
  rw [forall_run]; apply forall_congr'; intro r2
  simp [leanModel, lPred, lFn]

/-- Reproducibility, accepted candidate (binders exchanged, equation flipped). -/
theorem repro_candidate_lean_meaning (ρ : String → LVal) :
    reproPosClaim.denote leanModel ρ ↔
      ∀ b a : Repro.Run, Repro.sameConfig a b →
        Repro.outputDigest b = Repro.outputDigest a := by
  simp only [SemanticClaim.denote, reproPosClaim, denoteParams, Formula.denote, P, v,
    Term.denoteList, Term.denote, update, List.not_mem_nil, false_implies, implies_true,
    true_implies]
  rw [forall_run]; apply forall_congr'; intro b
  rw [forall_run]; apply forall_congr'; intro a
  simp [leanModel, lPred, lFn]

/-- Biology, selected interpretation. -/
theorem bio_interpretation_lean_meaning (ρ : String → LVal) :
    bioClaim.denote leanModel ρ ↔
      ∀ x : Bio.Residue, Bio.binding x →
        Bio.inSite (Bio.posOf x) ∧ Bio.validIndex (Bio.posOf x) := by
  simp only [SemanticClaim.denote, bioClaim, denoteParams, Formula.denote, P, v,
    Term.denoteList, Term.denote, update, List.not_mem_nil, false_implies, implies_true,
    true_implies]
  rw [forall_residue]; apply forall_congr'; intro x
  simp [leanModel, lPred, lFn]

/-- Biology, accepted candidate (contrapositive with De Morgan). -/
theorem bio_candidate_lean_meaning (ρ : String → LVal) :
    bioPosClaim.denote leanModel ρ ↔
      ∀ y : Bio.Residue, (¬ Bio.inSite (Bio.posOf y) ∨ ¬ Bio.validIndex (Bio.posOf y)) →
        ¬ Bio.binding y := by
  simp only [SemanticClaim.denote, bioPosClaim, denoteParams, Formula.denote, P, v,
    Term.denoteList, Term.denote, update, List.not_mem_nil, false_implies, implies_true,
    true_implies]
  rw [forall_residue]; apply forall_congr'; intro y
  simp [leanModel, lPred, lFn]

/-! ## Certificates transfer to the actual Lean statements -/

/-- **AI safety**: the kernel-checked `CERTIFIED_TRANSLATION` of `revPosReq` yields a
    kernel-checked equivalence of the two *Lean* statements over the real declarations. -/
theorem rev_certified_lean_statements_equivalent :
    (∀ i : Nat, Agent.revoked i → ∀ j : Nat, ∀ a : Agent.Action,
        Agent.before i j ∧ Agent.performs j a → ¬ Agent.forbidden a) ↔
    (∀ r : Nat, Agent.revoked r → ∀ act : Agent.Action, ∀ t : Nat,
        ¬ (Agent.forbidden act ∧ (Agent.performs t act ∧ Agent.before r t))) := by
  rw [← rev_interpretation_lean_meaning (fun _ => .junk),
    ← rev_candidate_lean_meaning (fun _ => .junk)]
  exact decideV2_certified_preserves_denotation rev_certified leanModel _

/-- **Reproducibility.** -/
theorem repro_certified_lean_statements_equivalent :
    (∀ r1 r2 : Repro.Run, Repro.sameConfig r1 r2 →
        Repro.outputDigest r1 = Repro.outputDigest r2) ↔
    (∀ b a : Repro.Run, Repro.sameConfig a b →
        Repro.outputDigest b = Repro.outputDigest a) := by
  rw [← repro_interpretation_lean_meaning (fun _ => .junk),
    ← repro_candidate_lean_meaning (fun _ => .junk)]
  exact decideV2_certified_preserves_denotation repro_certified leanModel _

/-- **Biology.** -/
theorem bio_certified_lean_statements_equivalent :
    (∀ x : Bio.Residue, Bio.binding x →
        Bio.inSite (Bio.posOf x) ∧ Bio.validIndex (Bio.posOf x)) ↔
    (∀ y : Bio.Residue, (¬ Bio.inSite (Bio.posOf y) ∨ ¬ Bio.validIndex (Bio.posOf y)) →
        ¬ Bio.binding y) := by
  rw [← bio_interpretation_lean_meaning (fun _ => .junk),
    ← bio_candidate_lean_meaning (fun _ => .junk)]
  exact decideV2_certified_preserves_denotation bio_certified leanModel _

end PCS.V2.Semantic.LeanModel
