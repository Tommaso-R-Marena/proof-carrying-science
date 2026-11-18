import ScientificReasoning.CheckCertificate

/-!
# Completeness via explicit proof terms (sorry-free)

`Derives` ↔ ∃ ProofTerm.interpret (unique ids).
`ProofTerm.compile` produces certificates accepted by `checkCertificate`.
-/

namespace ScientificReasoning

theorem uniquePremiseIds_cons
    (p : Premise) (rest : List Premise)
    (h : uniquePremiseIds (p :: rest) = true) :
    (∀ q ∈ rest, q.id ≠ p.id) ∧ uniquePremiseIds rest = true := by
  simp only [uniquePremiseIds] at h
  cases hany : rest.any (fun q => decide (q.id = p.id)) with
  | true => simp [hany] at h
  | false =>
      simp [hany] at h
      refine ⟨?_, h⟩
      intro q hq heq
      have : rest.any (fun r => decide (r.id = p.id)) = true :=
        (List.any_eq_true).2 ⟨q, hq, by simpa [heq]⟩
      simp [this] at hany

theorem findPremise_of_mem_unique
    (ps : List Premise) (p : Premise) (hp : p ∈ ps)
    (hu : uniquePremiseIds ps = true) :
    findPremise ps p.id = some p := by
  induction ps with
  | nil => cases hp
  | cons q rest ih =>
      simp only [findPremise, List.find?]
      have ⟨hne, hurest⟩ := uniquePremiseIds_cons q rest hu
      cases hp with
      | head => simp
      | tail _ hp' =>
          have hneq : q.id ≠ p.id := fun he => hne p hp' he.symm
          simp [decide_eq_false hneq]
          exact ih hp' hurest

def shiftStep (off : Nat) : StepSpec → StepSpec
  | .hyp p => .hyp p
  | .andI l r => .andI (l + off) (r + off)
  | .andE1 s => .andE1 (s + off)
  | .andE2 s => .andE2 (s + off)

def shiftSteps (off : Nat) (ss : List StepSpec) : List StepSpec :=
  ss.map (shiftStep off)

theorem checkStepsGo_append
    (ps : List Premise) (r1 r2 : List StepSpec) (acc mid js : List VerifiedJudgment)
    (h1 : checkStepsGo ps r1 acc = some mid)
    (h2 : checkStepsGo ps r2 mid = some js) :
    checkStepsGo ps (r1 ++ r2) acc = some js := by
  induction r1 generalizing acc mid with
  | nil =>
      simp [checkStepsGo] at h1; cases h1; simpa using h2
  | cons st r ih =>
      simp [checkStepsGo] at h1
      cases hs : checkStep ps acc st with
      | none => simp [hs] at h1
      | some j =>
          simp [hs] at h1
          simp [checkStepsGo, hs]
          exact ih (acc ++ [j]) mid h1 h2

theorem getElem_append_offset {α} (as bs : List α) (i : Nat) (hi : i < bs.length) :
    (as ++ bs)[as.length + i]'(by simp [List.length_append]; omega) = bs[i] := by
  have h₁ : as.length ≤ as.length + i := Nat.le_add_right _ _
  have h₂ : as.length + i < (as ++ bs).length := by simp [List.length_append]; omega
  simpa [Nat.add_sub_cancel_left] using
    (List.getElem_append_right (as := as) (bs := bs) (i := as.length + i) h₁ (h₂ := h₂))

private theorem decLt_eq_isTrue {n m : Nat} (h : n < m) :
    Nat.decLt n m = isTrue h := Subsingleton.elim _ _

