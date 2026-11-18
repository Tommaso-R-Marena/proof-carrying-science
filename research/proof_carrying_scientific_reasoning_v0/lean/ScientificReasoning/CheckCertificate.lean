import ScientificReasoning.Certificates

/-!
# Executable certificate checker (schema v1)

`checkCertificate c = some j → Derives …`
Also enforces unique premise IDs (Lean–Python WF contract).
-/

namespace ScientificReasoning

inductive StepSpec where
  | hyp (premiseId : PropId)
  | andI (left right : Nat)
  | andE1 (src : Nat)
  | andE2 (src : Nat)
  deriving Repr, DecidableEq, Inhabited

structure StructuredCertificate where
  premises : List Premise
  steps : List StepSpec
  conclusionStep : Nat
  deriving Repr, DecidableEq, Inhabited

structure VerifiedJudgment where
  formula : Formula
  support : Support
  assurance : Assurance
  deriving Repr, DecidableEq, Inhabited

def StructuredCertificate.toContext (c : StructuredCertificate) : Context :=
  { premises := c.premises }

/-- Well-formedness: premise ids are pairwise unique. -/
def uniquePremiseIds : List Premise → Bool
  | [] => true
  | p :: rest =>
      !(rest.any (fun q => decide (q.id = p.id))) && uniquePremiseIds rest

theorem mem_of_find?_eq_some {α} (xs : List α) (p : α → Bool) (x : α)
    (h : List.find? p xs = some x) : x ∈ xs := by
  induction xs with
  | nil => simp at h
  | cons a as ih =>
      simp only [List.find?] at h
      split at h
      · next ht => cases h; exact List.mem_cons_self
      · next hf => exact List.mem_cons_of_mem _ (ih h)

def findPremise (ps : List Premise) (i : PropId) : Option Premise :=
  ps.find? (fun p => decide (p.id = i))

def checkStep (ps : List Premise) (prior : List VerifiedJudgment) (st : StepSpec) :
    Option VerifiedJudgment :=
  match st with
  | .hyp pid =>
      match findPremise ps pid with
      | none => none
      | some p =>
          some {
            formula := p.formula
            support := [p.id]
            assurance := Assurance.hypDeclared p.authority
          }
  | .andI l r =>
      match Nat.decLt l prior.length, Nat.decLt r prior.length with
      | isTrue hl, isTrue hr =>
          let jl := prior[l]
          let jr := prior[r]
          some {
            formula := Formula.and jl.formula jr.formula
            support := jl.support ++ jr.support
            assurance := Assurance.meetA jl.assurance jr.assurance
          }
      | _, _ => none
  | .andE1 s =>
      match Nat.decLt s prior.length with
      | isFalse _ => none
      | isTrue hs =>
          let j0 := prior[s]
          match j0.formula with
          | .and φ _ =>
              some { formula := φ, support := j0.support, assurance := j0.assurance }
          | _ => none
  | .andE2 s =>
      match Nat.decLt s prior.length with
      | isFalse _ => none
      | isTrue hs =>
          let j0 := prior[s]
          match j0.formula with
          | .and _ ψ =>
              some { formula := ψ, support := j0.support, assurance := j0.assurance }
          | _ => none

theorem checkStep_sound
    (Γ : Context) (prior : List VerifiedJudgment) (st : StepSpec)
    (hp : ∀ j ∈ prior, Derives Γ j.support j.assurance.declared j.formula)
    (j : VerifiedJudgment) (h : checkStep Γ.premises prior st = some j) :
    Derives Γ j.support j.assurance.declared j.formula := by
  cases st with
  | hyp pid =>
      cases hf : findPremise Γ.premises pid with
      | none => simp [checkStep, hf] at h
      | some p =>
          simp [checkStep, hf] at h
          cases h
          exact Derives.hyp Γ p (mem_of_find?_eq_some _ _ _ hf)
  | andI l r =>
      cases hl : Nat.decLt l prior.length with
      | isFalse => simp [checkStep, hl] at h
      | isTrue hlt =>
          cases hr : Nat.decLt r prior.length with
          | isFalse => simp [checkStep, hl, hr] at h
          | isTrue hrt =>
              simp [checkStep, hl, hr] at h
              cases h
              exact Derives.andI Γ _ _ _ _ _ _
                (hp _ (List.getElem_mem hlt))
                (hp _ (List.getElem_mem hrt))
  | andE1 s =>
      cases hs : Nat.decLt s prior.length with
      | isFalse => simp [checkStep, hs] at h
      | isTrue hst =>
          have hj0 := hp prior[s] (List.getElem_mem hst)
          cases hf : prior[s].formula with
          | atom _ => simp [checkStep, hs, hf] at h
          | not _ => simp [checkStep, hs, hf] at h
          | and φ ψ =>
              simp [checkStep, hs, hf] at h
              cases h
              exact Derives.andE1 Γ _ _ φ ψ (by simpa [hf] using hj0)
  | andE2 s =>
      cases hs : Nat.decLt s prior.length with
      | isFalse => simp [checkStep, hs] at h
      | isTrue hst =>
          have hj0 := hp prior[s] (List.getElem_mem hst)
          cases hf : prior[s].formula with
          | atom _ => simp [checkStep, hs, hf] at h
          | not _ => simp [checkStep, hs, hf] at h
          | and φ ψ =>
              simp [checkStep, hs, hf] at h
              cases h
              exact Derives.andE2 Γ _ _ φ ψ (by simpa [hf] using hj0)

