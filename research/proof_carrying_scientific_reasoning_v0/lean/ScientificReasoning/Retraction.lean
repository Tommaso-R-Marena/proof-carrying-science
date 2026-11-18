import ScientificReasoning.Contradictions

/-!
# Retraction: withdrawing a premise invalidates dependent supports
-/

namespace ScientificReasoning

def Support.dependsOn (S : Support) (i : PropId) : Prop := i ∈ S

def invalidatedBy (S : Support) (withdrawn : List PropId) : Prop :=
  ∃ i ∈ withdrawn, i ∈ S

theorem hyp_invalidated_by_self (p : Premise) :
    invalidatedBy [p.id] [p.id] :=
  ⟨p.id, by simp, by simp⟩

theorem andI_support_union_invalidation
    (S T : Support) (i : PropId)
    (h : i ∈ S ∨ i ∈ T) :
    invalidatedBy (S ++ T) [i] := by
  refine ⟨i, by simp, List.mem_append.2 h⟩

def Context.retract (Γ : Context) (withdrawn : List PropId) : Context :=
  { premises := Γ.premises.filter (fun p => !decide (p.id ∈ withdrawn)) }

theorem retract_removes
    (Γ : Context) (withdrawn : List PropId) (i : PropId) (hi : i ∈ withdrawn) :
    ¬ (Context.retract Γ withdrawn).hasId i := by
  intro ⟨p, hp, hid⟩
  have hfilt := List.mem_filter.1 hp
  have hbool : (!decide (p.id ∈ withdrawn)) = true := hfilt.2
  have hdec : decide (p.id ∈ withdrawn) = false := by
    cases hd : decide (p.id ∈ withdrawn) with
    | true => simp [hd] at hbool
    | false => rfl
  have hn : p.id ∉ withdrawn := of_decide_eq_false hdec
  exact hn (by simpa [hid] using hi)

theorem retracted_hyp_unavailable
    (Γ : Context) (p : Premise) (withdrawn : List PropId)
    (hw : p.id ∈ withdrawn)
    (hmem : p ∈ (Context.retract Γ withdrawn).premises) : False := by
  have : ¬ (Context.retract Γ withdrawn).hasId p.id := retract_removes Γ withdrawn p.id hw
  exact this ⟨p, hmem, rfl⟩

end ScientificReasoning

#print axioms ScientificReasoning.retract_removes
#print axioms ScientificReasoning.hyp_invalidated_by_self
#print axioms ScientificReasoning.andI_support_union_invalidation