theorem checkStep_shift
    (ps : List Premise) (prior acc : List VerifiedJudgment) (st : StepSpec)
    (j : VerifiedJudgment) (h : checkStep ps acc st = some j) :
    checkStep ps (prior ++ acc) (shiftStep prior.length st) = some j := by
  cases st with
  | hyp pid =>
      simpa [checkStep, shiftStep] using h
  | andI l r =>
      match hl : Nat.decLt l acc.length, hr : Nat.decLt r acc.length with
      | isFalse _, _ => simp [checkStep, hl] at h
      | isTrue _, isFalse _ => simp [checkStep, hl, hr] at h
      | isTrue hlt, isTrue hrt =>
          simp [checkStep, hl, hr] at h
          cases h
          let off := prior.length
          have hlt' : l + off < (prior ++ acc).length := by
            simp [List.length_append, off]; omega
          have hrt' : r + off < (prior ++ acc).length := by
            simp [List.length_append, off]; omega
          have el : (prior ++ acc)[l + off]'(hlt') = acc[l]'(hlt) := by
            simpa [Nat.add_comm, off] using getElem_append_offset prior acc l hlt
          have er : (prior ++ acc)[r + off]'(hrt') = acc[r]'(hrt) := by
            simpa [Nat.add_comm, off] using getElem_append_offset prior acc r hrt
          change checkStep ps (prior ++ acc) (.andI (l + off) (r + off)) = some _
          unfold checkStep
          have dlt := decLt_eq_isTrue hlt'
          have drt := decLt_eq_isTrue hrt'
          simp only [dlt, drt]
          simp [el, er]
  | andE1 s =>
      match hs : Nat.decLt s acc.length with
      | isFalse _ => simp [checkStep, hs] at h
      | isTrue hst =>
          simp [checkStep, hs] at h
          cases hf : (acc[s]).formula with
          | atom _ => simp [hf] at h
          | not _ => simp [hf] at h
          | and φ ψ =>
              simp [hf] at h; cases h
              let off := prior.length
              have hs' : s + off < (prior ++ acc).length := by
                simp [List.length_append, off]; omega
              have el : (prior ++ acc)[s + off]'(hs') = acc[s]'(hst) := by
                simpa [Nat.add_comm, off] using getElem_append_offset prior acc s hst
              change checkStep ps (prior ++ acc) (.andE1 (s + off)) = some _
              unfold checkStep
              have d := decLt_eq_isTrue hs'
              simp only [d]
              simp [el, hf]
  | andE2 s =>
      match hs : Nat.decLt s acc.length with
      | isFalse _ => simp [checkStep, hs] at h
      | isTrue hst =>
          simp [checkStep, hs] at h
          cases hf : (acc[s]).formula with
          | atom _ => simp [hf] at h
          | not _ => simp [hf] at h
          | and φ ψ =>
              simp [hf] at h; cases h
              let off := prior.length
              have hs' : s + off < (prior ++ acc).length := by
                simp [List.length_append, off]; omega
              have el : (prior ++ acc)[s + off]'(hs') = acc[s]'(hst) := by
                simpa [Nat.add_comm, off] using getElem_append_offset prior acc s hst
              change checkStep ps (prior ++ acc) (.andE2 (s + off)) = some _
              unfold checkStep
              have d := decLt_eq_isTrue hs'
              simp only [d]
              simp [el, hf]