/-- Schema v1 never sets mathEstablished through Hyp/AndI/AndE alone. -/
theorem checkStep_mathEstablished_false
    (ps : List Premise) (prior : List VerifiedJudgment) (st : StepSpec)
    (hprior : ∀ j ∈ prior, j.assurance.mathEstablished = false)
    (j : VerifiedJudgment) (h : checkStep ps prior st = some j) :
    j.assurance.mathEstablished = false := by
  cases st with
  | hyp pid =>
      cases hf : findPremise ps pid with
      | none => simp [checkStep, hf] at h
      | some p =>
          simp [checkStep, hf] at h
          cases h
          rfl
  | andI l r =>
      cases hl : Nat.decLt l prior.length with
      | isFalse => simp [checkStep, hl] at h
      | isTrue hlt =>
          cases hr : Nat.decLt r prior.length with
          | isFalse => simp [checkStep, hl, hr] at h
          | isTrue hrt =>
              simp [checkStep, hl, hr] at h
              cases h
              simp [Assurance.meetA,
                hprior _ (List.getElem_mem hlt),
                hprior _ (List.getElem_mem hrt)]
  | andE1 s =>
      cases hs : Nat.decLt s prior.length with
      | isFalse => simp [checkStep, hs] at h
      | isTrue hst =>
          have hj := hprior prior[s] (List.getElem_mem hst)
          cases hf : prior[s].formula with
          | atom _ => simp [checkStep, hs, hf] at h
          | not _ => simp [checkStep, hs, hf] at h
          | and φ ψ =>
              simp [checkStep, hs, hf] at h
              cases h
              exact hj
  | andE2 s =>
      cases hs : Nat.decLt s prior.length with
      | isFalse => simp [checkStep, hs] at h
      | isTrue hst =>
          have hj := hprior prior[s] (List.getElem_mem hst)
          cases hf : prior[s].formula with
          | atom _ => simp [checkStep, hs, hf] at h
          | not _ => simp [checkStep, hs, hf] at h
          | and φ ψ =>
              simp [checkStep, hs, hf] at h
              cases h
              exact hj

def checkStepsGo (ps : List Premise) : List StepSpec → List VerifiedJudgment → Option (List VerifiedJudgment)
  | [], acc => some acc
  | st :: rest, acc =>
      match checkStep ps acc st with
      | none => none
      | some j => checkStepsGo ps rest (acc ++ [j])

def checkStepsLTR (ps : List Premise) (steps : List StepSpec) : Option (List VerifiedJudgment) :=
  checkStepsGo ps steps []

theorem checkStepsGo_sound
    (Γ : Context) (rest : List StepSpec) (acc : List VerifiedJudgment)
    (hacc : ∀ j ∈ acc, Derives Γ j.support j.assurance.declared j.formula)
    (js : List VerifiedJudgment)
    (h : checkStepsGo Γ.premises rest acc = some js) :
    ∀ j ∈ js, Derives Γ j.support j.assurance.declared j.formula := by
  induction rest generalizing acc with
  | nil =>
      simp [checkStepsGo] at h; cases h; exact hacc
  | cons st rest ih =>
      cases hs : checkStep Γ.premises acc st with
      | none => simp [checkStepsGo, hs] at h
      | some j =>
          simp [checkStepsGo, hs] at h
          have hj := checkStep_sound Γ acc st hacc j hs
          apply ih (acc ++ [j])
          · intro x hx
            cases List.mem_append.1 hx with
            | inl hx => exact hacc x hx
            | inr hx => simp at hx; subst hx; exact hj
          · exact h

theorem checkStepsGo_mathEstablished_false
    (ps : List Premise) (rest : List StepSpec) (acc : List VerifiedJudgment)
    (hacc : ∀ j ∈ acc, j.assurance.mathEstablished = false)
    (js : List VerifiedJudgment)
    (h : checkStepsGo ps rest acc = some js) :
    ∀ j ∈ js, j.assurance.mathEstablished = false := by
  induction rest generalizing acc with
  | nil =>
      simp [checkStepsGo] at h; cases h; exact hacc
  | cons st rest ih =>
      cases hs : checkStep ps acc st with
      | none => simp [checkStepsGo, hs] at h
      | some j =>
          simp [checkStepsGo, hs] at h
          have hj := checkStep_mathEstablished_false ps acc st hacc j hs
          apply ih (acc ++ [j])
          · intro x hx
            cases List.mem_append.1 hx with
            | inl hx => exact hacc x hx
            | inr hx => simp at hx; subst hx; exact hj
          · exact h

