import Withdrawal

namespace PCSResearch.ClaimContract

open Withdrawal

/-- Reviewed identifiers for the meaning of a positive bit. -/
inductive Target where
  | causal (model assumptions estimand : String)
  | policy (policy trace criterion : String)
  | mathReference (reference statement : String)
  deriving DecidableEq, Repr

structure Subject where
  source : String
  target : Target
  deriving DecidableEq, Repr

structure Scope where
  subject : Subject
  withdrawalBudget : Nat
  deriving DecidableEq, Repr

inductive Interpretation where
  | unparsed | ambiguous | reviewed (subject : Subject)
  deriving DecidableEq, Repr

structure Evidence (W G : Type) where
  scope : Scope
  worlds : List W
  groups : List G
  agrees : W → G → Bool
  holds : W → Bool

inductive Decision where
  | unparsed | ambiguous | bindingMismatch | invalidEvidence | inconsistent | insufficient
  | decided (polarity : Bool)
  deriving DecidableEq, Repr

structure Receipt where
  scope : Scope
  decision : Decision
  deriving DecidableEq, Repr

private def assess [DecidableEq W] [DecidableEq G] (e : Evidence W G) : Decision :=
  if ¬e.worlds.Nodup ∨ ¬e.groups.Nodup ∨ e.groups.length < e.scope.withdrawalBudget then
    .invalidEvidence
  else if !(e.worlds.any (fun w => e.groups.all (e.agrees w))) then .inconsistent
  else if check e.worlds e.groups e.agrees (fun w => e.holds w == true) e.scope.withdrawalBudget then
    .decided true
  else if check e.worlds e.groups e.agrees (fun w => e.holds w == false) e.scope.withdrawalBudget then
    .decided false
  else .insufficient

def receive [DecidableEq W] [DecidableEq G] (request : Scope) (i : Interpretation)
    (input : Option (Evidence W G)) : Receipt :=
  ⟨request, match i with
    | .unparsed => .unparsed
    | .ambiguous => .ambiguous
    | .reviewed subject =>
      if subject ≠ request.subject then .bindingMismatch else
      match input with
      | none => .insufficient
      | some e => if e.scope = request then assess e else .bindingMismatch⟩

/-- Presentation retains every scope field even for missing or adverse evidence. -/
def Receipt.display (r : Receipt) : Scope × String := (r.scope, match r.decision with
  | .unparsed => "UNPARSED"
  | .ambiguous => "AMBIGUOUS"
  | .bindingMismatch => "BINDING_MISMATCH"
  | .invalidEvidence => "INVALID_EVIDENCE"
  | .inconsistent => "INCONSISTENT"
  | .insufficient => "INSUFFICIENT"
  | .decided p =>
    match r.scope.subject.target with
    | .causal .. => if p then "SUPPORTED_UNDER_CAUSAL_MODEL" else "REFUTED_UNDER_CAUSAL_MODEL"
    | .policy .. => if p then "SATISFIES_SUPPLIED_POLICY" else "VIOLATES_SUPPLIED_POLICY"
    | .mathReference .. => if p then "AGREES_WITH_FORMAL_REFERENCE" else "DIFFERS_FROM_FORMAL_REFERENCE")

/-- Both polarities require the complete evidence to admit a world. A negative
verdict needs universal opposition throughout the same withdrawal budget. -/
private theorem assess_sound [DecidableEq W] [DecidableEq G] (e : Evidence W G) (p : Bool)
    (h : assess e = .decided p) :
    robust e.worlds e.groups e.agrees (fun w => e.holds w == p) e.scope.withdrawalBudget := by
  unfold assess at h
  split at h
  · contradiction
  split at h
  · contradiction
  split at h
  next checked =>
    cases h
    exact (check_exact _ _ _ _ _).mp checked
  next =>
    split at h
    next checked =>
      cases h
      exact (check_exact _ _ _ _ _).mp checked
    next => contradiction

/-- Each decided receipt binds the reviewed source and target, exact input
scope, and requested budget. Its polarity holds for every listed surviving
interpretation under every allowed withdrawal, with a nonvacuous base. -/
theorem decided_sound [DecidableEq W] [DecidableEq G] (q : Scope) (i : Interpretation)
    (input : Option (Evidence W G)) (p : Bool)
    (h : (receive q i input).decision = .decided p) :
    (receive q i input).scope = q ∧ i = .reviewed q.subject ∧
    ∃ e, input = some e ∧ e.scope = q ∧ grounded e.worlds e.groups e.agrees ∧
      ∀ d : G → Bool, cost e.groups d ≤ q.withdrawalBudget →
        ∀ w ∈ e.worlds, survives e.groups e.agrees d w → e.holds w = p := by
  refine ⟨rfl, ?_⟩
  cases i with
  | unparsed | ambiguous => contradiction
  | reviewed s =>
    by_cases hs : s = q.subject
    · subst s
      refine ⟨rfl, ?_⟩
      cases input with
      | none => simp [receive] at h
      | some e =>
        by_cases he : e.scope = q
        · have ha : assess e = .decided p := by simpa [receive, he] using h
          obtain ⟨base, universal⟩ := assess_sound e p ha
          refine ⟨e, rfl, he, base, ?_⟩
          intro d hd w hw survived
          simpa using universal d (he ▸ hd) w hw survived
        · simp [receive, he] at h
    · simp [receive, hs] at h

#print axioms decided_sound
end PCSResearch.ClaimContract