theorem checkStepsGo_shift
    (ps : List Premise) (steps : List StepSpec) (prior acc js : List VerifiedJudgment)
    (h : checkStepsGo ps steps acc = some js) :
    checkStepsGo ps (shiftSteps prior.length steps) (prior ++ acc) =
      some (prior ++ js) := by
  induction steps generalizing acc with
  | nil =>
      simp [checkStepsGo, shiftSteps] at h ⊢; cases h; rfl
  | cons st rest ih =>
      simp [checkStepsGo] at h
      cases hs : checkStep ps acc st with
      | none => simp [hs] at h
      | some j =>
          simp [hs] at h
          have hs' := checkStep_shift ps prior acc st j hs
          simp [checkStepsGo, shiftSteps, List.map_cons, hs']
          have := ih (acc ++ [j]) h
          simpa [List.append_assoc] using this

theorem checkStepsLTR_concat_shift
    (ps : List Premise) (steps₁ steps₂ : List StepSpec)
    (js₁ js₂ : List VerifiedJudgment)
    (h1 : checkStepsLTR ps steps₁ = some js₁)
    (h2 : checkStepsLTR ps steps₂ = some js₂) :
    checkStepsLTR ps (steps₁ ++ shiftSteps js₁.length steps₂) = some (js₁ ++ js₂) := by
  have h2' :
      checkStepsGo ps (shiftSteps js₁.length steps₂) js₁ = some (js₁ ++ js₂) := by
    simpa [List.append_nil] using
      checkStepsGo_shift ps steps₂ js₁ [] js₂ (by simpa [checkStepsLTR] using h2)
  have h1' : checkStepsGo ps steps₁ [] = some js₁ := by simpa [checkStepsLTR] using h1
  simpa [checkStepsLTR] using
    checkStepsGo_append ps steps₁ (shiftSteps js₁.length steps₂) [] js₁ (js₁ ++ js₂) h1' h2'

theorem checkStepsGo_length
    (ps : List Premise) (steps : List StepSpec) (acc js : List VerifiedJudgment)
    (h : checkStepsGo ps steps acc = some js) :
    js.length = acc.length + steps.length := by
  induction steps generalizing acc with
  | nil =>
      simp [checkStepsGo] at h; cases h; simp
  | cons st rest ih =>
      simp [checkStepsGo] at h
      cases hs : checkStep ps acc st with
      | none => simp [hs] at h
      | some j =>
          simp [hs] at h
          have := ih (acc ++ [j]) h
          simp at this ⊢; omega

theorem checkStepsLTR_length
    (ps : List Premise) (steps : List StepSpec) (js : List VerifiedJudgment)
    (h : checkStepsLTR ps steps = some js) :
    js.length = steps.length := by
  have := checkStepsGo_length ps steps [] js (by simpa [checkStepsLTR] using h)
  simpa using this

theorem checkStepsLTR_snoc_andI
    (ps : List Premise) (steps : List StepSpec) (js : List VerifiedJudgment)
    (l r : Nat) (hl : l < js.length) (hr : r < js.length)
    (h : checkStepsLTR ps steps = some js) :
    checkStepsLTR ps (steps ++ [.andI l r]) = some (js ++ [{
      formula := Formula.and js[l].formula js[r].formula
      support := js[l].support ++ js[r].support
      assurance := Assurance.meetA js[l].assurance js[r].assurance
    }]) := by
  have hgo : checkStepsGo ps steps [] = some js := by simpa [checkStepsLTR] using h
  have hstep : checkStep ps js (.andI l r) = some {
      formula := Formula.and js[l].formula js[r].formula
      support := js[l].support ++ js[r].support
      assurance := Assurance.meetA js[l].assurance js[r].assurance
    } := by
    unfold checkStep
    have dlt := decLt_eq_isTrue hl
    have drt := decLt_eq_isTrue hr
    simp only [dlt, drt]
  simpa [checkStepsLTR] using
    checkStepsGo_append ps steps [.andI l r] [] js (js ++ [_]) hgo (by
      simp [checkStepsGo, hstep])

theorem checkStepsLTR_snoc_andE1
    (ps : List Premise) (steps : List StepSpec) (js : List VerifiedJudgment)
    (s : Nat) (hs : s < js.length) (φ ψ : Formula)
    (hf : js[s].formula = Formula.and φ ψ)
    (h : checkStepsLTR ps steps = some js) :
    checkStepsLTR ps (steps ++ [.andE1 s]) = some (js ++ [{
      formula := φ
      support := js[s].support
      assurance := js[s].assurance
    }]) := by
  have hgo : checkStepsGo ps steps [] = some js := by simpa [checkStepsLTR] using h
  have hstep : checkStep ps js (.andE1 s) = some {
      formula := φ
      support := js[s].support
      assurance := js[s].assurance
    } := by
    unfold checkStep
    have d := decLt_eq_isTrue hs
    simp only [d, hf]
  simpa [checkStepsLTR] using
    checkStepsGo_append ps steps [.andE1 s] [] js (js ++ [_]) hgo (by
      simp [checkStepsGo, hstep])

theorem checkStepsLTR_snoc_andE2
    (ps : List Premise) (steps : List StepSpec) (js : List VerifiedJudgment)
    (s : Nat) (hs : s < js.length) (φ ψ : Formula)
    (hf : js[s].formula = Formula.and φ ψ)
    (h : checkStepsLTR ps steps = some js) :
    checkStepsLTR ps (steps ++ [.andE2 s]) = some (js ++ [{
      formula := ψ
      support := js[s].support
      assurance := js[s].assurance
    }]) := by
  have hgo : checkStepsGo ps steps [] = some js := by simpa [checkStepsLTR] using h
  have hstep : checkStep ps js (.andE2 s) = some {
      formula := ψ
      support := js[s].support
      assurance := js[s].assurance
    } := by
    unfold checkStep
    have d := decLt_eq_isTrue hs
    simp only [d, hf]
  simpa [checkStepsLTR] using
    checkStepsGo_append ps steps [.andE2 s] [] js (js ++ [_]) hgo (by
      simp [checkStepsGo, hstep])

inductive ProofTerm where
  | hyp : PropId → ProofTerm
  | andI : ProofTerm → ProofTerm → ProofTerm
  | andE1 : ProofTerm → ProofTerm
  | andE2 : ProofTerm → ProofTerm
  deriving Repr, DecidableEq, Inhabited

def ProofTerm.compile : ProofTerm → List StepSpec × Nat
  | .hyp pid => ([.hyp pid], 0)
  | .andI l r =>
      ( (ProofTerm.compile l).1 ++
          shiftSteps (ProofTerm.compile l).1.length (ProofTerm.compile r).1 ++
          [.andI (ProofTerm.compile l).2
            ((ProofTerm.compile l).1.length + (ProofTerm.compile r).2)]
      , (ProofTerm.compile l).1.length + (ProofTerm.compile r).1.length )
  | .andE1 t =>
      ((ProofTerm.compile t).1 ++ [.andE1 (ProofTerm.compile t).2],
        (ProofTerm.compile t).1.length)
  | .andE2 t =>
      ((ProofTerm.compile t).1 ++ [.andE2 (ProofTerm.compile t).2],
        (ProofTerm.compile t).1.length)

theorem ProofTerm.compile_steps_pos (t : ProofTerm) :
    0 < (ProofTerm.compile t).1.length := by
  induction t with
  | hyp _ => simp [ProofTerm.compile]
  | andI l r ihl ihr =>
      simp [ProofTerm.compile, List.length_append, shiftSteps, List.length_map]
      omega
  | andE1 t ih =>
      simp [ProofTerm.compile, List.length_append]
  | andE2 t ih =>
      simp [ProofTerm.compile, List.length_append]

theorem ProofTerm.compile_steps_ne (t : ProofTerm) :
    (ProofTerm.compile t).1 ≠ [] :=
  fun h => by
    have := ProofTerm.compile_steps_pos t
    simp [h] at this

def ProofTerm.interpret (Γ : Context) : ProofTerm → Option (Support × Authority × Formula)
  | .hyp pid =>
      match findPremise Γ.premises pid with
      | none => none
      | some p => some ([p.id], p.authority, p.formula)
  | .andI l r =>
      match ProofTerm.interpret Γ l, ProofTerm.interpret Γ r with
      | some (S, a, φ), some (T, b, ψ) =>
          some (S ++ T, Authority.meet a b, Formula.and φ ψ)
      | _, _ => none
  | .andE1 t =>
      match ProofTerm.interpret Γ t with
      | some (S, a, Formula.and φ _) => some (S, a, φ)
      | _ => none
  | .andE2 t =>
      match ProofTerm.interpret Γ t with
      | some (S, a, Formula.and _ ψ) => some (S, a, ψ)
      | _ => none

theorem interpret_implies_derives
    (Γ : Context) (t : ProofTerm) (S : Support) (a : Authority) (φ : Formula)
    (h : ProofTerm.interpret Γ t = some (S, a, φ)) :
    Derives Γ S a φ := by
  induction t generalizing S a φ with
  | hyp pid =>
      simp [ProofTerm.interpret] at h
      cases hf : findPremise Γ.premises pid with
      | none => simp [hf] at h
      | some p =>
          simp [hf] at h
          obtain ⟨rfl, ⟨rfl, rfl⟩⟩ := h
          exact Derives.hyp Γ p (mem_of_find?_eq_some _ _ _ hf)
  | andI l r ihl ihr =>
      simp [ProofTerm.interpret] at h
      cases hl : ProofTerm.interpret Γ l with
      | none => simp [hl] at h
      | some jl =>
          cases hr : ProofTerm.interpret Γ r with
          | none => simp [hl, hr] at h
          | some jr =>
              simp [hl, hr] at h
              rcases jl with ⟨S1, a1, φ1⟩
              rcases jr with ⟨S2, a2, φ2⟩
              obtain ⟨rfl, ⟨rfl, rfl⟩⟩ := h
              exact Derives.andI Γ _ _ _ _ _ _ (ihl _ _ _ hl) (ihr _ _ _ hr)
  | andE1 t ih =>
      simp [ProofTerm.interpret] at h
      cases ht : ProofTerm.interpret Γ t with
      | none => simp [ht] at h
      | some jt =>
          rcases jt with ⟨S0, a0, ψ0⟩
          simp [ht] at h
          cases ψ0 with
          | atom _ => simp at h
          | not _ => simp at h
          | and φ ψ =>
              simp at h
              obtain ⟨rfl, ⟨rfl, rfl⟩⟩ := h
              exact Derives.andE1 Γ _ _ φ ψ (ih _ _ _ ht)
  | andE2 t ih =>
      simp [ProofTerm.interpret] at h
      cases ht : ProofTerm.interpret Γ t with
      | none => simp [ht] at h
      | some jt =>
          rcases jt with ⟨S0, a0, ψ0⟩
          simp [ht] at h
          cases ψ0 with
          | atom _ => simp at h
          | not _ => simp at h
          | and φ ψ =>
              simp at h
              obtain ⟨rfl, ⟨rfl, rfl⟩⟩ := h
              exact Derives.andE2 Γ _ _ φ ψ (ih _ _ _ ht)

theorem derives_to_proofterm
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ)
    (hu : uniquePremiseIds Γ.premises = true) :
    ∃ t : ProofTerm, ProofTerm.interpret Γ t = some (S, a, φ) := by
  induction h with
  | hyp p hp =>
      refine ⟨.hyp p.id, ?_⟩
      simp [ProofTerm.interpret, findPremise_of_mem_unique Γ.premises p hp hu]
  | andI S T a b φ ψ hφ hψ ihφ ihψ =>
      obtain ⟨tl, hl⟩ := ihφ
      obtain ⟨tr, hr⟩ := ihψ
      refine ⟨.andI tl tr, ?_⟩
      simp [ProofTerm.interpret, hl, hr]
  | andE1 S a φ ψ hand ih =>
      obtain ⟨t, ht⟩ := ih
      refine ⟨.andE1 t, ?_⟩
      simp [ProofTerm.interpret, ht]
  | andE2 S a φ ψ hand ih =>
      obtain ⟨t, ht⟩ := ih
      refine ⟨.andE2 t, ?_⟩
      simp [ProofTerm.interpret, ht]