theorem checkStepsLTR_sound
    (Γ : Context) (steps : List StepSpec) (js : List VerifiedJudgment)
    (h : checkStepsLTR Γ.premises steps = some js) :
    ∀ j ∈ js, Derives Γ j.support j.assurance.declared j.formula :=
  checkStepsGo_sound Γ steps [] (by intro j hj; cases hj) js h

/-- Reject duplicate premise ids before checking steps (WF contract with Python). -/
def checkCertificate (c : StructuredCertificate) : Option VerifiedJudgment :=
  match decide (uniquePremiseIds c.premises = true) with
  | false => none
  | true =>
      match checkStepsLTR c.premises c.steps with
      | none => none
      | some js =>
          match Nat.decLt c.conclusionStep js.length with
          | isTrue h => some js[c.conclusionStep]
          | isFalse _ => none

/-- Executable trace validity (Finding D fix). Unlike abstract `Certificate.valid`,
this requires the recorded step list to check. -/
def StructuredCertificate.traceValid (c : StructuredCertificate) : Prop :=
  ∃ j, checkCertificate c = some j

theorem checkCertificate_sound
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificate c = some j) :
    Derives c.toContext j.support j.assurance.declared j.formula := by
  cases hu : decide (uniquePremiseIds c.premises = true) with
  | false => simp [checkCertificate, hu] at h
  | true =>
      cases hs : checkStepsLTR c.premises c.steps with
      | none => simp [checkCertificate, hu, hs] at h
      | some js =>
          cases hc : Nat.decLt c.conclusionStep js.length with
          | isFalse => simp [checkCertificate, hu, hs, hc] at h
          | isTrue hlt =>
              simp [checkCertificate, hu, hs, hc] at h
              cases h
              exact checkStepsLTR_sound c.toContext c.steps js
                (by simpa [StructuredCertificate.toContext] using hs)
                _ (List.getElem_mem hlt)

theorem traceValid_implies_derives
    (c : StructuredCertificate) (h : c.traceValid) :
    ∃ j, checkCertificate c = some j ∧
      Derives c.toContext j.support j.assurance.declared j.formula := by
  obtain ⟨j, hj⟩ := h
  exact ⟨j, hj, checkCertificate_sound c j hj⟩

theorem checkCertificate_implies_entails
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificate c = some j) :
    Entails c.toContext j.formula :=
  derives_sound _ _ _ _ (checkCertificate_sound c j h)

theorem hyp_not_math_established
    (ps : List Premise) (prior : List VerifiedJudgment) (pid : PropId) (j : VerifiedJudgment)
    (h : checkStep ps prior (.hyp pid) = some j) :
    j.assurance.mathEstablished = false := by
  cases hf : findPremise ps pid with
  | none => simp [checkStep, hf] at h
  | some p =>
      simp [checkStep, hf] at h
      cases h
      rfl

/-- No schema-v1 acceptance path yields mathEstablished=true without external attestation. -/
theorem checkCertificate_mathEstablished_false
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificate c = some j) :
    j.assurance.mathEstablished = false := by
  cases hu : decide (uniquePremiseIds c.premises = true) with
  | false => simp [checkCertificate, hu] at h
  | true =>
      cases hs : checkStepsLTR c.premises c.steps with
      | none => simp [checkCertificate, hu, hs] at h
      | some js =>
          cases hc : Nat.decLt c.conclusionStep js.length with
          | isFalse => simp [checkCertificate, hu, hs, hc] at h
          | isTrue hlt =>
              simp [checkCertificate, hu, hs, hc] at h
              cases h
              exact checkStepsGo_mathEstablished_false c.premises c.steps []
                (by intro j hj; cases hj) js hs _ (List.getElem_mem hlt)

theorem checkCertificate_requires_unique_ids
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificate c = some j) :
    uniquePremiseIds c.premises = true := by
  cases hu : decide (uniquePremiseIds c.premises = true) with
  | false => simp [checkCertificate, hu] at h
  | true =>
      exact of_decide_eq_true hu

end ScientificReasoning

#print axioms ScientificReasoning.checkCertificate_sound
#print axioms ScientificReasoning.checkCertificate_mathEstablished_false
#print axioms ScientificReasoning.checkCertificate_requires_unique_ids
#print axioms ScientificReasoning.hyp_not_math_established
#print axioms ScientificReasoning.traceValid_implies_derives