theorem derives_iff_interpret
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (hu : uniquePremiseIds Γ.premises = true) :
    Derives Γ S a φ ↔
      ∃ t : ProofTerm, ProofTerm.interpret Γ t = some (S, a, φ) :=
  ⟨fun h => derives_to_proofterm Γ S a φ h hu,
   fun ⟨t, ht⟩ => interpret_implies_derives Γ t S a φ ht⟩

/-- Inductive compile correctness (strong form). -/
theorem compile_ok
    (Γ : Context) (t : ProofTerm) (S : Support) (a : Authority) (φ : Formula)
    (hu : uniquePremiseIds Γ.premises = true)
    (h : ProofTerm.interpret Γ t = some (S, a, φ)) :
    ∃ (js : List VerifiedJudgment),
      checkStepsLTR Γ.premises (ProofTerm.compile t).1 = some js ∧
      js[(ProofTerm.compile t).2]? = some {
        formula := φ, support := S,
        assurance := { declared := a, mathEstablished := false } } ∧
      js.length = (ProofTerm.compile t).1.length := by
  induction t generalizing S a φ with
  | hyp pid =>
      simp [ProofTerm.interpret] at h
      cases hf : findPremise Γ.premises pid with
      | none => simp [hf] at h
      | some p =>
          simp [hf] at h
          obtain ⟨rfl, ⟨rfl, rfl⟩⟩ := h
          let j : VerifiedJudgment := {
            formula := p.formula, support := [p.id],
            assurance := Assurance.hypDeclared p.authority }
          have hc : checkStepsLTR Γ.premises (ProofTerm.compile (.hyp pid)).1 = some [j] := by
            simp [ProofTerm.compile, checkStepsLTR, checkStepsGo, checkStep, hf, j,
              Assurance.hypDeclared]
          have hj : [j][(ProofTerm.compile (.hyp pid)).2]? = some {
              formula := p.formula, support := [p.id],
              assurance := { declared := p.authority, mathEstablished := false } } := by
            simp [ProofTerm.compile, j, Assurance.hypDeclared]
          have hlen : [j].length = (ProofTerm.compile (.hyp pid)).1.length := by
            simp [ProofTerm.compile]
          exact ⟨[j], hc, hj, hlen⟩
  | andI l r ihl ihr =>
      simp [ProofTerm.interpret] at h
      cases hl0 : ProofTerm.interpret Γ l with
      | none => simp [hl0] at h
      | some jl =>
          cases hr0 : ProofTerm.interpret Γ r with
          | none => simp [hl0, hr0] at h
          | some jr =>
              simp [hl0, hr0] at h
              rcases jl with ⟨S1, a1, φ1⟩
              rcases jr with ⟨S2, a2, φ2⟩
              obtain ⟨rfl, ⟨rfl, rfl⟩⟩ := h
              obtain ⟨js1, hc1, hj1, hlens1⟩ := ihl S1 a1 φ1 hl0
              obtain ⟨js2, hc2, hj2, hlens2⟩ := ihr S2 a2 φ2 hr0
              have hcat := checkStepsLTR_concat_shift _ _ _ js1 js2 hc1 hc2
              have hcat' :
                  checkStepsLTR Γ.premises
                    ((ProofTerm.compile l).1 ++
                      shiftSteps (ProofTerm.compile l).1.length (ProofTerm.compile r).1) =
                    some (js1 ++ js2) := by
                simpa [hlens1] using hcat
              have hi1 : (ProofTerm.compile l).2 < js1.length :=
                (List.getElem?_eq_some_iff.mp hj1).1
              have hi2 : (ProofTerm.compile r).2 < js2.length :=
                (List.getElem?_eq_some_iff.mp hj2).1
              have hi1' : (ProofTerm.compile l).2 < (js1 ++ js2).length := by
                simp [List.length_append]; omega
              have hi2' : (ProofTerm.compile l).1.length + (ProofTerm.compile r).2 <
                  (js1 ++ js2).length := by
                simp [List.length_append, hlens2]; omega
              have hsnoc := checkStepsLTR_snoc_andI Γ.premises _
                (js1 ++ js2) (ProofTerm.compile l).2
                ((ProofTerm.compile l).1.length + (ProofTerm.compile r).2)
                hi1' hi2' hcat'
              have el :
                  (js1 ++ js2)[(ProofTerm.compile l).2]'(hi1') =
                    js1[(ProofTerm.compile l).2]'(hi1) := List.getElem_append_left ..
              have er :
                  (js1 ++ js2)[(ProofTerm.compile l).1.length + (ProofTerm.compile r).2]'(hi2') =
                    js2[(ProofTerm.compile r).2]'(hi2) := by
                simpa [hlens1.symm] using
                  getElem_append_offset js1 js2 (ProofTerm.compile r).2 hi2
              have jl1 : js1[(ProofTerm.compile l).2]'(hi1) =
                  { formula := φ1, support := S1,
                    assurance := { declared := a1, mathEstablished := false } } :=
                (List.getElem?_eq_some_iff.mp hj1).2
              have jr2 : js2[(ProofTerm.compile r).2]'(hi2) =
                  { formula := φ2, support := S2,
                    assurance := { declared := a2, mathEstablished := false } } :=
                (List.getElem?_eq_some_iff.mp hj2).2
              let jAnd : VerifiedJudgment := {
                formula := Formula.and φ1 φ2
                support := S1 ++ S2
                assurance := Assurance.meetA
                  { declared := a1, mathEstablished := false }
                  { declared := a2, mathEstablished := false }
              }
              have hsnoc' :
                  checkStepsLTR Γ.premises (ProofTerm.compile (.andI l r)).1 =
                    some (js1 ++ js2 ++ [jAnd]) := by
                simpa [ProofTerm.compile, jAnd, Assurance.meetA, el, er, jl1, jr2] using hsnoc
              have hj :
                  (js1 ++ js2 ++ [jAnd])[(ProofTerm.compile (.andI l r)).2]? = some {
                    formula := Formula.and φ1 φ2, support := S1 ++ S2,
                    assurance := { declared := Authority.meet a1 a2, mathEstablished := false }
                  } := by
                have hlenMid : (js1 ++ js2).length =
                    (ProofTerm.compile l).1.length + (ProofTerm.compile r).1.length := by
                  simp [List.length_append, hlens1, hlens2]
                have hidx : (js1 ++ js2).length ≤ (ProofTerm.compile (.andI l r)).2 := by
                  simp [ProofTerm.compile, hlenMid]
                have := List.getElem?_append_right (l₁ := js1 ++ js2) (l₂ := [jAnd]) hidx
                simp [ProofTerm.compile, hlenMid, Nat.sub_self, jAnd, Assurance.meetA] at this ⊢
                exact this
              have hlenEq : (js1 ++ js2 ++ [jAnd]).length =
                  (ProofTerm.compile (.andI l r)).1.length := by
                simp [ProofTerm.compile, List.length_append, shiftSteps, List.length_map,
                  hlens1, hlens2]
              exact ⟨js1 ++ js2 ++ [jAnd], hsnoc', hj, hlenEq⟩
  | andE1 t ih =>
      simp [ProofTerm.interpret] at h
      cases ht : ProofTerm.interpret Γ t with
      | none => simp [ht] at h
      | some jt =>
          rcases jt with ⟨S0, a0, ψ0⟩
          simp [ht] at h
          cases hψ : ψ0 with
          | atom _ => simp [hψ] at h
          | not _ => simp [hψ] at h
          | and φ0 ψ0' =>
              simp [hψ] at h
              obtain ⟨rfl, ⟨rfl, rfl⟩⟩ := h
              obtain ⟨js, hc, hj, hlen⟩ := ih S0 a0 (Formula.and φ0 ψ0') (by
                simpa [ht, hψ])
              have hi : (ProofTerm.compile t).2 < js.length :=
                (List.getElem?_eq_some_iff.mp hj).1
              have hjv : js[(ProofTerm.compile t).2]'(hi) =
                  { formula := Formula.and φ0 ψ0', support := S0,
                    assurance := { declared := a0, mathEstablished := false } } :=
                (List.getElem?_eq_some_iff.mp hj).2
              have hf : js[(ProofTerm.compile t).2].formula = Formula.and φ0 ψ0' := by
                simp [hjv]
              have hsnoc := checkStepsLTR_snoc_andE1 Γ.premises (ProofTerm.compile t).1 js
                (ProofTerm.compile t).2 hi φ0 ψ0' hf hc
              let jOut : VerifiedJudgment := {
                formula := φ0
                support := S0
                assurance := { declared := a0, mathEstablished := false }
              }
              have hsnoc' :
                  checkStepsLTR Γ.premises (ProofTerm.compile (.andE1 t)).1 =
                    some (js ++ [jOut]) := by
                simpa [ProofTerm.compile, jOut, hjv] using hsnoc
              have hj' :
                  (js ++ [jOut])[(ProofTerm.compile (.andE1 t)).2]? = some jOut := by
                have hidx : js.length ≤ (ProofTerm.compile (.andE1 t)).2 := by
                  simp [ProofTerm.compile, hlen]
                have := List.getElem?_append_right (l₁ := js) (l₂ := [jOut]) hidx
                simpa [ProofTerm.compile, hlen, Nat.sub_self] using this
              have hlenEq : (js ++ [jOut]).length = (ProofTerm.compile (.andE1 t)).1.length := by
                simp [ProofTerm.compile, List.length_append, hlen]
              exact ⟨js ++ [jOut], hsnoc', by simpa [jOut] using hj', hlenEq⟩
  | andE2 t ih =>
      simp [ProofTerm.interpret] at h
      cases ht : ProofTerm.interpret Γ t with
      | none => simp [ht] at h
      | some jt =>
          rcases jt with ⟨S0, a0, ψ0⟩
          simp [ht] at h
          cases hψ : ψ0 with
          | atom _ => simp [hψ] at h
          | not _ => simp [hψ] at h
          | and φ0 ψ0' =>
              simp [hψ] at h
              obtain ⟨rfl, ⟨rfl, rfl⟩⟩ := h
              obtain ⟨js, hc, hj, hlen⟩ := ih S0 a0 (Formula.and φ0 ψ0') (by
                simpa [ht, hψ])
              have hi : (ProofTerm.compile t).2 < js.length :=
                (List.getElem?_eq_some_iff.mp hj).1
              have hjv : js[(ProofTerm.compile t).2]'(hi) =
                  { formula := Formula.and φ0 ψ0', support := S0,
                    assurance := { declared := a0, mathEstablished := false } } :=
                (List.getElem?_eq_some_iff.mp hj).2
              have hf : js[(ProofTerm.compile t).2].formula = Formula.and φ0 ψ0' := by
                simp [hjv]
              have hsnoc := checkStepsLTR_snoc_andE2 Γ.premises (ProofTerm.compile t).1 js
                (ProofTerm.compile t).2 hi φ0 ψ0' hf hc
              let jOut : VerifiedJudgment := {
                formula := ψ0'
                support := S0
                assurance := { declared := a0, mathEstablished := false }
              }
              have hsnoc' :
                  checkStepsLTR Γ.premises (ProofTerm.compile (.andE2 t)).1 =
                    some (js ++ [jOut]) := by
                simpa [ProofTerm.compile, jOut, hjv] using hsnoc
              have hj' :
                  (js ++ [jOut])[(ProofTerm.compile (.andE2 t)).2]? = some jOut := by
                have hidx : js.length ≤ (ProofTerm.compile (.andE2 t)).2 := by
                  simp [ProofTerm.compile, hlen]
                have := List.getElem?_append_right (l₁ := js) (l₂ := [jOut]) hidx
                simpa [ProofTerm.compile, hlen, Nat.sub_self] using this
              have hlenEq : (js ++ [jOut]).length = (ProofTerm.compile (.andE2 t)).1.length := by
                simp [ProofTerm.compile, List.length_append, hlen]
              exact ⟨js ++ [jOut], hsnoc', by simpa [jOut] using hj', hlenEq⟩





/-- Certificate completeness: interpret ⇒ accepted checkCertificate. -/
theorem interpret_checkCertificate
    (Γ : Context) (t : ProofTerm) (S : Support) (a : Authority) (φ : Formula)
    (hu : uniquePremiseIds Γ.premises = true)
    (h : ProofTerm.interpret Γ t = some (S, a, φ)) :
    checkCertificate {
      premises := Γ.premises
      steps := (ProofTerm.compile t).1
      conclusionStep := (ProofTerm.compile t).2
    } = some {
      formula := φ
      support := S
      assurance := { declared := a, mathEstablished := false }
    } := by
  obtain ⟨js, hc, hj, hlen⟩ := compile_ok Γ t S a φ hu h
  have hi : (ProofTerm.compile t).2 < js.length := (List.getElem?_eq_some_iff.mp hj).1
  have hjv : js[(ProofTerm.compile t).2]'(hi) =
      { formula := φ, support := S,
        assurance := { declared := a, mathEstablished := false } } :=
    (List.getElem?_eq_some_iff.mp hj).2
  simp [checkCertificate, hu, hc]
  cases hlt : Nat.decLt (ProofTerm.compile t).2 js.length with
  | isTrue ht => simpa [hjv]
  | isFalse hf => exact absurd hi hf



/-- Full completeness: Derives ⇒ accepted certificate (unique ids). -/
theorem derives_completeness
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ)
    (hu : uniquePremiseIds Γ.premises = true) :
    ∃ (c : StructuredCertificate) (j : VerifiedJudgment),
      c.premises = Γ.premises ∧
      checkCertificate c = some j ∧
      j.formula = φ ∧ j.support = S ∧ j.assurance.declared = a ∧
      j.assurance.mathEstablished = false := by
  obtain ⟨t, ht⟩ := derives_to_proofterm Γ S a φ h hu
  refine ⟨
    { premises := Γ.premises
      steps := (ProofTerm.compile t).1
      conclusionStep := (ProofTerm.compile t).2 },
    { formula := φ, support := S,
      assurance := { declared := a, mathEstablished := false } },
    rfl, interpret_checkCertificate Γ t S a φ hu ht, rfl, rfl, rfl, rfl⟩

/-- Semantic equivalence package for the Python-modelled checker algorithm. -/
theorem pythonLean_semantic_triangle
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificate c = some j) :
    Derives c.toContext j.support j.assurance.declared j.formula ∧
    j.assurance.mathEstablished = false ∧
    uniquePremiseIds c.premises = true :=
  ⟨checkCertificate_sound c j h,
   checkCertificate_mathEstablished_false c j h,
   checkCertificate_requires_unique_ids c j h⟩

end ScientificReasoning

#print axioms ScientificReasoning.derives_iff_interpret
#print axioms ScientificReasoning.compile_ok
#print axioms ScientificReasoning.interpret_checkCertificate
#print axioms ScientificReasoning.derives_completeness
#print axioms ScientificReasoning.pythonLean_semantic_triangle
